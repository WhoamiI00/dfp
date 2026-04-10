"""Shared pytest fixtures."""
import numpy as np
import pytest
import cv2
from vision.src.models import Intrinsics, Extrinsics, ExtrinsicMarker


@pytest.fixture
def synthetic_intrinsics() -> Intrinsics:
    """A perfect pinhole camera at 1280x720 with focal length 800 px."""
    K = np.array([
        [800.0, 0.0, 640.0],
        [0.0, 800.0, 360.0],
        [0.0, 0.0, 1.0],
    ])
    dist = np.zeros(5)
    return Intrinsics(
        image_size=(1280, 720),
        camera_matrix=K,
        dist_coeffs=dist,
        calibration_error_px=0.0,
        captured_images=0,
    )


@pytest.fixture
def synthetic_extrinsics() -> Extrinsics:
    """Camera positioned at workspace corner (-0.5, -0.5, 2.0), looking at center."""
    # Camera at (-0.5, -0.5, 2.0) world, looking toward (1.25, 1.25, 0)
    cam_pos_world = np.array([-0.5, -0.5, 2.0])
    target_world = np.array([1.25, 1.25, 0.0])
    forward = target_world - cam_pos_world
    forward = forward / np.linalg.norm(forward)
    world_up = np.array([0.0, 0.0, 1.0])
    right = np.cross(forward, world_up)
    right = right / np.linalg.norm(right)
    down = np.cross(forward, right)  # camera Y axis points down

    # Rotation matrix: camera axes in world frame = [right, down, forward]
    R_cw = np.column_stack([right, down, forward])
    # We need world-to-camera rotation
    R_wc = R_cw.T
    rvec, _ = cv2.Rodrigues(R_wc)
    tvec = -R_wc @ cam_pos_world

    return Extrinsics(
        rvec=rvec.flatten(),
        tvec=tvec.flatten(),
        floor_reference_markers=[
            ExtrinsicMarker(id=0, workspace_xy_m=(0.0, 0.0)),
            ExtrinsicMarker(id=1, workspace_xy_m=(2.5, 0.0)),
            ExtrinsicMarker(id=2, workspace_xy_m=(2.5, 2.5)),
            ExtrinsicMarker(id=3, workspace_xy_m=(0.0, 2.5)),
        ],
        calibration_error_px=0.0,
    )


def project_world_to_pixel(
    world_xyz: np.ndarray,
    intrinsics: Intrinsics,
    extrinsics: Extrinsics,
) -> tuple[float, float]:
    """Helper: forward-project a world point to a pixel (for test setup)."""
    R, _ = cv2.Rodrigues(extrinsics.rvec)
    cam = R @ world_xyz + extrinsics.tvec
    if cam[2] <= 0:
        raise ValueError("Point is behind camera")
    u = intrinsics.camera_matrix[0, 0] * (cam[0] / cam[2]) + intrinsics.camera_matrix[0, 2]
    v = intrinsics.camera_matrix[1, 1] * (cam[1] / cam[2]) + intrinsics.camera_matrix[1, 2]
    return float(u), float(v)
