"""Chessboard intrinsic calibration + load/save."""
from pathlib import Path
import numpy as np
import cv2
import yaml
from vision.src.models import Intrinsics


CHESSBOARD_INNER_CORNERS = (9, 6)  # inner corner count, not square count


class IntrinsicCalibrationError(Exception):
    pass


def save_intrinsics(intrinsics: Intrinsics, path: Path) -> None:
    data = {
        "image_size": list(intrinsics.image_size),
        "camera_matrix": intrinsics.camera_matrix.tolist(),
        "dist_coeffs": intrinsics.dist_coeffs.tolist(),
        "calibration_error_px": float(intrinsics.calibration_error_px),
        "captured_images": int(intrinsics.captured_images),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.safe_dump(data, f)


def load_intrinsics(path: Path) -> Intrinsics:
    with path.open("r") as f:
        data = yaml.safe_load(f)
    return Intrinsics(
        image_size=tuple(data["image_size"]),
        camera_matrix=np.array(data["camera_matrix"], dtype=np.float64),
        dist_coeffs=np.array(data["dist_coeffs"], dtype=np.float64),
        calibration_error_px=float(data["calibration_error_px"]),
        captured_images=int(data["captured_images"]),
    )


def calibrate_from_images(images: list[np.ndarray]) -> Intrinsics:
    """Calibrate a camera from chessboard images.

    Each image must show the 9x6 chessboard pattern fully visible.
    Raises IntrinsicCalibrationError if fewer than 8 valid images or
    reprojection error > 2.0 px.
    """
    if len(images) < 8:
        raise IntrinsicCalibrationError(
            f"Need at least 8 chessboard images, got {len(images)}"
        )

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    objp = np.zeros((CHESSBOARD_INNER_CORNERS[0] * CHESSBOARD_INNER_CORNERS[1], 3), np.float32)
    objp[:, :2] = np.mgrid[
        0:CHESSBOARD_INNER_CORNERS[0], 0:CHESSBOARD_INNER_CORNERS[1]
    ].T.reshape(-1, 2)

    object_points = []
    image_points = []
    image_size = None
    for img in images:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if image_size is None:
            image_size = (gray.shape[1], gray.shape[0])
        ret, corners = cv2.findChessboardCorners(gray, CHESSBOARD_INNER_CORNERS, None)
        if not ret:
            continue
        refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        object_points.append(objp)
        image_points.append(refined)

    if len(object_points) < 8:
        raise IntrinsicCalibrationError(
            f"Only {len(object_points)} of {len(images)} images had detectable chessboards; need at least 8"
        )

    ret, K, dist, _, _ = cv2.calibrateCamera(
        object_points, image_points, image_size, None, None
    )
    if ret > 2.0:
        raise IntrinsicCalibrationError(
            f"Reprojection error too high: {ret:.2f} px (max 2.0)"
        )

    return Intrinsics(
        image_size=image_size,
        camera_matrix=K,
        dist_coeffs=dist.flatten(),
        calibration_error_px=float(ret),
        captured_images=len(object_points),
    )
