"""Tests for the detector mode dispatcher in routes.py.

Verify the three modes (`aruco`, `hsv`, `aruco_then_hsv`) all reach the
expected detection function and that the fallback chain works.
"""
import yaml
from vision.tests.conftest import make_synthetic_robot_image


def _set_detector_mode(tmp_config, mode: str) -> None:
    p = tmp_config / "settings.yaml"
    with p.open("r") as f:
        data = yaml.safe_load(f)
    data["robot"]["detector"] = mode
    with p.open("w") as f:
        yaml.safe_dump(data, f)


def test_default_aruco_then_hsv_falls_back_to_hsv(client, tmp_config):
    """conftest renders red/green markers (no ArUco tag in frame). With
    detector=aruco_then_hsv (the default), ArUco fails -> HSV path runs ->
    pose recovered."""
    _set_detector_mode(tmp_config, "aruco_then_hsv")
    r = client.post("/api/detect")
    assert r.status_code == 200
    pose = r.json()["robot_pose"]
    assert pose is not None, "HSV fallback should have detected the red/green markers"


def test_hsv_only_mode_uses_hsv(client, tmp_config):
    _set_detector_mode(tmp_config, "hsv")
    r = client.post("/api/detect")
    assert r.status_code == 200
    pose = r.json()["robot_pose"]
    assert pose is not None


def test_aruco_only_mode_returns_none_when_no_tag(client, tmp_config):
    """No ArUco tag in the synthetic frame and detector='aruco' (no fallback)
    -> /detect returns robot_pose=None with reason 'markers_not_found'."""
    _set_detector_mode(tmp_config, "aruco")
    r = client.post("/api/detect")
    assert r.status_code == 200
    body = r.json()
    assert body["robot_pose"] is None
    assert body["reason"] == "markers_not_found"


def test_invalid_detector_mode_rejected_by_config_loader(client, tmp_config):
    _set_detector_mode(tmp_config, "magic")
    r = client.post("/api/detect")
    assert r.status_code == 500
    assert r.json()["detail"]["error"] == "config_error"
