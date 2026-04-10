"""Tests for intrinsic calibration save/load round-trip."""
import numpy as np
from pathlib import Path
from vision.src.calibration.intrinsic import save_intrinsics, load_intrinsics
from vision.src.models import Intrinsics


def test_intrinsic_round_trip(tmp_path: Path):
    original = Intrinsics(
        image_size=(1280, 720),
        camera_matrix=np.array([[800.0, 0, 640], [0, 800, 360], [0, 0, 1]]),
        dist_coeffs=np.array([0.1, -0.05, 0.001, 0.002, 0.0]),
        calibration_error_px=0.42,
        captured_images=15,
    )
    path = tmp_path / "intrinsics.yaml"
    save_intrinsics(original, path)
    loaded = load_intrinsics(path)
    assert loaded.image_size == original.image_size
    assert np.allclose(loaded.camera_matrix, original.camera_matrix)
    assert np.allclose(loaded.dist_coeffs, original.dist_coeffs)
    assert loaded.calibration_error_px == original.calibration_error_px
    assert loaded.captured_images == original.captured_images
