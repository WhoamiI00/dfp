"""Robot pose detection from a single ArUco tag.

A black-and-white tag mounted flat on top of the robot. ArUco gives sub-pixel
corner accuracy and is fully invariant to lighting, sticker colour, and
background colour — the things that wreck the HSV pipeline.

Heading derivation: ArUco returns the four tag corners in a fixed order
(top-left, top-right, bottom-right, bottom-left in the tag's own frame). We
project the tag centre and the midpoint of the top edge onto the floor plane
via the same `project_pixel_to_floor` helper that HSV uses, so the resulting
(x, y, heading) lives in the same workspace coordinate system — endpoints
that mix detectors keep working without translation.

Tag ID and physical size come from RobotConfig.markers.tag_id /
markers.tag_size_m. Use the same DICT_4X4_50 dictionary as the extrinsic
calibration so we don't have to load two detector instances.
"""
from __future__ import annotations
import numpy as np
import cv2
from vision.src.models import Intrinsics, Extrinsics, RobotPose
from vision.src.calibration.parallax import project_pixel_to_floor
from vision.src.calibration.extrinsic import ARUCO_DICT


def _aruco_detector():
    """Build a fresh ArUco detector. Cheap; no need to cache."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    params = cv2.aruco.DetectorParameters()
    return cv2.aruco.ArucoDetector(aruco_dict, params)


def detect_robot_aruco(
    frame: np.ndarray,
    intrinsics: Intrinsics,
    extrinsics: Extrinsics,
    travel_height_m: float,
    tag_id: int,
) -> RobotPose | None:
    """Detect a single ArUco tag identified by `tag_id` and return the robot
    pose at `travel_height_m` above the floor (the tag's mounting height).

    Returns None if the tag isn't visible. Caller is responsible for falling
    back to HSV (or returning a 'robot_not_detected' error to the client).
    """
    undistorted = cv2.undistort(frame, intrinsics.camera_matrix, intrinsics.dist_coeffs)
    detector = _aruco_detector()
    corners, ids, _ = detector.detectMarkers(undistorted)
    if ids is None:
        return None

    ids_flat = ids.flatten().tolist()
    if tag_id not in ids_flat:
        return None
    idx = ids_flat.index(tag_id)
    # corners[idx] is shape (1, 4, 2) — 4 corners in (u, v).
    tag_corners = corners[idx].reshape(4, 2)

    # ArUco corner order: TL, TR, BR, BL (clockwise from top-left).
    tl, tr, br, bl = tag_corners
    centre_px = tag_corners.mean(axis=0)
    top_mid_px = (tl + tr) / 2.0

    # Project both points onto the floor plane at the tag's mounting height.
    # Same projector HSV uses, so coordinates stay consistent across detectors.
    try:
        centre_world = project_pixel_to_floor(
            (float(centre_px[0]), float(centre_px[1])),
            travel_height_m, intrinsics, extrinsics,
        )
        top_world = project_pixel_to_floor(
            (float(top_mid_px[0]), float(top_mid_px[1])),
            travel_height_m, intrinsics, extrinsics,
        )
    except ValueError:
        # Ray parallel to floor or behind camera — calibration is wrong;
        # treat as "not detected" rather than crashing the request.
        return None

    dx = top_world[0] - centre_world[0]
    dy = top_world[1] - centre_world[1]
    heading_deg = float(np.degrees(np.arctan2(dy, dx)))

    return RobotPose(
        x_m=float(centre_world[0]),
        y_m=float(centre_world[1]),
        heading_deg=heading_deg,
        confidence=1.0,  # ArUco doesn't have HSV's blob-area confidence problem
    )
