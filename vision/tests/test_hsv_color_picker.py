"""Backend tests for the color-picker endpoints and helpers."""
import cv2
import numpy as np
from vision.src.detection.hsv_ranges import sample_hsv_range_from_pixel
from vision.src.detection.robot import mask_for_ranges
from vision.tests.conftest import make_synthetic_robot_image


def _solid_frame(bgr: tuple[int, int, int], size=(720, 1280)) -> np.ndarray:
    h, w = size
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:, :] = bgr
    return frame


def test_sample_returns_range_that_masks_the_sampled_colour():
    # Solid cyan-ish blue (BGR) — inside the generic blue hue range.
    frame = _solid_frame((200, 120, 40))
    ranges, median = sample_hsv_range_from_pixel(frame, (640, 360), patch_size=5)

    assert len(ranges) >= 1
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = mask_for_ranges(hsv, ranges)
    # The sampled point must be masked by the range we just built.
    assert mask[360, 640] > 0
    # And so should almost the whole solid patch.
    assert mask.mean() > 200  # nearly fully white out of 255


def test_sample_near_red_hue_wrap_emits_two_ranges():
    # Pure red in BGR — hue is near 0 in OpenCV HSV.
    frame = _solid_frame((0, 0, 220))
    ranges, median = sample_hsv_range_from_pixel(frame, (100, 100), patch_size=3)
    assert median[0] < 10 or median[0] > 170
    assert len(ranges) == 2  # two bands bracketing the hue wheel


def test_sample_rejects_out_of_bounds_pixel():
    frame = _solid_frame((0, 200, 0))
    import pytest
    with pytest.raises(ValueError):
        sample_hsv_range_from_pixel(frame, (9999, 9999))


# --- API ---------------------------------------------------------------------


def _upload_solid_frame(client, bgr):
    frame = _solid_frame(bgr)
    ok, buf = cv2.imencode(".png", frame)
    assert ok
    files = {"file": ("solid.png", buf.tobytes(), "image/png")}
    r = client.post("/api/camera/image", files=files)
    assert r.status_code == 200


def test_hsv_sample_endpoint_returns_bands_covering_sampled_pixel(client):
    _upload_solid_frame(client, (200, 120, 40))
    r = client.post("/api/hsv/sample", json={"pixel_u": 640, "pixel_v": 360})
    assert r.status_code == 200
    data = r.json()
    assert "median_h" in data
    assert len(data["bands"]) >= 1
    band = data["bands"][0]
    assert band["h_min"] <= data["median_h"] <= band["h_max"] or len(data["bands"]) == 2
    assert band["s_min"] <= data["median_s"] <= band["s_max"]
    assert band["v_min"] <= data["median_v"] <= band["v_max"]


def test_hsv_sample_endpoint_400_on_bad_pixel(client):
    r = client.post("/api/hsv/sample", json={"pixel_u": 99999, "pixel_v": 99999})
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "invalid_pixel"


def test_custom_hsv_round_trip(client):
    # Empty list initially
    r = client.get("/api/hsv/custom_ranges")
    assert r.status_code == 200
    assert r.json()["entries"] == []

    # Upsert a range
    payload = {
        "bands": [
            {"h_min": 20, "s_min": 80, "v_min": 150,
             "h_max": 35, "s_max": 255, "v_max": 255},
        ]
    }
    r = client.put("/api/hsv/custom_ranges/my_yellow", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "my_yellow"
    assert body["bands"][0]["h_min"] == 20

    # List shows it
    r = client.get("/api/hsv/custom_ranges")
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["name"] == "my_yellow"

    # Delete
    r = client.delete("/api/hsv/custom_ranges/my_yellow")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r = client.get("/api/hsv/custom_ranges")
    assert r.json()["entries"] == []


def test_custom_hsv_rejects_invalid_name(client):
    r = client.put("/api/hsv/custom_ranges/bad name!", json={
        "bands": [{
            "h_min": 0, "s_min": 0, "v_min": 0,
            "h_max": 10, "s_max": 255, "v_max": 255,
        }],
    })
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "invalid_color_name"


def test_custom_hsv_delete_404_on_missing(client):
    r = client.delete("/api/hsv/custom_ranges/never_saved")
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "custom_hsv_not_found"


def test_auto_detect_uses_saved_custom_color(
    client, synthetic_intrinsics, synthetic_extrinsics
):
    """End-to-end: save a custom colour, then ask auto-detect to use it."""
    # Render a scene with three cyan-ish blobs at known world positions.
    from vision.tests.conftest import project_world_to_pixel
    base = make_synthetic_robot_image(
        synthetic_intrinsics, synthetic_extrinsics,
        robot_xy_m=(1.25, 1.25), heading_deg=0.0, height_m=0.30,
    )
    half = 22
    world_positions = [(0.5, 2.0), (1.25, 2.0), (2.0, 2.0)]
    for (wx, wy) in world_positions:
        u, v = project_world_to_pixel(
            np.array([wx, wy, 0.0]), synthetic_intrinsics, synthetic_extrinsics,
        )
        u, v = int(round(u)), int(round(v))
        # Cyan-ish BGR (not matching any built-in range)
        cv2.rectangle(base, (u - half, v - half), (u + half, v + half), (255, 180, 0), -1)

    ok, buf = cv2.imencode(".png", base)
    assert ok
    client.post("/api/camera/image", files={"file": ("scene.png", buf.tobytes(), "image/png")})

    # Save a custom colour tuned to the cyan-ish BGR we just drew.
    client.put("/api/hsv/custom_ranges/robot_cyan", json={
        "bands": [{
            "h_min": 85, "s_min": 150, "v_min": 150,
            "h_max": 110, "s_max": 255, "v_max": 255,
        }],
    })

    # Auto-detect using the custom name
    r = client.post("/api/layout/auto_detect", json={
        "marker_color": "robot_cyan",
        "max_count": 3,
        "persist": False,
    })
    assert r.status_code == 200, r.text
    assert len(r.json()["shelves"]) == 3
