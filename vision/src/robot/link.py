"""Thin serial wrapper for streaming single-char commands to the Mega over
HC-05 Bluetooth. Each char blocks until the firmware replies with "OK" or
"PONG", so the PC and the robot stay in lockstep and the Mega's RX buffer
never backs up mid-plan.

The port is opened and closed per call — HC-05 link warmup is ~2 s, which
is fine for a button-click workflow and keeps us free of stale-handle
issues between runs. If this becomes a bottleneck, move to a persistent
connection guarded by a module-level lock.
"""
from __future__ import annotations
import os
import time
from dataclasses import dataclass
from threading import Lock

import serial


DEFAULT_PORT = os.environ.get("ROBOT_PORT", "COM6")
DEFAULT_BAUD = int(os.environ.get("ROBOT_BAUD", "9600"))
LINK_WARMUP_S = 2.0
READ_TIMEOUT_S = 10.0

_lock = Lock()  # one execute at a time


@dataclass
class CommandLog:
    cmd: str
    reply: str
    elapsed_ms: int


@dataclass
class ExecuteResult:
    ok: bool
    chars_sent: int
    log: list[CommandLog]
    error: str | None = None


def send_sequence(
    sequence: str,
    port: str = DEFAULT_PORT,
    baud: int = DEFAULT_BAUD,
) -> ExecuteResult:
    """Open `port`, send each char of `sequence` and wait for its ack.

    Aborts on the first non-OK/non-PONG reply. Always closes the port.
    """
    if not sequence:
        return ExecuteResult(ok=True, chars_sent=0, log=[])

    with _lock:
        try:
            link = serial.Serial(port, baud, timeout=READ_TIMEOUT_S)
        except serial.SerialException as e:
            return ExecuteResult(
                ok=False, chars_sent=0, log=[],
                error=f"could not open {port}: {e}",
            )

        log: list[CommandLog] = []
        try:
            time.sleep(LINK_WARMUP_S)
            link.reset_input_buffer()

            for c in sequence:
                t0 = time.monotonic()
                link.write(c.encode())
                reply = link.readline().decode(errors="replace").strip()
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                log.append(CommandLog(cmd=c, reply=reply, elapsed_ms=elapsed_ms))

                if reply not in ("OK", "PONG"):
                    return ExecuteResult(
                        ok=False,
                        chars_sent=len(log),
                        log=log,
                        error=f"unexpected reply after '{c}': {reply!r}",
                    )

            return ExecuteResult(ok=True, chars_sent=len(log), log=log)
        finally:
            link.close()
