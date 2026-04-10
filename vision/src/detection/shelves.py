"""Auto-detect shelf marker stickers in a camera frame and project them
to workspace world coordinates.

Used by `POST /layout/auto_detect` to seed or refresh shelves.json without
manual coordinate entry. The strategy is deliberately simple: run the
shelf-marker HSV mask, keep the top-N blobs by pixel area, sort them
left-to-right, and project each centroid through the current calibration.
Good enough for a well-lit top-down frame with a handful of coloured
stickers; not a replacement for a proper layout workflow when the scene
gets complex.
"""
from dataclasses import dataclass
import cv2
import numpy as np
from vision.src.calibration.parallax import project_pixel_to_floor
from vision.src.detection.hsv_ranges import HsvRange
from vision.src.detection.robot import (
    _all_blob_centroids,
    mask_for_ranges,
)
from vision.src.models import Intrinsics, Extrinsics


@dataclass(frozen=True)
class ShelfCandidate:
    pixel_cx: float
    pixel_cy: float
    pixel_area: int
    world_x_m: float
    world_y_m: float


def detect_shelf_candidates(
    frame: np.ndarray,
    marker_ranges: list[HsvRange],
    intrinsics: Intrinsics,
    extrinsics: Extrinsics,
    max_count: int,
    marker_height_m: float = 0.0,
) -> list[ShelfCandidate]:
    """Detect up to `max_count` coloured shelf markers in `frame` and project
    each centroid to the floor plane via the current calibration.

    The top `max_count` blobs by pixel area are taken, then sorted
    left-to-right by pixel x so the returned order is stable and matches
    the natural reading order of a horizontal shelf row.

    `marker_height_m` is the world z of the marker plane (0.0 for stickers
    on the floor/shelf top, nonzero if the markers sit above the floor).
    """
    undistorted = cv2.undistort(frame, intrinsics.camera_matrix, intrinsics.dist_coeffs)
    hsv = cv2.cvtColor(undistorted, cv2.COLOR_BGR2HSV)

    mask = mask_for_ranges(hsv, marker_ranges)
    blobs = _all_blob_centroids(mask)
    if not blobs:
        return []

    top = sorted(blobs, key=lambda b: -b[2])[:max_count]
    top_sorted = sorted(top, key=lambda b: b[0])

    candidates: list[ShelfCandidate] = []
    for cx, cy, area in top_sorted:
        world = project_pixel_to_floor(
            (cx, cy), marker_height_m, intrinsics, extrinsics
        )
        candidates.append(
            ShelfCandidate(
                pixel_cx=float(cx),
                pixel_cy=float(cy),
                pixel_area=int(area),
                world_x_m=float(world[0]),
                world_y_m=float(world[1]),
            )
        )
    return candidates
