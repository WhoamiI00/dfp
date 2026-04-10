"""Synthetic calibration for prototype/dev use without a real camera.

Assumes a top-down overhead camera centered over the workspace. Produces
intrinsics and extrinsics consistent with that assumption so the full
vision pipeline can run on AI-generated top-down test images.

This is NOT a replacement for real chessboard + ArUco calibration.
Use it only with images that look like a direct overhead view of the
workspace.
"""
import cv2
import numpy as np
from vision.src.models import Extrinsics, ExtrinsicMarker, Intrinsics, Settings


SYNTHETIC_CAMERA_HEIGHT_M = 2.5


def build_synthetic_calibration(
    frame: np.ndarray, settings: Settings
) -> tuple[Intrinsics, Extrinsics]:
    """Build intrinsics + extrinsics for a synthetic overhead camera that
    makes the workspace width exactly fill the image width.
    """
    height_px, width_px = frame.shape[:2]
    ws_w = settings.workspace.width_m
    ws_h = settings.workspace.height_m

    fx = fy = float(width_px) * SYNTHETIC_CAMERA_HEIGHT_M / ws_w
    cx = float(width_px) / 2.0
    cy = float(height_px) / 2.0

    K = np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64)
    dist = np.zeros(5, dtype=np.float64)

    intrinsics = Intrinsics(
        image_size=(width_px, height_px),
        camera_matrix=K,
        dist_coeffs=dist,
        calibration_error_px=0.0,
        captured_images=0,
    )

    # Camera centered over workspace, looking straight down.
    # World +X -> cam +X, world +Y -> cam -Y, world +Z -> cam -Z.
    R = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, -1.0, 0.0],
            [0.0, 0.0, -1.0],
        ],
        dtype=np.float64,
    )
    rvec, _ = cv2.Rodrigues(R)

    cam_origin = np.array([ws_w / 2.0, ws_h / 2.0, SYNTHETIC_CAMERA_HEIGHT_M])
    tvec = -R @ cam_origin

    expected_corners = [
        ExtrinsicMarker(id=0, workspace_xy_m=(0.0, 0.0)),
        ExtrinsicMarker(id=1, workspace_xy_m=(ws_w, 0.0)),
        ExtrinsicMarker(id=2, workspace_xy_m=(ws_w, ws_h)),
        ExtrinsicMarker(id=3, workspace_xy_m=(0.0, ws_h)),
    ]

    extrinsics = Extrinsics(
        rvec=rvec.flatten(),
        tvec=tvec.flatten(),
        floor_reference_markers=expected_corners,
        calibration_error_px=0.0,
    )

    return intrinsics, extrinsics
