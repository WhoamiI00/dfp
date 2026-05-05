"""Tests for the fake link used in sim mode and the link.send_sequence dispatcher."""
import time
import pytest

from vision.src.robot.fake_link import send_sequence_fake
from vision.src.robot import link as link_module
from vision.src.models import RobotLinkConfig


SIM_CFG = RobotLinkConfig(type="sim")


def test_fake_empty_sequence_returns_ok():
    result = send_sequence_fake("", time_scale=0.0)
    assert result.ok is True
    assert result.chars_sent == 0
    assert result.log == []


def test_fake_single_forward_acks_ok():
    result = send_sequence_fake("F", time_scale=0.0)
    assert result.ok is True
    assert result.chars_sent == 1
    assert result.log[0].cmd == "F"
    assert result.log[0].reply == "OK"


def test_fake_full_drive_protocol_acks():
    result = send_sequence_fake("FBLRGPSX", time_scale=0.0)
    assert result.ok is True
    assert result.chars_sent == 8
    assert [e.reply for e in result.log] == ["OK"] * 8


def test_fake_unknown_char_aborts():
    # `Z` isn't in the fake's command map, so it returns ERR and the
    # following `F` never runs.
    result = send_sequence_fake("FZF", time_scale=0.0)
    assert result.ok is False
    assert result.chars_sent == 2  # F (ok) + Z (err); aborts before second F
    assert result.log[1].cmd == "Z"
    assert result.log[1].reply.startswith("ERR")


def test_fake_whitespace_chars_skipped():
    result = send_sequence_fake("F\n F", time_scale=0.0)
    assert result.ok is True
    assert result.chars_sent == 2  # both Fs, whitespace dropped
    assert all(e.cmd == "F" for e in result.log)


def test_fake_timing_roughly_matches_drive():
    # F drive is ~0.45 s, scale 0.1 -> ~45 ms. Allow generous slack for CI jitter.
    t0 = time.monotonic()
    send_sequence_fake("FF", time_scale=0.1)
    elapsed = time.monotonic() - t0
    assert 0.05 < elapsed < 0.5, f"expected ~0.09s, got {elapsed:.3f}s"


def test_send_sequence_routes_to_fake_when_link_type_sim():
    """robot_link.type='sim' makes send_sequence use the fake without
    touching the network — no real ESP32 needed for tests."""
    result = link_module.send_sequence("F", link_cfg=SIM_CFG)
    assert result.ok is True
    assert result.log[0].reply == "OK"


def test_runtime_sim_override_forces_fake_even_when_link_is_wifi():
    """The sim-mode override (set from /robot/mode) wins over settings.yaml."""
    wifi_cfg = RobotLinkConfig(type="wifi", host="0.0.0.0", port=1)
    link_module.set_sim_mode(True)
    try:
        # If sim override didn't kick in this would try to hit 0.0.0.0:1 and fail.
        result = link_module.send_sequence("F", link_cfg=wifi_cfg)
        assert result.ok is True
        assert result.log[0].reply == "OK"
    finally:
        link_module.set_sim_mode(None)


def test_sim_mode_default_is_false():
    link_module.set_sim_mode(None)
    assert link_module.is_sim_mode() is False


def test_send_sequence_with_no_cfg_falls_back_to_fake():
    """Defensive: callers that forget link_cfg get the fake, not a network call."""
    link_module.set_sim_mode(None)
    result = link_module.send_sequence("F")
    assert result.ok is True
