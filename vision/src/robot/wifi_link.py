"""HTTP-over-WiFi link to the ESP32 robot.

The ESP32 firmware exposes:
  GET /cmd?val=<char>   one-shot command, returns "OK"
  GET /distance         current ultrasonic reading in cm (-1 = no echo)

Single-character commands:
  Drive: F B L R   start motion / S stop drive
  Lift:  U D       start motion / u stop lift
  Slide: I O       start motion / i stop slider
  Grip:  G open / N close / H release (detach servo)
  X     panic stop everything

The firmware has a 300-400 ms watchdog: motors halt if no command arrives in
that window. We don't rely on it, but it's a safety net for network blips.

This module composes those primitives into the higher-level actions the
planner needs (drive one cell, turn 90, lift to a target distance, run the
grab/place sequence). Each action returns a SubAck describing what happened
so the closed-loop controller can log it.
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from threading import Event, Lock, Thread
from typing import Callable, Optional
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError

from vision.src.models import RobotLinkConfig
from vision.src.robot.link import CommandLog, ExecuteResult


# Per-process lock so concurrent /execute/stream + manual control can't
# clobber each other on the same ESP32. Matches the pattern in link.py.
_lock = Lock()


@dataclass
class SubAck:
    """One link-level action's result, mirroring CommandLog for log uniformity."""
    cmd: str
    reply: str
    elapsed_ms: int
    ok: bool = True
    error: str | None = None

    def to_log(self) -> CommandLog:
        return CommandLog(cmd=self.cmd, reply=self.reply, elapsed_ms=self.elapsed_ms)


class WifiLinkError(Exception):
    pass


@dataclass
class WifiLink:
    """Stateful client for one ESP32 robot. Construct from RobotLinkConfig."""
    cfg: RobotLinkConfig
    # Injection point so tests can replace the HTTP layer with a fake.
    transport: Callable[[str, float], str] = field(default=None)  # type: ignore

    def __post_init__(self):
        if self.transport is None:
            self.transport = _default_http_get

    # --- Low-level transport -------------------------------------------------

    def _base_url(self) -> str:
        return f"http://{self.cfg.host}:{self.cfg.port}"

    def _send_cmd(self, val: str) -> SubAck:
        """One ESP32 /cmd request. Single char in `val`."""
        url = f"{self._base_url()}/cmd?{urlencode({'val': val})}"
        t0 = time.monotonic()
        try:
            reply = self.transport(url, self.cfg.request_timeout_s)
            elapsed = int((time.monotonic() - t0) * 1000)
            return SubAck(cmd=val, reply=reply.strip(), elapsed_ms=elapsed, ok=True)
        except Exception as e:
            elapsed = int((time.monotonic() - t0) * 1000)
            return SubAck(
                cmd=val, reply="", elapsed_ms=elapsed,
                ok=False, error=str(e),
            )

    def read_distance_cm(self) -> float:
        """Return current ultrasonic reading. -1.0 on error or no echo."""
        url = f"{self._base_url()}/distance"
        try:
            text = self.transport(url, self.cfg.request_timeout_s).strip()
            return float(text)
        except Exception:
            return -1.0

    # --- Composite drive primitives ------------------------------------------
    #
    # Each composite sends a "start" char, sleeps for the configured duration,
    # then sends an explicit stop. Reported as a single SubAck whose `cmd`
    # field is the start char (so the UI log lines look familiar).

    # Stop commands MUST succeed — leaving a motor running is the worst
    # failure mode. Retry a few times before giving up. The ESP32's own
    # 300-400 ms watchdog is the safety net of last resort, but we should
    # never rely on it.
    _STOP_RETRY_COUNT = 3

    def _send_stop(self, stop_char: str) -> SubAck:
        last: SubAck | None = None
        for attempt in range(self._STOP_RETRY_COUNT):
            ack = self._send_cmd(stop_char)
            if ack.ok:
                return ack
            last = ack
            time.sleep(0.05)  # brief backoff before retry
        # All retries failed. Return the last failure so the caller sees
        # the original error message.
        return last  # type: ignore

    # The ESP32 firmware has a ~300ms watchdog: if no drive command arrives
    # within that window, it auto-stops the motor as a safety net. To keep
    # the motor running for the full requested duration, we re-send the
    # start char every HEARTBEAT_MS — same pattern the browser-based Manual
    # tab uses.
    #
    # Smoothness matters: if heartbeats are delayed by a slow HTTP response
    # (ESP32 busy serving the previous request), the watchdog can trip and
    # the motor stutters. To avoid that we run heartbeats on a dedicated
    # thread that fires on a strict tick, and the main thread just sleeps.
    # Heartbeat HTTP errors are swallowed — one missed beat is fine, the
    # next beat is only HEARTBEAT_MS away.
    _HEARTBEAT_MS = 100   # below the 300ms watchdog by a comfortable margin

    def _drive_for(
        self, start_char: str, stop_char: str, duration_ms: int,
        heartbeat: bool = True,
    ) -> SubAck:
        """Send `start_char`, sleep `duration_ms`, send `stop_char`.

        If `heartbeat=True` (default for drive/lift), spawn a thread that
        re-sends `start_char` every HEARTBEAT_MS so the firmware's 300ms
        watchdog doesn't auto-stop the motor mid-move.

        If `heartbeat=False` (slider), skip heartbeats — the firmware
        handles slider auto-stop on its own time-based limit, and our
        heartbeats would only reset that safety timer and add HTTP load.
        """
        t0 = time.monotonic()
        start = self._send_cmd(start_char)
        if not start.ok:
            return start

        stop_event = Event()
        beater: Thread | None = None

        if heartbeat:
            beat_s = self._HEARTBEAT_MS / 1000.0

            def beat():
                while not stop_event.is_set():
                    if stop_event.wait(beat_s):
                        return
                    try:
                        self.transport(
                            f"{self._base_url()}/cmd?{urlencode({'val': start_char})}",
                            self.cfg.request_timeout_s,
                        )
                    except Exception:
                        pass

            beater = Thread(target=beat, daemon=True, name=f"heartbeat-{start_char}")
            beater.start()

        try:
            time.sleep(duration_ms / 1000.0)
        finally:
            if beater is not None:
                stop_event.set()
                beater.join(timeout=1.0)

        stop = self._send_stop(stop_char)
        elapsed = int((time.monotonic() - t0) * 1000)
        if not stop.ok:
            # Stop failed even after retries. The ESP32's own 300ms watchdog
            # halts the motor when heartbeats stop arriving, so physically
            # the motor is most likely already off — just unconfirmed.
            return SubAck(
                cmd=start_char,
                reply=f"start={start.reply!r} stop_err={stop.error!r}",
                elapsed_ms=elapsed, ok=False, error=stop.error,
            )
        return SubAck(
            cmd=start_char, reply="OK", elapsed_ms=elapsed, ok=True,
        )

    def drive_forward(self, ms: int | None = None) -> SubAck:
        return self._drive_for("F", "S", ms if ms is not None else self.cfg.cell_drive_ms)

    def drive_backward(self, ms: int | None = None) -> SubAck:
        return self._drive_for("B", "S", ms if ms is not None else self.cfg.cell_drive_ms)

    def turn_left(self, ms: int | None = None) -> SubAck:
        return self._drive_for("L", "S", ms if ms is not None else self.cfg.turn_90_ms)

    def turn_right(self, ms: int | None = None) -> SubAck:
        return self._drive_for("R", "S", ms if ms is not None else self.cfg.turn_90_ms)

    def stop_drive(self) -> SubAck:
        return self._send_cmd("S")

    def panic_stop(self) -> SubAck:
        return self._send_cmd("X")

    # --- Lift to a target ultrasonic distance --------------------------------

    def lift_to(self, target_cm: float) -> SubAck:
        """Drive lift up or down until the carriage's upward-facing ultrasonic
        reads `target_cm` (smaller cm = higher floor).

        Drives at full power and keeps a 100ms heartbeat going so the
        ESP32's ~300ms safety watchdog doesn't kill the motor mid-move
        (this matches the manual UP/DOWN button behaviour, which is why
        manual mode worked while lift_to was stalling).

        Stop conditions, in priority order:
          1. Within tolerance of target -> ok.
          2. Crossed the target (overshoot guard) -> ok.
          3. (Opt-in) No progress for `lift_stall_window_ms` -> fail.
             Disabled when `lift_min_progress_cm <= 0`.
          4. (Opt-in) Hard `lift_max_runtime_ms` ceiling -> fail.
             Disabled when `lift_max_runtime_ms <= 0`.

        Default config disables both guards so the lift runs to target
        no matter how long it takes — matches "full power until reached"
        for movement plans where the user wants reliable physical
        positioning.
        """
        cmd_label = f"lift_to({target_cm:.1f})"
        t0 = time.monotonic()
        current = self.read_distance_cm()
        if current < 0:
            return SubAck(
                cmd=cmd_label, reply="no_echo",
                elapsed_ms=int((time.monotonic() - t0) * 1000),
                ok=False, error="ultrasonic returned no echo",
            )

        if abs(current - target_cm) <= self.cfg.lift_tolerance_cm:
            return SubAck(
                cmd=cmd_label, reply=f"already_at_{current:.1f}cm",
                elapsed_ms=int((time.monotonic() - t0) * 1000), ok=True,
            )

        # Smaller cm = higher → lift UP shrinks the reading, DOWN grows it.
        direction = "U" if current > target_cm else "D"
        start = self._send_cmd(direction)
        if not start.ok:
            return SubAck(
                cmd=cmd_label, reply="start_failed",
                elapsed_ms=int((time.monotonic() - t0) * 1000),
                ok=False, error=start.error,
            )

        # Heartbeat thread — re-sends `direction` every HEARTBEAT_MS so the
        # firmware's ~300ms motor watchdog doesn't auto-stop the motor while
        # we're polling the ultrasonic. Same pattern _drive_for uses.
        # Without this, the motor only ran for ~300ms then stopped, which is
        # why manual hold-to-drive worked but lift_to stalled at ~0.3cm/s.
        beat_stop = Event()
        beat_s = self._HEARTBEAT_MS / 1000.0

        def beat():
            while not beat_stop.is_set():
                if beat_stop.wait(beat_s):
                    return
                try:
                    self.transport(
                        f"{self._base_url()}/cmd?{urlencode({'val': direction})}",
                        self.cfg.request_timeout_s,
                    )
                except Exception:
                    pass

        beater = Thread(target=beat, daemon=True, name=f"heartbeat-lift-{direction}")
        beater.start()

        # Optional guards — both default to OFF (cfg <= 0) so the lift runs
        # at full power until it reaches the target or the user aborts.
        stall_enabled = self.cfg.lift_min_progress_cm > 0 and self.cfg.lift_stall_window_ms > 0
        runtime_enabled = self.cfg.lift_max_runtime_ms > 0
        stall_window_s = self.cfg.lift_stall_window_ms / 1000.0
        max_runtime_s = self.cfg.lift_max_runtime_ms / 1000.0
        last_progress_check_t = time.monotonic()
        last_progress_check_cm = current

        try:
            while True:
                now = time.monotonic()
                if runtime_enabled and (now - t0) > max_runtime_s:
                    elapsed = int((now - t0) * 1000)
                    return SubAck(
                        cmd=cmd_label, reply=f"max_runtime_at_{current:.1f}cm",
                        elapsed_ms=elapsed, ok=False,
                        error=(
                            f"lift exceeded max runtime ({self.cfg.lift_max_runtime_ms}ms) "
                            f"without reaching {target_cm:.1f}cm — stalled at {current:.1f}cm"
                        ),
                    )

                time.sleep(0.04)  # ~25 Hz poll, well under sensor rate
                reading = self.read_distance_cm()
                if reading < 0:
                    # One bad read is fine — keep going. Stall check only
                    # cares about confirmed readings, not noise.
                    continue
                current = reading

                # Stop if we're inside tolerance or have crossed the target.
                close = abs(current - target_cm) <= self.cfg.lift_tolerance_cm
                crossed = (
                    (direction == "U" and current <= target_cm)
                    or (direction == "D" and current >= target_cm)
                )
                if close or crossed:
                    elapsed = int((time.monotonic() - t0) * 1000)
                    return SubAck(
                        cmd=cmd_label, reply=f"reached_{current:.1f}cm",
                        elapsed_ms=elapsed, ok=True,
                    )

                # Progress check at window boundaries — only if enabled.
                if stall_enabled and (now - last_progress_check_t) >= stall_window_s:
                    progress = abs(current - last_progress_check_cm)
                    if progress < self.cfg.lift_min_progress_cm:
                        elapsed = int((time.monotonic() - t0) * 1000)
                        return SubAck(
                            cmd=cmd_label, reply=f"stalled_at_{current:.1f}cm",
                            elapsed_ms=elapsed, ok=False,
                            error=(
                                f"lift stalled at {current:.1f}cm — moved only "
                                f"{progress:.2f}cm in {self.cfg.lift_stall_window_ms}ms "
                                f"(min {self.cfg.lift_min_progress_cm}cm). "
                                f"Hit a hard stop or motor jammed."
                            ),
                        )
                    last_progress_check_t = now
                    last_progress_check_cm = current
        finally:
            beat_stop.set()
            beater.join(timeout=1.0)
            self._send_cmd("u")  # always stop the lift, even on exception

    # --- Slider -------------------------------------------------------------
    #
    # IMPORTANT: slider durations are HARDWARE LIMITS, not tuning knobs.
    # Going past slider_extend_ms risks the slider detaching from its gear
    # (no end-stop switch). Caller-supplied `ms` values are ignored — the
    # config values are the ceiling and we always use them.

    def slider_extend(self, ms: int | None = None) -> SubAck:
        # Ignore caller's ms — slider OUT is a fixed hardware-safe duration.
        # heartbeat=False: firmware has its own time-based slider auto-stop,
        # and our heartbeats would reset that safety timer + add HTTP load
        # that competes with whatever else the ESP32 is doing.
        return self._drive_for("O", "i", self.cfg.slider_extend_ms, heartbeat=False)

    def slider_retract(self, ms: int | None = None) -> SubAck:
        return self._drive_for("I", "i", self.cfg.slider_retract_ms, heartbeat=False)

    # --- Gripper ------------------------------------------------------------
    # Gripper is a servo. After commanding an angle we sleep so the servo
    # actually arrives before the next sequence step starts.

    def gripper_open(self) -> SubAck:
        return self._gripper_settle("G")

    def gripper_close(self) -> SubAck:
        return self._gripper_settle("N")

    def gripper_release(self) -> SubAck:
        return self._send_cmd("H")

    def _gripper_settle(self, cmd: str) -> SubAck:
        t0 = time.monotonic()
        ack = self._send_cmd(cmd)
        if not ack.ok:
            return ack
        time.sleep(self.cfg.gripper_settle_ms / 1000.0)
        return SubAck(
            cmd=cmd, reply="OK",
            elapsed_ms=int((time.monotonic() - t0) * 1000), ok=True,
        )

    # --- Multi-step pick / place sequences ----------------------------------

    def grab_at(self, floor_distance_cm: Optional[float]) -> list[SubAck]:
        """Sequence: lift to floor → slider out → gripper close → slider in
                   → lift back to travel.

        floor_distance_cm=None means "no lift step needed" (legacy single-floor
        shelves) — we go straight to slider out from whatever position the
        lift is already in. The travel-position lift step at the end is also
        skipped in that case.
        """
        return self._pick_or_place(floor_distance_cm, gripper_action=self.gripper_close)

    def place_at(self, floor_distance_cm: Optional[float]) -> list[SubAck]:
        return self._pick_or_place(floor_distance_cm, gripper_action=self.gripper_open)

    # --- Timed (open-loop) pick / place ------------------------------------
    #
    # Bypasses the ultrasonic-based lift_to. Operator measured how long the
    # lift takes to reach each floor by holding the Manual UP button, and
    # those durations get baked into shelves.json. Reliable for smoke tests
    # before vision is wired up; not robust to drift.

    def lift_up_for(self, ms: int) -> SubAck:
        """Drive lift up for exactly `ms` milliseconds. No sensor feedback."""
        if ms <= 0:
            return SubAck(cmd="lift_up_for(0)", reply="skipped", elapsed_ms=0, ok=True)
        return self._drive_for("U", "u", ms)

    def lift_down_for(self, ms: int) -> SubAck:
        if ms <= 0:
            return SubAck(cmd="lift_down_for(0)", reply="skipped", elapsed_ms=0, ok=True)
        return self._drive_for("D", "u", ms)

    def grab_timed(self, lift_up_ms: int, lift_down_ms: int) -> list[SubAck]:
        """Open-loop grab. Default rest state: gripper closed, slider in.

        Sequence:
          1. lift up to floor
          2. slider out         — extend toward object (gripper still closed)
          3. gripper open       — release claws around object
          4. gripper close      — clamp on object
          5. slider in          — retract with object
          6. lift down to rest

        End state: gripper closed (holding object), slider in.
        """
        steps: list[SubAck] = []

        def push(s: SubAck) -> bool:
            steps.append(s)
            return s.ok

        if lift_up_ms > 0:
            if not push(self.lift_up_for(lift_up_ms)):
                return steps
        if not push(self.slider_extend()):
            return steps
        if not push(self.gripper_open()):
            return steps
        if not push(self.gripper_close()):
            return steps
        if not push(self.slider_retract()):
            return steps
        if lift_down_ms > 0:
            push(self.lift_down_for(lift_down_ms))
        return steps

    def place_timed(self, lift_up_ms: int, lift_down_ms: int) -> list[SubAck]:
        """Open-loop place. Assumes gripper closed (holding object), slider in.

        Sequence:
          1. lift up to floor
          2. slider out         — position object over destination
          3. gripper open       — release object
          4. slider in          — retract empty
          5. gripper close      — return to rest state (closed + in)
          6. lift down to rest

        End state: gripper closed (empty), slider in. Matches default rest.
        """
        steps: list[SubAck] = []

        def push(s: SubAck) -> bool:
            steps.append(s)
            return s.ok

        if lift_up_ms > 0:
            if not push(self.lift_up_for(lift_up_ms)):
                return steps
        if not push(self.slider_extend()):
            return steps
        if not push(self.gripper_open()):
            return steps
        if not push(self.slider_retract()):
            return steps
        if not push(self.gripper_close()):
            return steps
        if lift_down_ms > 0:
            push(self.lift_down_for(lift_down_ms))
        return steps

    def _pick_or_place(
        self,
        floor_distance_cm: Optional[float],
        gripper_action: Callable[[], SubAck],
    ) -> list[SubAck]:
        steps: list[SubAck] = []

        def push(s: SubAck) -> bool:
            steps.append(s)
            return s.ok

        if floor_distance_cm is not None:
            if not push(self.lift_to(floor_distance_cm)):
                return steps
        if not push(self.slider_extend()):
            return steps
        if not push(gripper_action()):
            return steps
        if not push(self.slider_retract()):
            return steps
        if floor_distance_cm is not None:
            push(self.lift_to(self.cfg.travel_distance_cm))
        return steps


# --- HTTP transport (separated so tests can swap it) ------------------------

def _default_http_get(url: str, timeout_s: float) -> str:
    try:
        with urlopen(url, timeout=timeout_s) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except URLError as e:
        raise WifiLinkError(f"GET {url} failed: {e}") from e


# --- Drop-in replacement for send_sequence ---------------------------------
#
# The legacy serial code exposed `send_sequence(string)` which streamed chars.
# /execute/stream still wants something it can call per-step with the planner's
# next char. This wrapper accepts a single char and dispatches to the right
# composite primitive. Multi-char strings are NOT supported on WiFi — the
# closed-loop controller never sends more than one char per step anyway.

def send_one(link: WifiLink, ch: str) -> ExecuteResult:
    with _lock:
        if ch == "F":
            ack = link.drive_forward()
        elif ch == "B":
            ack = link.drive_backward()
        elif ch == "L":
            ack = link.turn_left()
        elif ch == "R":
            ack = link.turn_right()
        elif ch == "S":
            ack = link.stop_drive()
        elif ch == "X":
            ack = link.panic_stop()
        else:
            return ExecuteResult(
                ok=False, chars_sent=0, log=[],
                error=f"WiFi link: unknown drive char {ch!r}",
            )
    log = [ack.to_log()]
    return ExecuteResult(
        ok=ack.ok, chars_sent=1 if ack.ok else 0,
        log=log, error=ack.error,
    )
