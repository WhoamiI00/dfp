"""Robot detection tests using synthetic rendered scenes."""
import numpy as np
import pytest
from vision.src.detection.robot import detect_robot
from vision.tests.conftest import make_synthetic_robot_image


@pytest.mark.parametrize("x,y,heading", [
    (1.25, 1.25, 0.0),
    (0.5, 0.5, 90.0),
    (2.0, 0.5, 180.0),
    (1.0, 2.0, 270.0),
])
def test_detect_robot_position_and_heading(
    synthetic_intrinsics, synthetic_extrinsics, x, y, heading
):
    img = make_synthetic_robot_image(
        synthetic_intrinsics, synthetic_extrinsics,
        robot_xy_m=(x, y), heading_deg=heading, height_m=0.30,
    )
    pose = detect_robot(img, synthetic_intrinsics, synthetic_extrinsics, travel_height_m=0.30)
    assert pose is not None
    assert abs(pose.x_m - x) < 0.05, f"x error: {pose.x_m - x}"
    assert abs(pose.y_m - y) < 0.05, f"y error: {pose.y_m - y}"
    heading_diff = (pose.heading_deg - heading + 180) % 360 - 180
    assert abs(heading_diff) < 5, f"heading error: {heading_diff}"


def test_detect_robot_missing_markers(synthetic_intrinsics, synthetic_extrinsics):
    """Black image → no markers → robot_pose is None."""
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    pose = detect_robot(img, synthetic_intrinsics, synthetic_extrinsics, travel_height_m=0.30)
    assert pose is None
