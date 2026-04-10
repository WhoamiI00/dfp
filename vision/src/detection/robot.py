"""Robot pose detection from HSV color markers."""
import math
import numpy as np
import cv2
from vision.src.models import Intrinsics, Extrinsics, RobotPose
from vision.src.calibration.parallax import project_pixel_to_floor
from vision.src.detection.hsv_ranges import (
    RED_HSV_RANGES,
    GREEN_HSV_RANGES,
    MIN_MARKER_AREA_PX,
    HsvRange,
)


def mask_for_ranges(hsv: np.ndarray, ranges: list[tuple[np.ndarray, np.ndarray]]) -> np.ndarray:
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lo, hi in ranges:
        mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lo, hi))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def largest_blob(mask: np.ndarray) -> tuple[float, float, int] | None:
    """Return (cx, cy, area) of the largest blob in the mask, ignoring
    the minimum-area threshold. Useful for debugging."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    area = int(cv2.contourArea(largest))
    M = cv2.moments(largest)
    if M["m00"] == 0:
        return None
    cx = M["m10"] / M["m00"]
    cy = M["m01"] / M["m00"]
    return cx, cy, area


def _largest_blob_centroid(mask: np.ndarray) -> tuple[float, float, int] | None:
    result = largest_blob(mask)
    if result is None:
        return None
    if result[2] < MIN_MARKER_AREA_PX:
        return None
    return result


# Backwards-compat alias
_mask_for_ranges = mask_for_ranges


def detect_robot(
    frame: np.ndarray,
    intrinsics: Intrinsics,
    extrinsics: Extrinsics,
    travel_height_m: float,
    front_ranges: list[HsvRange] | None = None,
    back_ranges: list[HsvRange] | None = None,
) -> RobotPose | None:
    """Detect the robot's pose in a BGR frame. Returns None if markers are missing.

    `front_ranges` and `back_ranges` override the default red/green HSV ranges.
    """
    if front_ranges is None:
        front_ranges = RED_HSV_RANGES
    if back_ranges is None:
        back_ranges = GREEN_HSV_RANGES

    undistorted = cv2.undistort(frame, intrinsics.camera_matrix, intrinsics.dist_coeffs)
    hsv = cv2.cvtColor(undistorted, cv2.COLOR_BGR2HSV)

    front_mask = mask_for_ranges(hsv, front_ranges)
    back_mask = mask_for_ranges(hsv, back_ranges)

    front_blob = _largest_blob_centroid(front_mask)
    back_blob = _largest_blob_centroid(back_mask)
    if front_blob is None or back_blob is None:
        return None

    front_cx, front_cy, front_area = front_blob
    back_cx, back_cy, back_area = back_blob

    front_floor = project_pixel_to_floor(
        (front_cx, front_cy), travel_height_m, intrinsics, extrinsics
    )
    back_floor = project_pixel_to_floor(
        (back_cx, back_cy), travel_height_m, intrinsics, extrinsics
    )

    x = (front_floor[0] + back_floor[0]) / 2
    y = (front_floor[1] + back_floor[1]) / 2
    heading = math.degrees(
        math.atan2(front_floor[1] - back_floor[1], front_floor[0] - back_floor[0])
    )

    confidence = float(min(front_area, back_area) / (MIN_MARKER_AREA_PX * 5))
    confidence = min(confidence, 1.0)

    return RobotPose(x_m=x, y_m=y, heading_deg=heading, confidence=confidence)
