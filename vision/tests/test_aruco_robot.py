"""Tests for ArUco-based robot pose detection.

Strategy: render a real DICT_4X4_50 marker into a blank frame, warp it so its
4 corners land at the projected pixel positions of a known world-space tag,
then assert detect_robot_aruco recovers the right (x, y, heading).
"""
import math
import numpy as np
import cv2
import pytest
from vision.src.detection.aruco_robot import detect_robot_aruco
from vision.src.calibration.extrinsic import ARUCO_DICT
from vision.tests.conftest import project_world_to_pixel


def _render_tag_at_world_pose(
    intrinsics, extrinsics,
    world_xy_m: tuple[float, float],
    heading_deg: float,
    height_m: float,
    tag_id: int,
    tag_size_m: float,
    image_size: tuple[int, int] = (1280, 720),
) -> np.ndarray:
    """Render a DICT_4X4_50 tag onto a blank frame at the projected position
    of a world-space tag of `tag_size_m` centred at `(world_xy_m, height_m)`
    with the given heading.

    The robot's local +X axis (i.e. `heading_deg`) corresponds to the tag's
    "up" direction (top edge midpoint), matching the convention in
    aruco_robot.detect_robot_aruco.
    """
    # Build the 4 world corners of the tag in the order ArUco returns them:
    # TL, TR, BR, BL — viewed from above, with "top" being the heading direction.
    half = tag_size_m / 2.0
    rad = math.radians(heading_deg)
    cos, sin = math.cos(rad), math.sin(rad)
    cx, cy = world_xy_m

    # In tag-local frame: top is +X (forward = heading direction).
    # TL = (+half x, +half y), TR = (+half x, -half y), BR = (-half, -half), BL = (-half, +half)
    local = [(+half, +half), (+half, -half), (-half, -half), (-half, +half)]
    world_corners = []
    for lx, ly in local:
        wx = cx + cos * lx - sin * ly
        wy = cy + sin * lx + cos * ly
        world_corners.append((wx, wy, height_m))

    # Project each to pixel space.
    pixel_corners = np.array(
        [project_world_to_pixel(np.array(p), intrinsics, extrinsics) for p in world_corners],
        dtype=np.float32,
    )

    # Render the tag itself at a known size, then warp its 4 source corners
    # onto pixel_corners.
    tag_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    marker_img = cv2.aruco.generateImageMarker(tag_dict, tag_id, 200)
    src = np.array([[0, 0], [200, 0], [200, 200], [0, 200]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(src, pixel_corners)

    # Convert tag to BGR so it composites onto a colour frame.
    tag_bgr = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2BGR)
    canvas = np.full((image_size[1], image_size[0], 3), 200, dtype=np.uint8)
    warped = cv2.warpPerspective(tag_bgr, M, image_size, flags=cv2.INTER_NEAREST,
                                  borderMode=cv2.BORDER_TRANSPARENT)
    # Mask: anywhere the warp put pixels > 0, replace canvas. (Background of
    # warped image stays at black; the tag is mostly black and white, so use
    # a non-zero mask to avoid eating the tag's black squares.)
    mask = cv2.warpPerspective(
        np.full((200, 200), 255, dtype=np.uint8), M, image_size, flags=cv2.INTER_NEAREST,
    )
    canvas[mask > 0] = warped[mask > 0]
    return canvas


@pytest.mark.parametrize("world_xy,heading_deg", [
    ((1.25, 1.25), 0.0),
    ((0.5, 0.5), 90.0),
    ((2.0, 0.5), 180.0),
    ((1.0, 2.0), -90.0),
])
def test_detect_robot_aruco_recovers_pose(
    world_xy, heading_deg, synthetic_intrinsics, synthetic_extrinsics,
):
    frame = _render_tag_at_world_pose(
        synthetic_intrinsics, synthetic_extrinsics,
        world_xy_m=world_xy, heading_deg=heading_deg, height_m=0.30,
        tag_id=4, tag_size_m=0.10,  # 10 cm — bigger than default for synth test pixel accuracy
    )
    pose = detect_robot_aruco(
        frame, synthetic_intrinsics, synthetic_extrinsics,
        travel_height_m=0.30, tag_id=4,
    )
    assert pose is not None, "Tag should be detectable"
    assert abs(pose.x_m - world_xy[0]) < 0.05
    assert abs(pose.y_m - world_xy[1]) < 0.05
    # Heading wraps; compare via shortest angular diff.
    diff = ((pose.heading_deg - heading_deg + 180) % 360) - 180
    assert abs(diff) < 5.0, f"heading off by {diff:.1f}° (got {pose.heading_deg}, expected {heading_deg})"


def test_detect_robot_aruco_returns_none_when_tag_absent(
    synthetic_intrinsics, synthetic_extrinsics,
):
    # Plain grey frame, no tag rendered.
    frame = np.full((720, 1280, 3), 128, dtype=np.uint8)
    pose = detect_robot_aruco(
        frame, synthetic_intrinsics, synthetic_extrinsics,
        travel_height_m=0.30, tag_id=4,
    )
    assert pose is None


def test_detect_robot_aruco_returns_none_when_wrong_tag_id(
    synthetic_intrinsics, synthetic_extrinsics,
):
    # Render tag 7, ask detector for tag 4.
    frame = _render_tag_at_world_pose(
        synthetic_intrinsics, synthetic_extrinsics,
        world_xy_m=(1.25, 1.25), heading_deg=0.0, height_m=0.30,
        tag_id=7, tag_size_m=0.10,
    )
    pose = detect_robot_aruco(
        frame, synthetic_intrinsics, synthetic_extrinsics,
        travel_height_m=0.30, tag_id=4,  # different ID
    )
    assert pose is None


def test_detect_robot_aruco_confidence_is_one(
    synthetic_intrinsics, synthetic_extrinsics,
):
    frame = _render_tag_at_world_pose(
        synthetic_intrinsics, synthetic_extrinsics,
        world_xy_m=(1.25, 1.25), heading_deg=0.0, height_m=0.30,
        tag_id=4, tag_size_m=0.10,
    )
    pose = detect_robot_aruco(
        frame, synthetic_intrinsics, synthetic_extrinsics,
        travel_height_m=0.30, tag_id=4,
    )
    assert pose is not None
    assert pose.confidence == 1.0
