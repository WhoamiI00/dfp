"""Robot detection tests using synthetic rendered scenes."""
import cv2
import numpy as np
import pytest
from vision.src.detection.robot import detect_robot
from vision.tests.conftest import make_synthetic_robot_image, project_world_to_pixel


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


def test_detect_robot_ignores_far_decoy_back_blob(
    synthetic_intrinsics, synthetic_extrinsics
):
    """A huge green blob far from the front marker (e.g. a green shelf backdrop)
    must not be picked as the back marker — the small real back marker near the
    front marker should win via proximity filtering."""
    robot_xy = (1.25, 1.25)
    heading = 0.0
    img = make_synthetic_robot_image(
        synthetic_intrinsics,
        synthetic_extrinsics,
        robot_xy_m=robot_xy,
        heading_deg=heading,
        height_m=0.30,
    )

    # Paint a huge green decoy rectangle at a far corner of the workspace
    # (world ~0.2, 0.2, floor). Much larger than the real back marker blob.
    decoy_corners_world = [
        np.array([0.0, 0.0, 0.0]),
        np.array([0.6, 0.0, 0.0]),
        np.array([0.6, 0.6, 0.0]),
        np.array([0.0, 0.6, 0.0]),
    ]
    pixel_pts = np.array(
        [project_world_to_pixel(c, synthetic_intrinsics, synthetic_extrinsics)
         for c in decoy_corners_world],
        dtype=np.int32,
    )
    cv2.fillPoly(img, [pixel_pts], (0, 255, 0))

    pose = detect_robot(
        img, synthetic_intrinsics, synthetic_extrinsics, travel_height_m=0.30
    )
    assert pose is not None, "expected detection despite decoy"
    assert abs(pose.x_m - robot_xy[0]) < 0.05, f"x error: {pose.x_m - robot_xy[0]}"
    assert abs(pose.y_m - robot_xy[1]) < 0.05, f"y error: {pose.y_m - robot_xy[1]}"
    heading_diff = (pose.heading_deg - heading + 180) % 360 - 180
    assert abs(heading_diff) < 5, f"heading error: {heading_diff}"
