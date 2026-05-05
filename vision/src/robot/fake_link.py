"""Fake robot link for sim mode.

No hardware, no network. Mirrors the timing of the real WiFi link so the
closed-loop controller experiences the same per-step latency it would on the
ESP32. Used by /robot/mode {sim:true} and by the test suite.
"""
from __future__ import annotations
import time
from vision.src.robot.link import CommandLog, ExecuteResult


# Approximate timings (seconds) for each command. Mirrors the durations a
# WiFi link would spend doing F→sleep→S, etc. Tests can override the scale
# via the FAKE_LINK_TIME_SCALE env var if they care about wall-clock cost.
_DRIVE_S = 0.45
_TURN_S = 0.60
_GRAB_PLACE_S = 1.50  # full multi-step pick is slower than one drive
_DEFAULT_TIME_SCALE = 1.0


def _delay_for(cmd: str) -> float:
    if cmd in ("F", "B"):
        return _DRIVE_S
    if cmd in ("L", "R"):
        return _TURN_S
    if cmd in ("G", "P"):
        return _GRAB_PLACE_S
    return 0.0  # S, X, U, D, u, I, O, i, N, H — instantaneous in sim


def _reply_for(cmd: str) -> str | None:
    if cmd in ("F", "B", "L", "R", "G", "P", "S", "X",
               "U", "D", "u", "I", "O", "i", "N", "H"):
        return "OK"
    return None


def send_sequence_fake(
    sequence: str,
    time_scale: float = _DEFAULT_TIME_SCALE,
) -> ExecuteResult:
    """In-process fake of send_sequence. No network, no hardware."""
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
                ok=False, chars_sent=len(log), log=log,
                error=f"unexpected reply after '{c}': 'ERR {c}'",
            )
        log.append(CommandLog(cmd=c, reply=reply, elapsed_ms=elapsed_ms))

    return ExecuteResult(ok=True, chars_sent=len(log), log=log)
