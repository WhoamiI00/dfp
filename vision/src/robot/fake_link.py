"""Fake serial link for sim mode.

Mimics `link.send_sequence` without touching real hardware. Sleeps proportional
to the firmware's per-command timing so the closed-loop controller experiences
the same per-step latency as the real Mega + HC-05.

Used when ROBOT_SIM=1 or when the runtime sim flag is set via /robot/mode.
The Bluetooth robot can be unreachable (or non-existent) and the rest of the
pipeline — planner, /execute/stream, manual D-pad — keeps working.
"""
from __future__ import annotations
import time
from vision.src.robot.link import CommandLog, ExecuteResult


# Mirrors firmware/plan_executor/plan_executor.ino defaults so the fake feels
# like the real bot. If you tune the firmware values, update these too.
_FIRMWARE_CELL_FORWARD_S = 0.45
_FIRMWARE_TURN_90_S = 2.0
_FIRMWARE_GRAB_PLACE_S = 2.0

# Scale factor: tests want fast fakes; demos want realistic timing.
# Override with FAKE_LINK_TIME_SCALE env var if needed.
_DEFAULT_TIME_SCALE = 1.0


def _delay_for(cmd: str) -> float:
    if cmd in ("F", "B"):
        return _FIRMWARE_CELL_FORWARD_S
    if cmd in ("L", "R"):
        return _FIRMWARE_TURN_90_S
    if cmd in ("G", "P"):
        return _FIRMWARE_GRAB_PLACE_S
    return 0.0  # S, ?, unknown


def _reply_for(cmd: str) -> str | None:
    if cmd in ("F", "B", "L", "R", "G", "P", "S"):
        return "OK"
    if cmd == "?":
        return "PONG"
    return None  # unknown -> ERR


def send_sequence_fake(
    sequence: str,
    port: str = "FAKE",
    baud: int = 0,
    time_scale: float = _DEFAULT_TIME_SCALE,
) -> ExecuteResult:
    """Drop-in replacement for `send_sequence` with no serial I/O.

    `port` and `baud` are accepted but unused — they're in the signature so
    callers can swap real/fake without changing argument lists. `time_scale`
    lets tests run instantly (pass 0.0) while production uses 1.0.
    """
    if not sequence:
        return ExecuteResult(ok=True, chars_sent=0, log=[])

    log: list[CommandLog] = []
    for c in sequence:
        if c in ("\n", "\r", " "):
            continue
        delay = _delay_for(c) * time_scale
        if delay > 0:
            time.sleep(delay)
        reply = _reply_for(c)
        elapsed_ms = int(delay * 1000)
        if reply is None:
            log.append(CommandLog(cmd=c, reply=f"ERR {c}", elapsed_ms=elapsed_ms))
            return ExecuteResult(
                ok=False,
                chars_sent=len(log),
                log=log,
                error=f"unexpected reply after '{c}': 'ERR {c}'",
            )
        log.append(CommandLog(cmd=c, reply=reply, elapsed_ms=elapsed_ms))

    return ExecuteResult(ok=True, chars_sent=len(log), log=log)
