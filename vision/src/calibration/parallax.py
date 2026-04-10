"""Pixel-to-floor projection with height correction."""
import numpy as np
import cv2
from vision.src.models import Intrinsics, Extrinsics


def project_pixel_to_floor(
    pixel_uv: tuple[float, float],
    height_above_floor_m: float,
    intrinsics: Intrinsics,
    extrinsics: Extrinsics,
) -> tuple[float, float]:
    """Back-project a pixel observed at a known height above the floor
    to the corresponding (x, y) point in workspace coordinates.

    The marker is observed in the image at pixel (u, v). It physically lives at
    height `h` above the floor. We back-project the pixel to a ray in camera
    space, transform it to world space, and intersect with the plane z = h.
    """
    u, v = pixel_uv

    # 1. Undistort the pixel to normalized ideal-camera coordinates.
    pts = np.array([[[u, v]]], dtype=np.float64)
    undistorted = cv2.undistortPoints(pts, intrinsics.camera_matrix, intrinsics.dist_coeffs)
    x_n, y_n = undistorted[0, 0]

    # 2. Build a ray in camera coordinates: direction = (x_n, y_n, 1), origin = 0.
    ray_cam = np.array([x_n, y_n, 1.0])

    # 3. Transform ray to world coordinates.
    R, _ = cv2.Rodrigues(extrinsics.rvec)
    # World-to-camera: cam = R @ world + t. Camera-to-world: world = R^T @ (cam - t).
    R_inv = R.T
    cam_origin_world = -R_inv @ extrinsics.tvec
    ray_world = R_inv @ ray_cam

    # 4. Intersect with plane z = height_above_floor_m.
    # Parametric ray: P = cam_origin_world + s * ray_world. Solve for z == height.
    if abs(ray_world[2]) < 1e-9:
        raise ValueError("Ray is parallel to the floor plane; cannot intersect.")
    s = (height_above_floor_m - cam_origin_world[2]) / ray_world[2]
    if s <= 0:
        raise ValueError("Intersection is behind the camera.")
    intersection = cam_origin_world + s * ray_world

    # 5. Return (x, y) — intersection is already at z == height, the floor projection is (x, y).
    return float(intersection[0]), float(intersection[1])
