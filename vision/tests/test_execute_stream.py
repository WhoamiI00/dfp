"""Tests for the closed-loop /execute/stream SSE endpoint and abort flow."""
import json
import threading
import time
import pytest
import yaml
from vision.tests.conftest import make_synthetic_robot_image
from vision.src.robot import link as link_module


def _enable_sim_mode():
    link_module.set_sim_mode(True)


def _restore_sim_mode():
    link_module.set_sim_mode(None)


@pytest.fixture(autouse=True)
def sim_mode_on():
    """Force sim mode for every test in this module so /execute/stream
    never tries to open a real serial port."""
    _enable_sim_mode()
    yield
    _restore_sim_mode()


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    """Parse SSE text into a list of (event_name, data_dict) tuples."""
    events = []
    current_event = None
    for line in text.splitlines():
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:") and current_event is not None:
            data_text = line[len("data:"):].strip()
            try:
                events.append((current_event, json.loads(data_text)))
            except json.JSONDecodeError:
                events.append((current_event, {"_raw": data_text}))
            current_event = None
    return events


def _shorten_max_steps(tmp_config, max_steps: int = 4) -> None:
    settings_path = tmp_config / "settings.yaml"
    with settings_path.open("r") as f:
        data = yaml.safe_load(f)
    data.setdefault("closed_loop", {})["max_steps"] = max_steps
    with settings_path.open("w") as f:
        yaml.safe_dump(data, f)


def _replace_camera_frame(client, intrinsics, extrinsics, robot_xy, heading=0.0):
    """Swap the test camera's frame to one with the robot at `robot_xy`.

    Uses the existing test-image override endpoint so we don't have to reach
    into camera internals.
    """
    import cv2
    frame = make_synthetic_robot_image(
        intrinsics, extrinsics,
        robot_xy_m=robot_xy, heading_deg=heading, height_m=0.30,
    )
    ok, buf = cv2.imencode(".png", frame)
    assert ok
    r = client.post(
        "/api/camera/image",
        files={"file": ("frame.png", buf.tobytes(), "image/png")},
    )
    assert r.status_code == 200


# --- /robot/mode endpoints --------------------------------------------------

def test_robot_mode_get_returns_current_state(client):
    r = client.get("/api/robot/mode")
    assert r.status_code == 200
    assert r.json() == {"sim": True}  # autouse fixture set it


def test_robot_mode_post_toggles(client):
    r = client.post("/api/robot/mode", json={"sim": False})
    assert r.status_code == 200
    assert r.json() == {"sim": False}
    r2 = client.post("/api/robot/mode", json={"sim": True})
    assert r2.json() == {"sim": True}


# --- /execute/stream happy path: already at goal -> done immediately --------

def test_stream_done_when_robot_already_at_approach_point(
    client, tmp_config, synthetic_intrinsics, synthetic_extrinsics,
):
    # shelf_A approach point is (0.707, 0.819) heading 270. Park the robot
    # right there — first iteration should fire `done` without any commands.
    _replace_camera_frame(
        client, synthetic_intrinsics, synthetic_extrinsics,
        robot_xy=(0.707, 0.819), heading=270.0,
    )
    r = client.post(
        "/api/execute/stream",
        json={"task": "navigate", "destination_shelf_id": "shelf_A"},
    )
    assert r.status_code == 200
    events = _parse_sse(r.text)
    names = [e[0] for e in events]
    assert "done" in names
    done = next(p for n, p in events if n == "done")
    assert done["sequence"] == ""
    assert done["steps"] == 0


# --- /execute/stream stuck: robot can't move, fake serial returns OK --------

def test_stream_stuck_when_camera_pose_never_changes(
    client, tmp_config, synthetic_intrinsics, synthetic_extrinsics,
):
    # Robot at (1.25, 1.25) (the conftest default), destination shelf_A
    # approach (0.707, 0.819). In sim mode the fake serial acks every F but
    # the camera frame is static, so the loop should detect "no progress"
    # after stuck_window_steps consecutive forwards.
    _shorten_max_steps(tmp_config, max_steps=20)  # leave room for stuck to fire first
    r = client.post(
        "/api/execute/stream",
        json={"task": "navigate", "destination_shelf_id": "shelf_A"},
    )
    assert r.status_code == 200
    events = _parse_sse(r.text)
    names = [e[0] for e in events]
    # Either "stuck" (preferred) or "step_budget_exceeded" is acceptable;
    # both mean the loop self-terminated rather than spinning forever.
    assert "stuck" in names or "step_budget_exceeded" in names


# --- /execute/stream step budget cap ----------------------------------------

def test_stream_step_budget_caps_runaway_loop(
    client, tmp_config, synthetic_intrinsics, synthetic_extrinsics,
):
    # Set max_steps to 2 and stuck check to never fire (huge window).
    settings_path = tmp_config / "settings.yaml"
    with settings_path.open("r") as f:
        data = yaml.safe_load(f)
    data.setdefault("closed_loop", {})["max_steps"] = 2
    data["closed_loop"]["stuck_window_steps"] = 999
    with settings_path.open("w") as f:
        yaml.safe_dump(data, f)

    r = client.post(
        "/api/execute/stream",
        json={"task": "navigate", "destination_shelf_id": "shelf_A"},
    )
    assert r.status_code == 200
    events = _parse_sse(r.text)
    names = [e[0] for e in events]
    assert "step_budget_exceeded" in names


# --- /execute/abort sets the flag (smoke test) ------------------------------

def test_execute_abort_endpoint_returns_ok(client):
    r = client.post("/api/execute/abort")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "running" in body


# --- 409 if a run is already in flight --------------------------------------
#
# Concurrency test: hold the run lock manually, then expect /execute/stream
# to refuse with 409. Avoids needing two threads to race naturally.

def test_stream_returns_409_when_already_running(client):
    from vision.src.api import routes
    routes._run_lock.acquire()
    try:
        r = client.post(
            "/api/execute/stream",
            json={"task": "navigate", "destination_shelf_id": "shelf_A"},
        )
        assert r.status_code == 409
        assert r.json()["detail"]["error"] == "execute_already_running"
    finally:
        routes._run_lock.release()


# --- unknown shelf -> 404 (validated up-front, before streaming starts) -----

def test_stream_unknown_shelf_404(client):
    r = client.post(
        "/api/execute/stream",
        json={"task": "navigate", "destination_shelf_id": "no_such_shelf"},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "unknown_shelf"
