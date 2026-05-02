"""Shared pytest fixtures."""
from pathlib import Path
import shutil
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


@pytest.fixture
def tmp_config(tmp_path: Path):
    import yaml
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    source_config = Path(__file__).resolve().parents[1] / "config"
    with (source_config / "settings.yaml").open("r") as f:
        settings_data = yaml.safe_load(f)
    settings_data["robot"]["markers"]["front_color"] = "red"
    settings_data["robot"]["markers"]["back_color"] = "green"
    with (config_dir / "settings.yaml").open("w") as f:
        yaml.safe_dump(settings_data, f)
    shutil.copy(source_config / "shelves.json", config_dir / "shelves.json")
    return config_dir


@pytest.fixture
def client(tmp_config, synthetic_intrinsics, synthetic_extrinsics):
    from fastapi.testclient import TestClient
    from vision.src.api.server import create_app
    from vision.src.api.camera import FakeCamera, SwitchableCamera
    from vision.src.api.routes import Paths, set_state
    from vision.src.calibration.intrinsic import save_intrinsics
    from vision.src.calibration.extrinsic import save_extrinsics

    frame = make_synthetic_robot_image(
        synthetic_intrinsics, synthetic_extrinsics,
        robot_xy_m=(1.25, 1.25), heading_deg=0.0, height_m=0.30,
    )
    camera = SwitchableCamera(FakeCamera(frame))
    app = create_app(camera=camera)

    from vision.src.inventory.orders import OrderQueue

    paths = Paths()
    paths.settings = tmp_config / "settings.yaml"
    paths.shelves = tmp_config / "shelves.json"
    paths.intrinsics = tmp_config / "camera_intrinsics.yaml"
    paths.extrinsics = tmp_config / "camera_extrinsics.yaml"
    paths.custom_hsv = tmp_config / "custom_hsv.yaml"
    paths.orders_db = tmp_config / "orders.db"
    save_intrinsics(synthetic_intrinsics, paths.intrinsics)
    save_extrinsics(synthetic_extrinsics, paths.extrinsics)
    set_state(paths, camera, orders=OrderQueue(paths.orders_db))

    return TestClient(app)


def make_synthetic_robot_image(
    intrinsics,
    extrinsics,
    robot_xy_m: tuple[float, float],
    heading_deg: float,
    height_m: float,
    image_size: tuple[int, int] = (1280, 720),
) -> np.ndarray:
    """Draw a synthetic scene with the two robot markers projected to pixel space."""
    img = np.full((image_size[1], image_size[0], 3), 40, dtype=np.uint8)

    marker_offset = 0.15  # 15 cm between red (front) and green (back)
    rad = np.radians(heading_deg)
    dx = np.cos(rad) * marker_offset / 2
    dy = np.sin(rad) * marker_offset / 2
    red_world = np.array([robot_xy_m[0] + dx, robot_xy_m[1] + dy, height_m])
    green_world = np.array([robot_xy_m[0] - dx, robot_xy_m[1] - dy, height_m])

    red_u, red_v = project_world_to_pixel(red_world, intrinsics, extrinsics)
    green_u, green_v = project_world_to_pixel(green_world, intrinsics, extrinsics)

    cv2.circle(img, (int(red_u), int(red_v)), 25, (0, 0, 255), -1)
    cv2.circle(img, (int(green_u), int(green_v)), 25, (0, 255, 0), -1)
    return img
