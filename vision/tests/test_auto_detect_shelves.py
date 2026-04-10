"""API tests for POST /layout/auto_detect."""
import cv2
import numpy as np
from vision.tests.conftest import (
    make_synthetic_robot_image,
    project_world_to_pixel,
)


def _frame_with_yellow_blobs(intr, extr, world_positions):
    """Render a synthetic scene with yellow rectangles at the given world
    positions. Uses the conftest forward-projection so the blob pixels line
    up with what the backend will project *back* to world coordinates."""
    img = make_synthetic_robot_image(
        intr, extr, robot_xy_m=(1.25, 1.25), heading_deg=0.0, height_m=0.30,
    )
    half = 22  # pixel half-size of each drawn rectangle
    for (wx, wy) in world_positions:
        u, v = project_world_to_pixel(np.array([wx, wy, 0.0]), intr, extr)
        u, v = int(round(u)), int(round(v))
        cv2.rectangle(img, (u - half, v - half), (u + half, v + half), (0, 255, 255), -1)
    return img


def _upload_frame(client, frame):
    ok, buf = cv2.imencode(".png", frame)
    assert ok
    files = {"file": ("scene.png", buf.tobytes(), "image/png")}
    r = client.post("/api/camera/image", files=files)
    assert r.status_code == 200


def test_auto_detect_returns_three_shelves_in_left_to_right_order(
    client, synthetic_intrinsics, synthetic_extrinsics
):
    world_positions = [(0.5, 2.0), (1.25, 2.0), (2.0, 2.0)]
    frame = _frame_with_yellow_blobs(
        synthetic_intrinsics, synthetic_extrinsics, world_positions
    )
    _upload_frame(client, frame)

    r = client.post("/api/layout/auto_detect", json={
        "marker_color": "yellow",
        "max_count": 3,
        "persist": True,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["persisted"] is True
    assert len(data["shelves"]) == 3

    ids = [s["id"] for s in data["shelves"]]
    assert ids == ["shelf_A", "shelf_B", "shelf_C"]

    for shelf, (wx, wy) in zip(data["shelves"], world_positions):
        assert abs(shelf["world_x_m"] - wx) < 0.05, f"{shelf['id']} x={shelf['world_x_m']}"
        assert abs(shelf["world_y_m"] - wy) < 0.05, f"{shelf['id']} y={shelf['world_y_m']}"

    # Persisted shelves are now loadable via the existing GET endpoint.
    r2 = client.get("/api/shelves")
    persisted_ids = {s["id"] for s in r2.json()["shelves"]}
    assert persisted_ids == {"shelf_A", "shelf_B", "shelf_C"}


def test_auto_detect_respects_max_count(client, synthetic_intrinsics, synthetic_extrinsics):
    frame = _frame_with_yellow_blobs(
        synthetic_intrinsics, synthetic_extrinsics,
        [(0.5, 2.0), (1.25, 2.0), (2.0, 2.0)],
    )
    _upload_frame(client, frame)

    r = client.post("/api/layout/auto_detect", json={
        "marker_color": "yellow",
        "max_count": 2,
        "persist": False,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["persisted"] is False
    assert len(data["shelves"]) == 2


def test_auto_detect_returns_422_when_no_markers_found(client):
    # The default fixture frame has only the red/green robot markers; no
    # yellow blobs above the area threshold.
    r = client.post("/api/layout/auto_detect", json={
        "marker_color": "yellow",
        "max_count": 3,
    })
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "no_shelf_markers_found"


def test_auto_detect_rejects_unknown_marker_color(client):
    r = client.post("/api/layout/auto_detect", json={
        "marker_color": "octarine",
        "max_count": 3,
    })
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "unknown_marker_color"
