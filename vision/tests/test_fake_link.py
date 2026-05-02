"""Tests for the fake serial link used in sim mode."""
import os
import time
import pytest
from vision.src.robot.fake_link import send_sequence_fake
from vision.src.robot import link as link_module


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


def test_fake_full_protocol_chars_all_ack():
    result = send_sequence_fake("FBLRGPS?", time_scale=0.0)
    assert result.ok is True
    assert result.chars_sent == 8
    assert [e.reply for e in result.log] == ["OK"] * 7 + ["PONG"]


def test_fake_unknown_char_aborts():
    result = send_sequence_fake("FXF", time_scale=0.0)
    assert result.ok is False
    assert result.chars_sent == 2  # F (ok) + X (err); aborts before second F
    assert result.log[1].cmd == "X"
    assert result.log[1].reply.startswith("ERR")


def test_fake_whitespace_chars_skipped():
    result = send_sequence_fake("F\n F", time_scale=0.0)
    assert result.ok is True
    assert result.chars_sent == 2  # both Fs, whitespace dropped
    assert all(e.cmd == "F" for e in result.log)


def test_fake_timing_roughly_matches_firmware():
    # F is ~0.45 s, scale 0.1 -> ~45 ms. Allow generous slack for CI jitter.
    t0 = time.monotonic()
    send_sequence_fake("FF", time_scale=0.1)
    elapsed = time.monotonic() - t0
    assert 0.05 < elapsed < 0.5, f"expected ~0.09s, got {elapsed:.3f}s"


def test_send_sequence_uses_fake_when_sim_mode_enabled(monkeypatch):
    # Wipe any environment override and force runtime sim on.
    monkeypatch.delenv("ROBOT_SIM", raising=False)
    link_module.set_sim_mode(True)
    try:
        # If this hit a real serial port it would block / raise. The fake
        # returns OK for "?" with no I/O.
        result = link_module.send_sequence("?", port="DOES_NOT_EXIST", baud=9600)
        assert result.ok is True
        assert result.log[0].reply == "PONG"
    finally:
        link_module.set_sim_mode(None)


def test_env_sim_mode_picked_up(monkeypatch):
    link_module.set_sim_mode(None)  # clear any leftover override
    monkeypatch.setenv("ROBOT_SIM", "1")
    assert link_module.is_sim_mode() is True
    monkeypatch.setenv("ROBOT_SIM", "0")
    assert link_module.is_sim_mode() is False


def test_runtime_sim_override_beats_env(monkeypatch):
    monkeypatch.setenv("ROBOT_SIM", "0")
    link_module.set_sim_mode(True)
    try:
        assert link_module.is_sim_mode() is True
    finally:
        link_module.set_sim_mode(None)
    assert link_module.is_sim_mode() is False
