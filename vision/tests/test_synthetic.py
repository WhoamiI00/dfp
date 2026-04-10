"""Synthetic calibration tests."""
import numpy as np
import pytest
from vision.src.api.config_loader import load_settings
from vision.src.calibration.parallax import project_pixel_to_floor
from vision.src.calibration.synthetic import build_synthetic_calibration
from pathlib import Path


@pytest.fixture
def settings():
    cfg = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"
    return load_settings(cfg)


def test_synthetic_calibration_maps_image_center_to_workspace_center(settings):
    frame = np.zeros((1280, 1280, 3), dtype=np.uint8)
    intrinsics, extrinsics = build_synthetic_calibration(frame, settings)

    cx_px = frame.shape[1] / 2.0
    cy_px = frame.shape[0] / 2.0
    x, y = project_pixel_to_floor(
        (cx_px, cy_px), height_above_floor_m=0.0, intrinsics=intrinsics, extrinsics=extrinsics
    )
    assert abs(x - settings.workspace.width_m / 2) < 1e-6
    assert abs(y - settings.workspace.height_m / 2) < 1e-6


@pytest.mark.parametrize(
    "pixel_uv,expected_xy",
    [
        ((0.0, 640.0), (0.0, 1.25)),     # left edge → world (0, ws_h/2)
        ((1280.0, 640.0), (2.5, 1.25)),  # right edge → world (ws_w, ws_h/2)
        ((640.0, 0.0), (1.25, 2.5)),     # top edge → world (ws_w/2, ws_h)
    ],
)
def test_synthetic_calibration_edge_pixels(settings, pixel_uv, expected_xy):
    frame = np.zeros((1280, 1280, 3), dtype=np.uint8)
    intrinsics, extrinsics = build_synthetic_calibration(frame, settings)
    x, y = project_pixel_to_floor(
        pixel_uv, height_above_floor_m=0.0, intrinsics=intrinsics, extrinsics=extrinsics
    )
    assert abs(x - expected_xy[0]) < 1e-3
    assert abs(y - expected_xy[1]) < 1e-3
