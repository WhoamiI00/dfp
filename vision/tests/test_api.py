"""FastAPI integration tests with a FakeCamera."""
from vision.tests.conftest import make_synthetic_robot_image


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_settings(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    data = r.json()
    assert data["workspace"]["width_m"] == 2.5


def test_shelves_get(client):
    r = client.get("/api/shelves")
    assert r.status_code == 200
    ids = {s["id"] for s in r.json()["shelves"]}
    assert {"shelf_A", "shelf_B"}.issubset(ids)


def test_shelves_put_round_trip(client):
    payload = {
        "shelves": [
            {
                "id": "shelf_X",
                "x_m": 1.0, "y_m": 1.0, "width_m": 0.5, "length_m": 0.5,
                "rotation_deg": 0.0,
                "approach_point": {"x_m": 0.5, "y_m": 1.0, "heading_deg": 0.0},
            }
        ]
    }
    r = client.put("/api/shelves", json=payload)
    assert r.status_code == 200
    r2 = client.get("/api/shelves")
    assert len(r2.json()["shelves"]) == 1
    assert r2.json()["shelves"][0]["id"] == "shelf_X"


def test_calibration_status(client):
    r = client.get("/api/calibration/status")
    assert r.status_code == 200
    assert r.json() == {"intrinsic": True, "extrinsic": True}


def test_capture(client):
    r = client.get("/api/capture")
    assert r.status_code == 200
    assert "image_base64" in r.json()


def test_detect(client):
    r = client.post("/api/detect")
    assert r.status_code == 200
    data = r.json()
    assert data["robot_pose"] is not None
    assert abs(data["robot_pose"]["x_m"] - 1.25) < 0.05


def test_camera_mode_default_live(client):
    r = client.get("/api/camera/mode")
    assert r.status_code == 200
    assert r.json() == {"mode": "live"}


def test_camera_image_upload_and_clear(client, synthetic_intrinsics, synthetic_extrinsics):
    import cv2
    # Use a synthetic robot image at (0.75, 0.75) as the override.
    override_frame = make_synthetic_robot_image(
        synthetic_intrinsics, synthetic_extrinsics,
        robot_xy_m=(0.75, 0.75), heading_deg=0.0, height_m=0.30,
    )
    ok, buf = cv2.imencode(".png", override_frame)
    assert ok
    files = {"file": ("override.png", buf.tobytes(), "image/png")}

    r = client.post("/api/camera/image", files=files)
    assert r.status_code == 200
    assert r.json() == {"mode": "test_image"}

    # Detect now sees the overridden position, not the fake camera's default (1.25, 1.25).
    r2 = client.post("/api/detect")
    assert r2.status_code == 200
    pose = r2.json()["robot_pose"]
    assert pose is not None
    assert abs(pose["x_m"] - 0.75) < 0.05
    assert abs(pose["y_m"] - 0.75) < 0.05

    r3 = client.delete("/api/camera/image")
    assert r3.status_code == 200
    assert r3.json() == {"mode": "live"}

    # Detect falls back to the fake camera's original frame (1.25, 1.25).
    r4 = client.post("/api/detect")
    assert r4.status_code == 200
    pose2 = r4.json()["robot_pose"]
    assert pose2 is not None
    assert abs(pose2["x_m"] - 1.25) < 0.05


def test_plan_pick_place(client):
    r = client.post("/api/plan", json={
        "task": "pick_place",
        "source_shelf_id": "shelf_A",
        "destination_shelf_id": "shelf_B",
    })
    assert r.status_code == 200
    data = r.json()
    waypoint_types = [w["type"] for w in data["waypoints"]]
    assert "grab" in waypoint_types
    assert "place" in waypoint_types
