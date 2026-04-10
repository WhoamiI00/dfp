"""ArUco extrinsic calibration from floor markers."""
from pathlib import Path
import numpy as np
import cv2
import yaml
from vision.src.models import Extrinsics, ExtrinsicMarker, Intrinsics


ARUCO_DICT = cv2.aruco.DICT_4X4_50


class ExtrinsicCalibrationError(Exception):
    pass


def save_extrinsics(extrinsics: Extrinsics, path: Path) -> None:
    data = {
        "rvec": extrinsics.rvec.tolist(),
        "tvec": extrinsics.tvec.tolist(),
        "floor_reference_markers": [
            {"id": m.id, "workspace_xy_m": list(m.workspace_xy_m)}
            for m in extrinsics.floor_reference_markers
        ],
        "calibration_error_px": float(extrinsics.calibration_error_px),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.safe_dump(data, f)


def load_extrinsics(path: Path) -> Extrinsics:
    with path.open("r") as f:
        data = yaml.safe_load(f)
    return Extrinsics(
        rvec=np.array(data["rvec"], dtype=np.float64),
        tvec=np.array(data["tvec"], dtype=np.float64),
        floor_reference_markers=[
            ExtrinsicMarker(id=int(m["id"]), workspace_xy_m=tuple(m["workspace_xy_m"]))
            for m in data["floor_reference_markers"]
        ],
        calibration_error_px=float(data["calibration_error_px"]),
    )


def calibrate_from_frame(
    frame: np.ndarray,
    expected_markers: list[ExtrinsicMarker],
    intrinsics: Intrinsics,
) -> Extrinsics:
    """Detect ArUco markers in `frame` and compute extrinsics via solvePnP.

    Raises ExtrinsicCalibrationError if not all expected markers are found.
    """
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, params)
    corners, ids, _ = detector.detectMarkers(frame)

    if ids is None:
        raise ExtrinsicCalibrationError(
            "No ArUco markers detected",
        )
    ids = ids.flatten().tolist()

    expected_ids = [m.id for m in expected_markers]
    missing = [i for i in expected_ids if i not in ids]
    if missing:
        raise ExtrinsicCalibrationError(
            f"Missing expected ArUco marker IDs: {missing}; found: {ids}"
        )

    # Build world-point <-> image-point correspondences (marker center points).
    id_to_center_px: dict[int, np.ndarray] = {}
    for marker_id, marker_corners in zip(ids, corners):
        center = marker_corners[0].mean(axis=0)
        id_to_center_px[int(marker_id)] = center

    object_points = []
    image_points = []
    for m in expected_markers:
        object_points.append([m.workspace_xy_m[0], m.workspace_xy_m[1], 0.0])
        image_points.append(id_to_center_px[m.id])
    object_points = np.array(object_points, dtype=np.float64)
    image_points = np.array(image_points, dtype=np.float64)

    ok, rvec, tvec = cv2.solvePnP(
        object_points,
        image_points,
        intrinsics.camera_matrix,
        intrinsics.dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not ok:
        raise ExtrinsicCalibrationError("solvePnP failed")

    # Compute reprojection error for diagnostics.
    projected, _ = cv2.projectPoints(
        object_points, rvec, tvec, intrinsics.camera_matrix, intrinsics.dist_coeffs
    )
    error = float(np.linalg.norm(projected.reshape(-1, 2) - image_points, axis=1).mean())

    return Extrinsics(
        rvec=rvec.flatten(),
        tvec=tvec.flatten(),
        floor_reference_markers=list(expected_markers),
        calibration_error_px=error,
    )
