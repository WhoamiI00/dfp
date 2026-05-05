"""Robot link dispatch.

Two link types:
  wifi  -> HTTP to ESP32 (production hardware path).
  sim   -> in-process fake, no network. Used by tests and demo mode.

Old Bluetooth/Arduino serial code is gone — see git history if you need it.
The public `send_sequence(string)` function is preserved so the closed-loop
controller and manual-control endpoints don't have to know which link is
active. They send one char per step; that char is routed to the right link.

For multi-step grab/place sequences the WiFi link exposes higher-level
primitives (`grab_at`, `place_at`) that /execute/stream calls directly when
it sees a Grab/Place waypoint. Those don't go through send_sequence.
"""
from __future__ import annotations
from dataclasses import dataclass
from threading import Lock

from vision.src.models import RobotLinkConfig


_lock = Lock()


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


# --- Sim mode flag ----------------------------------------------------------
# Process-wide override settable at runtime via POST /robot/mode. Lets the UI
# flip between WiFi (real ESP32) and sim (no hardware) without restarting.
# When True, send_sequence routes to fake_link regardless of settings.
_sim_override: bool | None = None


def is_sim_mode() -> bool:
    return _sim_override is True


def set_sim_mode(enabled: bool | None) -> None:
    """Set the runtime sim flag. Pass None to clear and use settings.yaml."""
    global _sim_override
    _sim_override = enabled


def send_sequence(sequence: str, link_cfg: RobotLinkConfig | None = None) -> ExecuteResult:
    """Send each char of `sequence` to the configured robot link.

    Sim override (set_sim_mode(True)) wins over settings — useful when the
    user toggles sim from the web UI mid-session. Otherwise:
      - link_cfg.type == "sim"  -> fake link
      - link_cfg.type == "wifi" -> WiFi link to ESP32

    The closed-loop controller and manual /robot/send both send single chars,
    so multi-char sequences only matter for fake (which loops chars
    internally). For WiFi, multi-char strings are dispatched one char at a
    time and the first failure aborts the rest.
    """
    if not sequence:
        return ExecuteResult(ok=True, chars_sent=0, log=[])

    if is_sim_mode() or (link_cfg is not None and link_cfg.type == "sim"):
        from vision.src.robot.fake_link import send_sequence_fake
        return send_sequence_fake(sequence)

    if link_cfg is None:
        # Defensive: caller forgot to pass config. Default to sim so we don't
        # try to hit a hardcoded IP that doesn't exist on this LAN.
        from vision.src.robot.fake_link import send_sequence_fake
        return send_sequence_fake(sequence)

    if link_cfg.type == "wifi":
        return _send_via_wifi(sequence, link_cfg)

    return ExecuteResult(
        ok=False, chars_sent=0, log=[],
        error=f"unknown robot_link.type: {link_cfg.type!r}",
    )


def _send_via_wifi(sequence: str, cfg: RobotLinkConfig) -> ExecuteResult:
    """Route each char through the WiFi link, stopping on first failure."""
    from vision.src.robot.wifi_link import WifiLink, send_one

    link = WifiLink(cfg=cfg)
    combined: list[CommandLog] = []
    chars_sent = 0
    for ch in sequence:
        if ch in ("\n", "\r", " "):
            continue
        result = send_one(link, ch)
        combined.extend(result.log)
        chars_sent += result.chars_sent
        if not result.ok:
            return ExecuteResult(
                ok=False, chars_sent=chars_sent, log=combined,
                error=result.error,
            )
    return ExecuteResult(ok=True, chars_sent=chars_sent, log=combined)
