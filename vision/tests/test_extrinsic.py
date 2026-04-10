"""Extrinsic calibration round-trip test."""
import numpy as np
from pathlib import Path
from vision.src.calibration.extrinsic import save_extrinsics, load_extrinsics
from vision.src.models import Extrinsics, ExtrinsicMarker


def test_extrinsic_round_trip(tmp_path: Path):
    original = Extrinsics(
        rvec=np.array([0.1, 0.2, 0.3]),
        tvec=np.array([0.5, 0.5, 2.0]),
        floor_reference_markers=[
            ExtrinsicMarker(id=0, workspace_xy_m=(0.0, 0.0)),
            ExtrinsicMarker(id=1, workspace_xy_m=(2.5, 0.0)),
            ExtrinsicMarker(id=2, workspace_xy_m=(2.5, 2.5)),
            ExtrinsicMarker(id=3, workspace_xy_m=(0.0, 2.5)),
        ],
        calibration_error_px=1.1,
    )
    path = tmp_path / "extrinsics.yaml"
    save_extrinsics(original, path)
    loaded = load_extrinsics(path)
    assert np.allclose(loaded.rvec, original.rvec)
    assert np.allclose(loaded.tvec, original.tvec)
    assert len(loaded.floor_reference_markers) == 4
    assert loaded.floor_reference_markers[1].workspace_xy_m == (2.5, 0.0)
    assert loaded.calibration_error_px == 1.1
