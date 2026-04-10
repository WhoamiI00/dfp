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
)


def _mask_for_ranges(hsv: np.ndarray, ranges: list[tuple[np.ndarray, np.ndarray]]) -> np.ndarray:
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lo, hi in ranges:
        mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lo, hi))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def _largest_blob_centroid(mask: np.ndarray) -> tuple[float, float, int] | None:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    area = int(cv2.contourArea(largest))
    if area < MIN_MARKER_AREA_PX:
        return None
    M = cv2.moments(largest)
    if M["m00"] == 0:
        return None
    cx = M["m10"] / M["m00"]
    cy = M["m01"] / M["m00"]
    return cx, cy, area


def detect_robot(
    frame: np.ndarray,
    intrinsics: Intrinsics,
    extrinsics: Extrinsics,
    travel_height_m: float,
) -> RobotPose | None:
    """Detect the robot's pose in a BGR frame. Returns None if markers are missing."""
    undistorted = cv2.undistort(frame, intrinsics.camera_matrix, intrinsics.dist_coeffs)
    hsv = cv2.cvtColor(undistorted, cv2.COLOR_BGR2HSV)

    red_mask = _mask_for_ranges(hsv, RED_HSV_RANGES)
    green_mask = _mask_for_ranges(hsv, GREEN_HSV_RANGES)

    red_blob = _largest_blob_centroid(red_mask)
    green_blob = _largest_blob_centroid(green_mask)
    if red_blob is None or green_blob is None:
        return None

    red_cx, red_cy, red_area = red_blob
    green_cx, green_cy, green_area = green_blob

    red_floor = project_pixel_to_floor(
        (red_cx, red_cy), travel_height_m, intrinsics, extrinsics
    )
    green_floor = project_pixel_to_floor(
        (green_cx, green_cy), travel_height_m, intrinsics, extrinsics
    )

    x = (red_floor[0] + green_floor[0]) / 2
    y = (red_floor[1] + green_floor[1]) / 2
    heading = math.degrees(
        math.atan2(red_floor[1] - green_floor[1], red_floor[0] - green_floor[0])
    )

    confidence = float(min(red_area, green_area) / (MIN_MARKER_AREA_PX * 5))
    confidence = min(confidence, 1.0)

    return RobotPose(x_m=x, y_m=y, heading_deg=heading, confidence=confidence)
