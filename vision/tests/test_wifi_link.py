"""Tests for the WiFi link to the ESP32, using a mock HTTP transport.

The transport is injected as a callable, so no sockets, no port allocation,
and no risk of accidentally hitting a real ESP32 on the LAN during CI.
"""
from __future__ import annotations
from typing import Iterable
import pytest

from vision.src.models import RobotLinkConfig
from vision.src.robot.wifi_link import WifiLink, WifiLinkError


# A fast config: tiny timings so tests don't wall-clock anything noticeable.
FAST_CFG = RobotLinkConfig(
    type="wifi", host="127.0.0.1", port=80,
    cell_drive_ms=10, turn_90_ms=10,
    slider_extend_ms=10, slider_retract_ms=10, gripper_settle_ms=10,
    travel_distance_cm=25.0, lift_tolerance_cm=2.0,
    lift_stall_window_ms=200, lift_min_progress_cm=0.5,
    lift_max_runtime_ms=5000,
    request_timeout_s=0.1,
)


class MockTransport:
    """Records every URL and serves canned replies for /distance.

    Distance reads return values from `distance_seq` in order, then repeat
    the last one. /cmd always returns "OK" unless `fail_for` matches.
    """
    def __init__(self, distance_seq: Iterable[float] | None = None,
                 fail_for: set[str] | None = None):
        self.calls: list[str] = []
        self._distances = list(distance_seq or [])
        self._dist_idx = 0
        self._fail_for = fail_for or set()

    def __call__(self, url: str, timeout_s: float) -> str:
        self.calls.append(url)
        if "/distance" in url:
            if not self._distances:
                return "-1"
            i = min(self._dist_idx, len(self._distances) - 1)
            v = self._distances[i]
            self._dist_idx += 1
            return f"{v:.1f}"
        # /cmd
        # Pull val=X out of the URL crudely.
        for tok in url.split("?", 1)[-1].split("&"):
            if tok.startswith("val="):
                ch = tok[4:]
                if ch in self._fail_for:
                    raise WifiLinkError(f"mock failure for {ch}")
        return "OK"


# --- Drive composites -------------------------------------------------------

def test_drive_forward_sends_F_then_S():
    t = MockTransport()
    link = WifiLink(cfg=FAST_CFG, transport=t)
    ack = link.drive_forward()
    assert ack.ok
    assert any("val=F" in c for c in t.calls)
    assert any("val=S" in c for c in t.calls)


def test_drive_failure_propagates():
    t = MockTransport(fail_for={"F"})
    link = WifiLink(cfg=FAST_CFG, transport=t)
    ack = link.drive_forward()
    assert not ack.ok
    assert ack.error and "mock failure" in ack.error


def test_turn_left_uses_L_char():
    t = MockTransport()
    link = WifiLink(cfg=FAST_CFG, transport=t)
    link.turn_left()
    assert any("val=L" in c for c in t.calls)


# --- Lift to target ---------------------------------------------------------

def test_lift_to_skips_when_already_in_tolerance():
    """Reading already at target -> no movement, immediate OK."""
    t = MockTransport(distance_seq=[25.5])  # within 2 cm of 25
    link = WifiLink(cfg=FAST_CFG, transport=t)
    ack = link.lift_to(25.0)
    assert ack.ok
    # Only one /distance read, no U/D commands sent.
    assert all("val=U" not in c and "val=D" not in c for c in t.calls)


def test_lift_to_drives_up_when_current_higher_cm():
    """current=25, target=5 -> need to lift UP (smaller cm = higher)."""
    t = MockTransport(distance_seq=[25, 20, 15, 10, 5])
    link = WifiLink(cfg=FAST_CFG, transport=t)
    ack = link.lift_to(5.0)
    assert ack.ok, f"expected ok, got {ack}"
    assert any("val=U" in c for c in t.calls), "should have started lift up"
    assert any("val=u" in c for c in t.calls), "should have stopped lift"


def test_lift_to_drives_down_when_current_lower_cm():
    """current=5, target=25 -> need to lower (larger cm = lower)."""
    t = MockTransport(distance_seq=[5, 10, 15, 20, 25])
    link = WifiLink(cfg=FAST_CFG, transport=t)
    ack = link.lift_to(25.0)
    assert ack.ok
    assert any("val=D" in c for c in t.calls)
    assert any("val=u" in c for c in t.calls)


def test_lift_to_fails_when_stalled_no_progress():
    """Sensor reading flat-lines (motor stuck / hit stop) -> fail with
    a stalled-at message, not a wall-clock timeout."""
    t = MockTransport(distance_seq=[25])  # never moves
    cfg = RobotLinkConfig(**{
        **FAST_CFG.__dict__,
        "lift_stall_window_ms": 50,
        "lift_min_progress_cm": 0.5,
        "lift_max_runtime_ms": 5000,
    })
    link = WifiLink(cfg=cfg, transport=t)
    ack = link.lift_to(5.0)
    assert not ack.ok
    assert "stalled" in (ack.reply + (ack.error or ""))
    # Always emits a stop.
    assert any("val=u" in c for c in t.calls)


def test_lift_to_keeps_going_while_making_progress():
    """Slow lift that takes much longer than the old wall-clock timeout
    should still succeed as long as it's moving."""
    # 25 -> 23 -> 21 -> ... -> 5: many small steps. Window is 50ms with
    # min progress 0.5cm — each 2cm step exceeds that.
    sequence = list(range(25, 4, -1))  # 25, 24, ..., 5
    t = MockTransport(distance_seq=sequence)
    cfg = RobotLinkConfig(**{
        **FAST_CFG.__dict__,
        "lift_stall_window_ms": 50,
        "lift_min_progress_cm": 0.5,
        "lift_max_runtime_ms": 5000,
    })
    link = WifiLink(cfg=cfg, transport=t)
    ack = link.lift_to(5.0)
    assert ack.ok, f"expected ok, got {ack}"
    assert "reached" in ack.reply


def test_lift_to_no_echo_returns_failure_immediately():
    t = MockTransport(distance_seq=[-1])
    link = WifiLink(cfg=FAST_CFG, transport=t)
    ack = link.lift_to(10.0)
    assert not ack.ok
    assert "echo" in (ack.error or "")


# --- Multi-step grab / place -----------------------------------------------

def test_grab_at_runs_full_sequence_when_floor_given():
    # Distances: lift_to needs to see current then settle near target.
    # We're already at 25, going to 5: 25, 20, 10, 5, ... then for the
    # second lift_to(travel=25) we go 5, 15, 25.
    t = MockTransport(distance_seq=[25, 20, 10, 5, 5, 15, 25])
    link = WifiLink(cfg=FAST_CFG, transport=t)
    steps = link.grab_at(5.0)
    assert all(s.ok for s in steps), f"step failures: {[s for s in steps if not s.ok]}"

    # Expected actions in order: lift_to(5), slider_extend(O), close(N),
    # slider_retract(I), lift_to(travel=25).
    cmds = [s.cmd for s in steps]
    assert cmds[0].startswith("lift_to")
    assert "O" in cmds  # slider extend
    assert "N" in cmds  # gripper close
    assert "I" in cmds  # slider retract
    assert cmds[-1].startswith("lift_to")


def test_grab_at_skips_lift_when_floor_distance_none():
    """Legacy single-floor shelves -> no lift step."""
    t = MockTransport()
    link = WifiLink(cfg=FAST_CFG, transport=t)
    steps = link.grab_at(None)
    cmds = [s.cmd for s in steps]
    assert all(not c.startswith("lift_to") for c in cmds)
    # Still extends, grips, retracts.
    assert "O" in cmds and "N" in cmds and "I" in cmds


def test_place_at_uses_open_instead_of_close():
    t = MockTransport(distance_seq=[25, 18, 13, 13, 18, 25])
    link = WifiLink(cfg=FAST_CFG, transport=t)
    steps = link.place_at(13.0)
    cmds = [s.cmd for s in steps]
    assert "G" in cmds, "place should open the gripper, not close"
    assert "N" not in cmds


def test_grab_at_aborts_after_first_failed_step():
    t = MockTransport(distance_seq=[25], fail_for={"O"})  # slider extend fails
    link = WifiLink(cfg=FAST_CFG, transport=t)
    steps = link.grab_at(None)  # skip lift to isolate the slider failure
    assert not steps[-1].ok, "last recorded step should be the failure"
    cmds = [s.cmd for s in steps]
    # Failure on slider out -> we never reach gripper or retract.
    assert "N" not in cmds
    assert "I" not in cmds


# --- Distance readback -----------------------------------------------------

def test_read_distance_parses_float_response():
    t = MockTransport(distance_seq=[12.4])
    link = WifiLink(cfg=FAST_CFG, transport=t)
    assert link.read_distance_cm() == pytest.approx(12.4)


def test_read_distance_returns_negative_on_error():
    def boom(url, timeout_s):
        raise WifiLinkError("boom")
    link = WifiLink(cfg=FAST_CFG, transport=boom)
    assert link.read_distance_cm() == -1.0
