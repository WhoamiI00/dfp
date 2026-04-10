"""Tests for parallax pixel-to-floor projection."""
import numpy as np
import pytest
from vision.src.calibration.parallax import project_pixel_to_floor
from vision.tests.conftest import project_world_to_pixel


def test_parallax_height_zero_identity(synthetic_intrinsics, synthetic_extrinsics):
    """A point on the floor (z=0) should project back to its own floor position."""
    world = np.array([1.0, 1.5, 0.0])
    u, v = project_world_to_pixel(world, synthetic_intrinsics, synthetic_extrinsics)
    x, y = project_pixel_to_floor((u, v), 0.0, synthetic_intrinsics, synthetic_extrinsics)
    assert abs(x - 1.0) < 0.01, f"x error: {x - 1.0}"
    assert abs(y - 1.5) < 0.01, f"y error: {y - 1.5}"


def test_parallax_with_height(synthetic_intrinsics, synthetic_extrinsics):
    """A marker 30 cm above the floor at (1.0, 1.0) should resolve to (1.0, 1.0)."""
    height = 0.30
    world = np.array([1.0, 1.0, height])
    u, v = project_world_to_pixel(world, synthetic_intrinsics, synthetic_extrinsics)
    x, y = project_pixel_to_floor((u, v), height, synthetic_intrinsics, synthetic_extrinsics)
    assert abs(x - 1.0) < 0.01, f"x error: {x - 1.0}"
    assert abs(y - 1.0) < 0.01, f"y error: {y - 1.0}"


@pytest.mark.parametrize("x,y,h", [
    (0.5, 0.5, 0.10),
    (1.25, 1.25, 0.30),
    (2.0, 0.5, 0.30),
    (0.5, 2.0, 0.50),
])
def test_parallax_across_workspace(synthetic_intrinsics, synthetic_extrinsics, x, y, h):
    """Parallax correction should be accurate within 1 cm across the workspace."""
    world = np.array([x, y, h])
    u, v = project_world_to_pixel(world, synthetic_intrinsics, synthetic_extrinsics)
    rx, ry = project_pixel_to_floor((u, v), h, synthetic_intrinsics, synthetic_extrinsics)
    assert abs(rx - x) < 0.01, f"x error at ({x},{y},{h}): {rx - x}"
    assert abs(ry - y) < 0.01, f"y error at ({x},{y},{h}): {ry - y}"
