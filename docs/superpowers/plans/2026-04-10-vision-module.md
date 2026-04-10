# Vision Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone `dfp/vision/` Python module and a `/vision` route in `web-app/` that, together, detect a robot's pose from a corner-mounted camera snapshot, let the user edit a shelf layout via a web UI, and plan pick-and-place paths for a non-holonomic differential-drive robot.

**Architecture:** Python FastAPI backend exposes calibration, capture, detection, and planning endpoints; a new Next.js `/vision` route is a thin client with three tabs (calibration, layout editor, plan & run) talking to the backend over HTTP. Classical CV only — OpenCV for calibration and detection, custom A* with non-holonomic decomposition for planning. Snapshot-based workflow — no continuous video in phase 1.

**Tech Stack:** Python 3.10+, OpenCV 4.x, NumPy, FastAPI, pydantic, pytest, PyYAML; Next.js 16 (App Router) + React 19 + TypeScript + Tailwind.

**Spec reference:** [docs/superpowers/specs/2026-04-10-vision-module-design.md](../specs/2026-04-10-vision-module-design.md)

---

## File Structure Map

Before tasks, here is every file that will be created and what it owns. Each file has one clear responsibility.

### Python backend (`vision/`)

| File | Responsibility |
|---|---|
| `vision/requirements.txt` | Python dependencies |
| `vision/README.md` | How to install, calibrate, run |
| `vision/__init__.py` | Package marker |
| `vision/config/settings.yaml` | Static config: workspace dims, robot spec, camera source |
| `vision/config/shelves.json` | Shelf layout (sample + edited via UI) |
| `vision/src/__init__.py` | Package marker |
| `vision/src/models.py` | Shared dataclasses: `Settings`, `Shelf`, `ApproachPoint`, `Intrinsics`, `Extrinsics`, `RobotPose`, `Waypoint` variants |
| `vision/src/calibration/__init__.py` | Package marker |
| `vision/src/calibration/intrinsic.py` | Chessboard calibration, load/save `camera_intrinsics.yaml` |
| `vision/src/calibration/extrinsic.py` | ArUco floor marker calibration, load/save `camera_extrinsics.yaml` |
| `vision/src/calibration/parallax.py` | `project_pixel_to_floor(pixel, height, intrinsics, extrinsics)` |
| `vision/src/detection/__init__.py` | Package marker |
| `vision/src/detection/hsv_ranges.py` | HSV ranges for red and green markers |
| `vision/src/detection/robot.py` | `detect_robot(frame, ...)` → `RobotPose \| None` |
| `vision/src/planning/__init__.py` | Package marker |
| `vision/src/planning/grid.py` | `build_occupancy_grid(shelves, settings)` |
| `vision/src/planning/astar.py` | `a_star(grid, start_cell, goal_cell)` |
| `vision/src/planning/motion.py` | `decompose_to_waypoints(cell_path, start_heading_deg, final_heading_deg, settings)` |
| `vision/src/planning/task.py` | `plan_navigate_to()`, `plan_pick_and_place()` |
| `vision/src/planning/errors.py` | `NoPathError`, `ApproachPointBlockedError` |
| `vision/src/rendering/__init__.py` | Package marker |
| `vision/src/rendering/overlay.py` | Draw shelves, robot, path on an image |
| `vision/src/api/__init__.py` | Package marker |
| `vision/src/api/schemas.py` | pydantic request/response models |
| `vision/src/api/config_loader.py` | Load/validate/save `settings.yaml` and `shelves.json` |
| `vision/src/api/camera.py` | Camera interface (`OpenCVCamera` + `FakeCamera` for tests) |
| `vision/src/api/routes.py` | Endpoint handlers |
| `vision/src/api/server.py` | FastAPI app with CORS + routes mounted |
| `vision/scripts/run_server.py` | `python -m vision.scripts.run_server` entry point |
| `vision/scripts/capture_chessboard.py` | Helper to capture chessboard images |
| `vision/tests/__init__.py` | Package marker |
| `vision/tests/conftest.py` | pytest fixtures: synthetic camera, mock configs, fixture paths |
| `vision/tests/fixtures/` | Sample images + mock YAML/JSON configs |
| `vision/tests/test_parallax.py` | Unit tests for parallax math |
| `vision/tests/test_intrinsic.py` | Load/save + basic chessboard test |
| `vision/tests/test_extrinsic.py` | ArUco calibration test with synthetic image |
| `vision/tests/test_detection.py` | Robot detection against fixture images |
| `vision/tests/test_grid.py` | Occupancy grid construction tests |
| `vision/tests/test_astar.py` | A* search tests |
| `vision/tests/test_motion.py` | Non-holonomic decomposition tests |
| `vision/tests/test_task.py` | Task composition tests |
| `vision/tests/test_api.py` | FastAPI integration tests with fake camera |

### Frontend (`web-app/`)

| File | Responsibility |
|---|---|
| `web-app/app/vision/page.tsx` | `/vision` route: tab container |
| `web-app/app/vision/components/CalibrationTab.tsx` | Calibration tab UI |
| `web-app/app/vision/components/LayoutEditorTab.tsx` | SVG layout editor |
| `web-app/app/vision/components/PlanRunTab.tsx` | Plan & run UI |
| `web-app/app/vision/components/WaypointList.tsx` | Reusable waypoint list |
| `web-app/app/vision/lib/api.ts` | `fetch` wrappers for backend |
| `web-app/app/vision/lib/types.ts` | TypeScript types matching backend schemas |

---

## Conventions used throughout

- **Workspace coordinate system:** origin `(0, 0)` at the bottom-left ArUco marker, X axis pointing right, Y axis pointing forward (away from origin). All angles in degrees, counter-clockwise positive from the +X axis. 0° = facing +X, 90° = facing +Y. This convention is followed by every function that deals with position/heading.
- **Grid coordinates:** `(row, col)` with row = 0 at the bottom and column = 0 at the left, matching the workspace axes after flipping row order. Grid cell `(r, c)` has world center `(c * cell_size + cell_size/2, r * cell_size + cell_size/2)`.
- **Chessboard convention:** `9x6` refers to **inner corner count** (the OpenCV default), i.e. 10x7 physical squares. Square size does not affect intrinsics; defaulted to 25 mm in the script for documentation.
- **Direction tolerance in motion decomposition:** two consecutive cell-to-cell segments are considered "same direction" if their heading differs by `< 5°`. Consecutive same-direction segments are collapsed into a single `drive`.
- **Commit discipline:** each task ends with a `git commit`. Commit messages use `feat:`, `test:`, `chore:`, `docs:` prefixes.

---

## Task list

### Phase 0 — Scaffold

### Task 0.1: Directory scaffold

**Files:**
- Create: `vision/README.md`
- Create: `vision/requirements.txt`
- Create: `vision/__init__.py`
- Create: `vision/src/__init__.py`
- Create: `vision/src/calibration/__init__.py`
- Create: `vision/src/detection/__init__.py`
- Create: `vision/src/planning/__init__.py`
- Create: `vision/src/rendering/__init__.py`
- Create: `vision/src/api/__init__.py`
- Create: `vision/tests/__init__.py`
- Create: `vision/tests/fixtures/.gitkeep`
- Create: `vision/scripts/.gitkeep`

- [ ] **Step 1: Create empty package files**

Each `__init__.py` is a single line:
```python
"""Vision module for DFP robot navigation."""
```

Except `vision/src/calibration/__init__.py` etc., which are:
```python
"""<module> package."""
```

- [ ] **Step 2: Create `vision/requirements.txt`**

```
opencv-python>=4.9.0
opencv-contrib-python>=4.9.0
numpy>=1.26.0
pyyaml>=6.0
pydantic>=2.5.0
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.9
pytest>=8.0.0
```

Note: `opencv-contrib-python` is required for ArUco detection.

- [ ] **Step 3: Create `vision/README.md`**

```markdown
# vision — Robot detection and path planning

Phase 1 of the DFP reimplementation. Detects a robot's pose from a corner-mounted camera snapshot and plans pick-and-place paths for a non-holonomic differential-drive robot. See [the design spec](../docs/superpowers/specs/2026-04-10-vision-module-design.md) for details.

## Install

```bash
cd vision
pip install -r requirements.txt
```

## Run

```bash
python -m vision.scripts.run_server
```

Server starts on `http://localhost:8100`. Open the Next.js dev server (`cd ../web-app && npm run dev`) and visit `http://localhost:3000/vision`.

## Calibrate

1. **Intrinsic** (one-time): print a 9x6 chessboard, upload ~15 photos via the Calibration tab.
2. **Extrinsic** (per-setup): print 4 ArUco markers (DICT_4X4_50, IDs 0-3), place at workspace corners, click "Run extrinsic calibration".

## Test

```bash
pytest vision/tests -v
```
```

- [ ] **Step 4: Commit**

```bash
git add vision/
git commit -m "chore: scaffold vision module directory structure"
```

---

### Task 0.2: Shared data models

**Files:**
- Create: `vision/src/models.py`

- [ ] **Step 1: Write `models.py` with all shared dataclasses**

```python
"""Shared data models for the vision module."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
import numpy as np


# --- Workspace / config -----------------------------------------------------

@dataclass(frozen=True)
class WorkspaceConfig:
    width_m: float
    height_m: float
    cell_size_m: float


@dataclass(frozen=True)
class RobotMarkers:
    front_color: str
    back_color: str


@dataclass(frozen=True)
class RobotConfig:
    footprint_m: tuple[float, float]
    travel_height_m: float
    markers: RobotMarkers


@dataclass(frozen=True)
class CameraConfig:
    source: int | str
    resolution: tuple[int, int]


@dataclass(frozen=True)
class PlannerConfig:
    obstacle_inflation_m: float


@dataclass(frozen=True)
class Settings:
    workspace: WorkspaceConfig
    robot: RobotConfig
    camera: CameraConfig
    planner: PlannerConfig


# --- Shelves ----------------------------------------------------------------

@dataclass(frozen=True)
class ApproachPoint:
    x_m: float
    y_m: float
    heading_deg: float


@dataclass(frozen=True)
class Shelf:
    id: str
    x_m: float
    y_m: float
    width_m: float
    length_m: float
    rotation_deg: float
    approach_point: ApproachPoint


# --- Calibration ------------------------------------------------------------

@dataclass(frozen=True)
class Intrinsics:
    image_size: tuple[int, int]
    camera_matrix: np.ndarray  # 3x3
    dist_coeffs: np.ndarray    # (5,)
    calibration_error_px: float
    captured_images: int


@dataclass(frozen=True)
class ExtrinsicMarker:
    id: int
    workspace_xy_m: tuple[float, float]


@dataclass(frozen=True)
class Extrinsics:
    rvec: np.ndarray  # (3,)
    tvec: np.ndarray  # (3,)
    floor_reference_markers: list[ExtrinsicMarker]
    calibration_error_px: float


# --- Detection --------------------------------------------------------------

@dataclass(frozen=True)
class RobotPose:
    x_m: float
    y_m: float
    heading_deg: float
    confidence: float


# --- Waypoints --------------------------------------------------------------

@dataclass(frozen=True)
class Pose2D:
    x_m: float
    y_m: float
    heading_deg: float


@dataclass(frozen=True)
class TurnWaypoint:
    type: Literal["turn"] = "turn"
    target_heading_deg: float = 0.0
    from_pose: Pose2D = field(default_factory=lambda: Pose2D(0, 0, 0))


@dataclass(frozen=True)
class DriveWaypoint:
    type: Literal["drive"] = "drive"
    distance_m: float = 0.0
    from_pose: Pose2D = field(default_factory=lambda: Pose2D(0, 0, 0))
    to_pose: Pose2D = field(default_factory=lambda: Pose2D(0, 0, 0))


@dataclass(frozen=True)
class GrabWaypoint:
    type: Literal["grab"] = "grab"
    shelf_id: str = ""


@dataclass(frozen=True)
class PlaceWaypoint:
    type: Literal["place"] = "place"
    shelf_id: str = ""


@dataclass(frozen=True)
class ArriveWaypoint:
    type: Literal["arrive"] = "arrive"
    shelf_id: str = ""


Waypoint = TurnWaypoint | DriveWaypoint | GrabWaypoint | PlaceWaypoint | ArriveWaypoint
```

- [ ] **Step 2: Commit**

```bash
git add vision/src/models.py
git commit -m "feat(vision): add shared data models"
```

---

### Task 0.3: Config files

**Files:**
- Create: `vision/config/settings.yaml`
- Create: `vision/config/shelves.json`
- Create: `vision/config/.gitignore` — ignore generated calibration files

- [ ] **Step 1: Write `vision/config/settings.yaml`**

```yaml
workspace:
  width_m: 2.5
  height_m: 2.5
  cell_size_m: 0.25
robot:
  footprint_m: [0.5, 0.5]
  travel_height_m: 0.30
  markers:
    front_color: red
    back_color: green
camera:
  source: 0
  resolution: [1280, 720]
planner:
  obstacle_inflation_m: 0.10
```

- [ ] **Step 2: Write `vision/config/shelves.json` with 2 sample shelves**

```json
{
  "shelves": [
    {
      "id": "shelf_A",
      "x_m": 0.5,
      "y_m": 1.25,
      "width_m": 0.5,
      "length_m": 1.0,
      "rotation_deg": 0,
      "approach_point": {
        "x_m": 1.0,
        "y_m": 1.25,
        "heading_deg": 180
      }
    },
    {
      "id": "shelf_B",
      "x_m": 2.0,
      "y_m": 1.25,
      "width_m": 0.5,
      "length_m": 1.0,
      "rotation_deg": 0,
      "approach_point": {
        "x_m": 1.5,
        "y_m": 1.25,
        "heading_deg": 0
      }
    }
  ]
}
```

- [ ] **Step 3: Write `vision/config/.gitignore`**

```
camera_intrinsics.yaml
camera_extrinsics.yaml
```

Generated calibration files are machine-specific and should not be committed.

- [ ] **Step 4: Commit**

```bash
git add vision/config/
git commit -m "chore(vision): add default settings and sample shelves config"
```

---

### Phase 1 — Parallax math (load-bearing TDD)

### Task 1.1: Parallax — test first

**Files:**
- Create: `vision/tests/test_parallax.py`
- Create: `vision/tests/conftest.py`

The parallax function is the single most important math in the project. We write three tests before implementing it.

- [ ] **Step 1: Write `vision/tests/conftest.py` with a synthetic camera fixture**

```python
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
```

- [ ] **Step 2: Write `vision/tests/test_parallax.py` with three tests**

```python
"""Tests for parallax pixel-to-floor projection."""
import numpy as np
import pytest
from vision.src.calibration.parallax import project_pixel_to_floor
from vision.tests.conftest import project_world_to_pixel


def test_parallax_height_zero_identity(synthetic_intrinsics, synthetic_extrinsics):
    """A point on the floor (z=0) should project back to its own floor position."""
    world = np.array([1.0, 1.5, 0.0])
    u, v = project_world_to_pixel(world, synthetic_intrinsics, synthetic_extrinsics)
    x, y = project_pixel_to_floor((u, v), 0.0, synthetic_intrinsics, synthetic_extrinsics)
    assert abs(x - 1.0) < 0.01, f"x error: {x - 1.0}"
    assert abs(y - 1.5) < 0.01, f"y error: {y - 1.5}"


def test_parallax_with_height(synthetic_intrinsics, synthetic_extrinsics):
    """A marker 30 cm above the floor at (1.0, 1.0) should resolve to (1.0, 1.0)."""
    height = 0.30
    world = np.array([1.0, 1.0, height])
    u, v = project_world_to_pixel(world, synthetic_intrinsics, synthetic_extrinsics)
    x, y = project_pixel_to_floor((u, v), height, synthetic_intrinsics, synthetic_extrinsics)
    assert abs(x - 1.0) < 0.01, f"x error: {x - 1.0}"
    assert abs(y - 1.0) < 0.01, f"y error: {y - 1.0}"


@pytest.mark.parametrize("x,y,h", [
    (0.5, 0.5, 0.10),
    (1.25, 1.25, 0.30),
    (2.0, 0.5, 0.30),
    (0.5, 2.0, 0.50),
])
def test_parallax_across_workspace(synthetic_intrinsics, synthetic_extrinsics, x, y, h):
    """Parallax correction should be accurate within 1 cm across the workspace."""
    world = np.array([x, y, h])
    u, v = project_world_to_pixel(world, synthetic_intrinsics, synthetic_extrinsics)
    rx, ry = project_pixel_to_floor((u, v), h, synthetic_intrinsics, synthetic_extrinsics)
    assert abs(rx - x) < 0.01, f"x error at ({x},{y},{h}): {rx - x}"
    assert abs(ry - y) < 0.01, f"y error at ({x},{y},{h}): {ry - y}"
```

- [ ] **Step 3: Run tests — expect import failure**

```bash
pytest vision/tests/test_parallax.py -v
```

Expected: import error — `project_pixel_to_floor` does not exist yet.

- [ ] **Step 4: Commit the failing tests**

```bash
git add vision/tests/
git commit -m "test(vision): add failing parallax tests"
```

---

### Task 1.2: Parallax — implementation

**Files:**
- Create: `vision/src/calibration/parallax.py`

- [ ] **Step 1: Write `parallax.py`**

```python
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
```

- [ ] **Step 2: Run tests — expect pass**

```bash
pytest vision/tests/test_parallax.py -v
```

Expected: all 6 tests pass (3 named + 3 parametrized).

- [ ] **Step 3: Commit**

```bash
git add vision/src/calibration/parallax.py
git commit -m "feat(vision): implement parallax pixel-to-floor projection"
```

---

### Phase 2 — Intrinsic and extrinsic calibration

### Task 2.1: Intrinsic calibration load/save

**Files:**
- Create: `vision/src/calibration/intrinsic.py`
- Create: `vision/tests/test_intrinsic.py`

- [ ] **Step 1: Write `vision/tests/test_intrinsic.py`**

```python
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
```

- [ ] **Step 2: Write `vision/src/calibration/intrinsic.py`**

```python
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
```

- [ ] **Step 3: Run tests**

```bash
pytest vision/tests/test_intrinsic.py -v
```

Expected: `test_intrinsic_round_trip` passes.

- [ ] **Step 4: Commit**

```bash
git add vision/src/calibration/intrinsic.py vision/tests/test_intrinsic.py
git commit -m "feat(vision): add intrinsic chessboard calibration"
```

---

### Task 2.2: Extrinsic calibration

**Files:**
- Create: `vision/src/calibration/extrinsic.py`
- Create: `vision/tests/test_extrinsic.py`

- [ ] **Step 1: Write `vision/tests/test_extrinsic.py`**

```python
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
```

- [ ] **Step 2: Write `vision/src/calibration/extrinsic.py`**

```python
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

    # Build world-point ↔ image-point correspondences (marker center points).
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
```

- [ ] **Step 3: Run tests**

```bash
pytest vision/tests/test_extrinsic.py -v
```

Expected: `test_extrinsic_round_trip` passes.

- [ ] **Step 4: Commit**

```bash
git add vision/src/calibration/extrinsic.py vision/tests/test_extrinsic.py
git commit -m "feat(vision): add ArUco extrinsic calibration"
```

---

### Phase 3 — Robot detection

### Task 3.1: HSV ranges module

**Files:**
- Create: `vision/src/detection/hsv_ranges.py`

- [ ] **Step 1: Write `hsv_ranges.py`**

```python
"""HSV color ranges for robot markers. Tune these per lighting setup."""
import numpy as np


# Red hue wraps around 0/180 in OpenCV's HSV, so use two ranges.
RED_HSV_RANGES = [
    (np.array([0, 120, 70]), np.array([10, 255, 255])),
    (np.array([170, 120, 70]), np.array([180, 255, 255])),
]

GREEN_HSV_RANGES = [
    (np.array([40, 80, 70]), np.array([80, 255, 255])),
]

MIN_MARKER_AREA_PX = 200
```

- [ ] **Step 2: Commit**

```bash
git add vision/src/detection/hsv_ranges.py
git commit -m "feat(vision): add HSV ranges for robot markers"
```

---

### Task 3.2: Robot detection — test first

**Files:**
- Create: `vision/tests/test_detection.py`

- [ ] **Step 1: Add a fixture generator to `conftest.py`**

Append to `vision/tests/conftest.py`:

```python
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
```

- [ ] **Step 2: Write `vision/tests/test_detection.py`**

```python
"""Robot detection tests using synthetic rendered scenes."""
import numpy as np
import pytest
from vision.src.detection.robot import detect_robot
from vision.tests.conftest import make_synthetic_robot_image


@pytest.mark.parametrize("x,y,heading", [
    (1.25, 1.25, 0.0),
    (0.5, 0.5, 90.0),
    (2.0, 0.5, 180.0),
    (1.0, 2.0, 270.0),
])
def test_detect_robot_position_and_heading(
    synthetic_intrinsics, synthetic_extrinsics, x, y, heading
):
    img = make_synthetic_robot_image(
        synthetic_intrinsics, synthetic_extrinsics,
        robot_xy_m=(x, y), heading_deg=heading, height_m=0.30,
    )
    pose = detect_robot(img, synthetic_intrinsics, synthetic_extrinsics, travel_height_m=0.30)
    assert pose is not None
    assert abs(pose.x_m - x) < 0.05, f"x error: {pose.x_m - x}"
    assert abs(pose.y_m - y) < 0.05, f"y error: {pose.y_m - y}"
    heading_diff = (pose.heading_deg - heading + 180) % 360 - 180
    assert abs(heading_diff) < 5, f"heading error: {heading_diff}"


def test_detect_robot_missing_markers(synthetic_intrinsics, synthetic_extrinsics):
    """Black image → no markers → robot_pose is None."""
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    pose = detect_robot(img, synthetic_intrinsics, synthetic_extrinsics, travel_height_m=0.30)
    assert pose is None
```

- [ ] **Step 3: Run tests — expect failure**

```bash
pytest vision/tests/test_detection.py -v
```

Expected: ImportError — `detect_robot` doesn't exist.

---

### Task 3.3: Robot detection — implementation

**Files:**
- Create: `vision/src/detection/robot.py`

- [ ] **Step 1: Write `robot.py`**

```python
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
```

- [ ] **Step 2: Run tests**

```bash
pytest vision/tests/test_detection.py -v
```

Expected: all 4 parametrized cases + the missing-markers test pass.

- [ ] **Step 3: Commit**

```bash
git add vision/src/detection/ vision/tests/test_detection.py vision/tests/conftest.py
git commit -m "feat(vision): implement HSV-based robot detection with parallax correction"
```

---

### Phase 4 — Planning: grid and A*

### Task 4.1: Grid construction — tests first

**Files:**
- Create: `vision/src/planning/errors.py`
- Create: `vision/tests/test_grid.py`

- [ ] **Step 1: Write `vision/src/planning/errors.py`**

```python
"""Planning-related errors."""


class NoPathError(Exception):
    pass


class ApproachPointBlockedError(Exception):
    def __init__(self, shelf_id: str):
        super().__init__(f"Approach point blocked by inflated obstacle: shelf_id={shelf_id}")
        self.shelf_id = shelf_id
```

- [ ] **Step 2: Write `vision/tests/test_grid.py`**

```python
"""Occupancy grid construction tests."""
import pytest
from vision.src.planning.grid import build_occupancy_grid, world_to_cell, cell_to_world
from vision.src.planning.errors import ApproachPointBlockedError
from vision.src.models import (
    Settings, WorkspaceConfig, RobotConfig, RobotMarkers, CameraConfig, PlannerConfig,
    Shelf, ApproachPoint,
)


def make_settings(cell_size=0.25, inflation=0.0):
    return Settings(
        workspace=WorkspaceConfig(width_m=2.5, height_m=2.5, cell_size_m=cell_size),
        robot=RobotConfig(
            footprint_m=(0.5, 0.5),
            travel_height_m=0.30,
            markers=RobotMarkers(front_color="red", back_color="green"),
        ),
        camera=CameraConfig(source=0, resolution=(1280, 720)),
        planner=PlannerConfig(obstacle_inflation_m=inflation),
    )


def test_empty_grid_no_shelves():
    settings = make_settings()
    grid = build_occupancy_grid([], settings)
    assert grid.shape == (10, 10)
    assert not grid.any()


def test_grid_marks_shelf_cells():
    settings = make_settings(cell_size=0.25, inflation=0.0)
    shelf = Shelf(
        id="s", x_m=0.5, y_m=0.5, width_m=0.5, length_m=0.5, rotation_deg=0,
        approach_point=ApproachPoint(x_m=1.0, y_m=0.5, heading_deg=180),
    )
    grid = build_occupancy_grid([shelf], settings)
    # Shelf center (0.5, 0.5) with 0.5x0.5 footprint should mark cells around (2,2).
    assert grid[2, 2] == 1
    assert grid[0, 0] == 0  # corner cell should be free


def test_grid_inflation_widens_obstacle():
    inflated = build_occupancy_grid(
        [Shelf(
            id="s", x_m=1.25, y_m=1.25, width_m=0.25, length_m=0.25, rotation_deg=0,
            approach_point=ApproachPoint(x_m=0.5, y_m=1.25, heading_deg=0),
        )],
        make_settings(cell_size=0.25, inflation=0.25),
    )
    # A 0.25x0.25 shelf at (1.25, 1.25) inflated by 0.25 should occupy the center
    # 3x3 block around cell (5, 5).
    assert inflated[5, 5] == 1
    assert inflated[4, 5] == 1
    assert inflated[5, 4] == 1


def test_grid_small_inflation_rounds_up_not_down():
    """0.10 m inflation at 0.25 m cells should ceil to 1 cell, not floor to 0."""
    inflated = build_occupancy_grid(
        [Shelf(
            id="s", x_m=1.25, y_m=1.25, width_m=0.25, length_m=0.25, rotation_deg=0,
            approach_point=ApproachPoint(x_m=0.5, y_m=1.25, heading_deg=0),
        )],
        make_settings(cell_size=0.25, inflation=0.10),
    )
    # The shelf cell is (5, 5) and must have at least one ring of inflation.
    assert inflated[5, 5] == 1
    assert inflated[4, 5] == 1 or inflated[6, 5] == 1


def test_grid_raises_on_blocked_approach_point():
    settings = make_settings(cell_size=0.25, inflation=0.25)
    shelf = Shelf(
        id="blocked", x_m=1.25, y_m=1.25, width_m=1.0, length_m=1.0, rotation_deg=0,
        approach_point=ApproachPoint(x_m=1.25, y_m=1.25, heading_deg=0),
    )
    with pytest.raises(ApproachPointBlockedError):
        build_occupancy_grid([shelf], settings)


def test_world_to_cell_and_back():
    settings = make_settings(cell_size=0.25)
    row, col = world_to_cell((1.125, 1.625), settings)
    assert (row, col) == (6, 4)
    x, y = cell_to_world((6, 4), settings)
    assert abs(x - 1.125) < 1e-9
    assert abs(y - 1.625) < 1e-9
```

- [ ] **Step 3: Run tests — expect import failure**

```bash
pytest vision/tests/test_grid.py -v
```

---

### Task 4.2: Grid — implementation

**Files:**
- Create: `vision/src/planning/grid.py`

- [ ] **Step 1: Write `grid.py`**

```python
"""Occupancy grid construction."""
import math
import numpy as np
from vision.src.models import Settings, Shelf
from vision.src.planning.errors import ApproachPointBlockedError


def world_to_cell(xy_m: tuple[float, float], settings: Settings) -> tuple[int, int]:
    """World (x, y) in meters → (row, col). Raises ValueError if out of bounds.

    Points exactly on the far boundary are clamped to the last cell so that
    detection noise at the workspace edge does not error out.
    """
    x, y = xy_m
    ws = settings.workspace
    if not (0 <= x <= ws.width_m and 0 <= y <= ws.height_m):
        raise ValueError(f"Point ({x}, {y}) outside workspace")
    cols = int(round(ws.width_m / ws.cell_size_m))
    rows = int(round(ws.height_m / ws.cell_size_m))
    col = min(int(x / ws.cell_size_m), cols - 1)
    row = min(int(y / ws.cell_size_m), rows - 1)
    return row, col


def cell_to_world(rc: tuple[int, int], settings: Settings) -> tuple[float, float]:
    """(row, col) → world (x, y) at cell center."""
    row, col = rc
    s = settings.workspace.cell_size_m
    return col * s + s / 2, row * s + s / 2


def _rasterize_shelf(shelf: Shelf, grid: np.ndarray, settings: Settings) -> None:
    """Mark grid cells whose center lies inside the (rotated) shelf rectangle."""
    s = settings.workspace.cell_size_m
    cos = math.cos(math.radians(shelf.rotation_deg))
    sin = math.sin(math.radians(shelf.rotation_deg))
    half_w = shelf.width_m / 2
    half_l = shelf.length_m / 2

    rows, cols = grid.shape
    for row in range(rows):
        for col in range(cols):
            cx = col * s + s / 2
            cy = row * s + s / 2
            dx = cx - shelf.x_m
            dy = cy - shelf.y_m
            # Rotate into shelf local frame.
            local_x = cos * dx + sin * dy
            local_y = -sin * dx + cos * dy
            if -half_w <= local_x <= half_w and -half_l <= local_y <= half_l:
                grid[row, col] = 1


def _inflate(grid: np.ndarray, radius_cells: int) -> np.ndarray:
    """Grow obstacles by `radius_cells` using a square kernel."""
    if radius_cells <= 0:
        return grid
    rows, cols = grid.shape
    out = grid.copy()
    for row in range(rows):
        for col in range(cols):
            if grid[row, col] == 1:
                r0 = max(0, row - radius_cells)
                r1 = min(rows, row + radius_cells + 1)
                c0 = max(0, col - radius_cells)
                c1 = min(cols, col + radius_cells + 1)
                out[r0:r1, c0:c1] = 1
    return out


def build_occupancy_grid(shelves: list[Shelf], settings: Settings) -> np.ndarray:
    """Build an int8 occupancy grid from the shelf list.

    Grid cells are 0 for free, 1 for obstacle. Obstacles are shelves rasterized
    into the grid and then inflated by planner.obstacle_inflation_m, rounded
    up to the nearest whole cell so small safety margins never silently round
    to zero.
    """
    ws = settings.workspace
    rows = int(round(ws.height_m / ws.cell_size_m))
    cols = int(round(ws.width_m / ws.cell_size_m))
    grid = np.zeros((rows, cols), dtype=np.int8)

    for shelf in shelves:
        _rasterize_shelf(shelf, grid, settings)

    radius_cells = math.ceil(settings.planner.obstacle_inflation_m / ws.cell_size_m)
    inflated = _inflate(grid, radius_cells)

    for shelf in shelves:
        try:
            row, col = world_to_cell((shelf.approach_point.x_m, shelf.approach_point.y_m), settings)
        except ValueError:
            raise ApproachPointBlockedError(shelf.id)
        if inflated[row, col] == 1:
            raise ApproachPointBlockedError(shelf.id)

    return inflated
```

- [ ] **Step 2: Run tests**

```bash
pytest vision/tests/test_grid.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 3: Commit**

```bash
git add vision/src/planning/errors.py vision/src/planning/grid.py vision/tests/test_grid.py
git commit -m "feat(vision): add occupancy grid construction with inflation"
```

---

### Task 4.3: A* — tests first

**Files:**
- Create: `vision/tests/test_astar.py`

- [ ] **Step 1: Write `vision/tests/test_astar.py`**

```python
"""A* search tests."""
import numpy as np
import pytest
from vision.src.planning.astar import a_star
from vision.src.planning.errors import NoPathError


def test_astar_direct_line_empty_grid():
    grid = np.zeros((10, 10), dtype=np.int8)
    path = a_star(grid, (0, 0), (0, 9))
    assert path[0] == (0, 0)
    assert path[-1] == (0, 9)
    # Straight line should produce 10 cells.
    assert len(path) == 10


def test_astar_diagonal():
    grid = np.zeros((10, 10), dtype=np.int8)
    path = a_star(grid, (0, 0), (5, 5))
    assert path[0] == (0, 0)
    assert path[-1] == (5, 5)
    assert len(path) == 6


def test_astar_routes_around_obstacle():
    grid = np.zeros((10, 10), dtype=np.int8)
    grid[0:8, 5] = 1  # vertical wall with a gap at rows 8-9
    path = a_star(grid, (0, 0), (0, 9))
    assert path[0] == (0, 0)
    assert path[-1] == (0, 9)
    assert all(grid[r, c] == 0 for r, c in path)


def test_astar_unreachable_raises():
    grid = np.zeros((10, 10), dtype=np.int8)
    grid[:, 5] = 1  # full vertical wall
    with pytest.raises(NoPathError):
        a_star(grid, (0, 0), (0, 9))


def test_astar_start_is_goal():
    grid = np.zeros((10, 10), dtype=np.int8)
    path = a_star(grid, (3, 3), (3, 3))
    assert path == [(3, 3)]
```

- [ ] **Step 2: Run — expect import error**

```bash
pytest vision/tests/test_astar.py -v
```

---

### Task 4.4: A* — implementation

**Files:**
- Create: `vision/src/planning/astar.py`

- [ ] **Step 1: Write `astar.py`**

```python
"""A* pathfinding on a 2D occupancy grid (8-connected)."""
import heapq
import math
import numpy as np
from vision.src.planning.errors import NoPathError


_NEIGHBORS = [
    (-1, -1, math.sqrt(2)),
    (-1, 0, 1.0),
    (-1, 1, math.sqrt(2)),
    (0, -1, 1.0),
    (0, 1, 1.0),
    (1, -1, math.sqrt(2)),
    (1, 0, 1.0),
    (1, 1, math.sqrt(2)),
]


def _heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def a_star(
    grid: np.ndarray,
    start: tuple[int, int],
    goal: tuple[int, int],
) -> list[tuple[int, int]]:
    """Return the shortest 8-connected path from `start` to `goal` as a list
    of (row, col) cells. Raises NoPathError if unreachable.
    """
    rows, cols = grid.shape
    if start == goal:
        return [start]
    if grid[start] == 1:
        raise NoPathError(f"Start cell {start} is blocked")
    if grid[goal] == 1:
        raise NoPathError(f"Goal cell {goal} is blocked")

    open_heap: list[tuple[float, tuple[int, int]]] = [(_heuristic(start, goal), start)]
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {start: 0.0}
    closed: set[tuple[int, int]] = set()

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        if current == goal:
            # Reconstruct.
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path
        closed.add(current)

        for dr, dc, cost in _NEIGHBORS:
            nr, nc = current[0] + dr, current[1] + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            if grid[nr, nc] == 1:
                continue
            neighbor = (nr, nc)
            tentative = g_score[current] + cost
            if tentative < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = tentative
                came_from[neighbor] = current
                f = tentative + _heuristic(neighbor, goal)
                heapq.heappush(open_heap, (f, neighbor))

    raise NoPathError(f"No path from {start} to {goal}")
```

- [ ] **Step 2: Run tests**

```bash
pytest vision/tests/test_astar.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 3: Commit**

```bash
git add vision/src/planning/astar.py vision/tests/test_astar.py
git commit -m "feat(vision): add 8-connected A* grid pathfinding"
```

---

### Phase 5 — Motion decomposition and task layer

### Task 5.1: Motion decomposition — tests first

**Files:**
- Create: `vision/tests/test_motion.py`

- [ ] **Step 1: Write `vision/tests/test_motion.py`**

```python
"""Non-holonomic motion decomposition tests."""
from vision.src.planning.motion import decompose_to_waypoints
from vision.src.models import TurnWaypoint, DriveWaypoint
from vision.tests.test_grid import make_settings


def test_straight_line_single_drive():
    settings = make_settings(cell_size=0.25)
    cell_path = [(0, 0), (0, 1), (0, 2), (0, 3)]
    waypoints = decompose_to_waypoints(
        cell_path, start_heading_deg=0.0, final_heading_deg=0.0, settings=settings,
    )
    # Expect: no initial turn (already facing right), one drive, no final turn.
    drives = [w for w in waypoints if isinstance(w, DriveWaypoint)]
    turns = [w for w in waypoints if isinstance(w, TurnWaypoint)]
    assert len(drives) == 1
    assert abs(drives[0].distance_m - 0.75) < 1e-6  # 3 cells * 0.25 m
    assert len(turns) == 0


def test_right_angle_one_turn_two_drives():
    settings = make_settings(cell_size=0.25)
    cell_path = [(0, 0), (0, 1), (0, 2), (1, 2), (2, 2)]
    waypoints = decompose_to_waypoints(
        cell_path, start_heading_deg=0.0, final_heading_deg=90.0, settings=settings,
    )
    drives = [w for w in waypoints if isinstance(w, DriveWaypoint)]
    turns = [w for w in waypoints if isinstance(w, TurnWaypoint)]
    assert len(drives) == 2
    assert len(turns) == 1
    assert abs(turns[0].target_heading_deg - 90.0) < 1e-6


def test_initial_turn_when_starting_heading_wrong():
    settings = make_settings(cell_size=0.25)
    cell_path = [(0, 0), (0, 1), (0, 2)]
    waypoints = decompose_to_waypoints(
        cell_path, start_heading_deg=180.0, final_heading_deg=0.0, settings=settings,
    )
    turns = [w for w in waypoints if isinstance(w, TurnWaypoint)]
    drives = [w for w in waypoints if isinstance(w, DriveWaypoint)]
    # Expect: initial turn from 180 to 0, one drive, no final turn (already at 0)
    assert len(turns) == 1
    assert len(drives) == 1


def test_final_turn_to_match_approach_heading():
    settings = make_settings(cell_size=0.25)
    cell_path = [(0, 0), (0, 1)]
    waypoints = decompose_to_waypoints(
        cell_path, start_heading_deg=0.0, final_heading_deg=270.0, settings=settings,
    )
    turns = [w for w in waypoints if isinstance(w, TurnWaypoint)]
    drives = [w for w in waypoints if isinstance(w, DriveWaypoint)]
    # Expect: no initial turn, one drive, one final turn to 270.
    assert len(drives) == 1
    assert len(turns) == 1
    assert abs(turns[0].target_heading_deg - 270.0) < 1e-6


def test_single_cell_path_no_drive():
    settings = make_settings(cell_size=0.25)
    waypoints = decompose_to_waypoints(
        [(3, 3)], start_heading_deg=45.0, final_heading_deg=45.0, settings=settings,
    )
    # No movement, no turns.
    assert waypoints == []
```

- [ ] **Step 2: Run — expect import error**

```bash
pytest vision/tests/test_motion.py -v
```

---

### Task 5.2: Motion decomposition — implementation

**Files:**
- Create: `vision/src/planning/motion.py`

- [ ] **Step 1: Write `motion.py`**

```python
"""Non-holonomic motion decomposition.

Converts an A* cell path into a [turn, drive, turn, drive, ..., turn] sequence
suitable for a differential-drive robot that must turn in place before moving.
"""
import math
from vision.src.models import (
    Settings, TurnWaypoint, DriveWaypoint, Pose2D, Waypoint,
)
from vision.src.planning.grid import cell_to_world


DIRECTION_TOLERANCE_DEG = 5.0


def _heading_between(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Heading in degrees from point a to point b (0 = +X, 90 = +Y)."""
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def _normalize_angle(deg: float) -> float:
    return (deg + 180) % 360 - 180


def _heading_diff(a: float, b: float) -> float:
    return abs(_normalize_angle(a - b))


def decompose_to_waypoints(
    cell_path: list[tuple[int, int]],
    start_heading_deg: float,
    final_heading_deg: float,
    settings: Settings,
) -> list[Waypoint]:
    """Decompose a cell-by-cell A* path into turn and drive primitives."""
    if len(cell_path) < 2:
        return []

    # Convert cells to world coordinates.
    world_path = [cell_to_world(c, settings) for c in cell_path]

    # Compute segment headings and collapse same-direction segments.
    segments: list[tuple[tuple[float, float], tuple[float, float], float]] = []
    i = 0
    while i < len(world_path) - 1:
        start_pt = world_path[i]
        heading = _heading_between(start_pt, world_path[i + 1])
        # Extend as long as direction stays within tolerance.
        j = i + 1
        while j < len(world_path) - 1:
            next_heading = _heading_between(world_path[j], world_path[j + 1])
            if _heading_diff(heading, next_heading) > DIRECTION_TOLERANCE_DEG:
                break
            j += 1
        end_pt = world_path[j]
        segments.append((start_pt, end_pt, heading))
        i = j

    # Build waypoint list: initial turn, then turn+drive pairs for each segment,
    # then final turn.
    waypoints: list[Waypoint] = []
    current_heading = start_heading_deg
    current_pose = Pose2D(x_m=world_path[0][0], y_m=world_path[0][1], heading_deg=current_heading)

    for start_pt, end_pt, seg_heading in segments:
        if _heading_diff(current_heading, seg_heading) > DIRECTION_TOLERANCE_DEG:
            waypoints.append(TurnWaypoint(
                target_heading_deg=seg_heading,
                from_pose=current_pose,
            ))
            current_heading = seg_heading
            current_pose = Pose2D(current_pose.x_m, current_pose.y_m, seg_heading)

        distance = math.hypot(end_pt[0] - start_pt[0], end_pt[1] - start_pt[1])
        to_pose = Pose2D(x_m=end_pt[0], y_m=end_pt[1], heading_deg=seg_heading)
        waypoints.append(DriveWaypoint(
            distance_m=distance,
            from_pose=current_pose,
            to_pose=to_pose,
        ))
        current_pose = to_pose
        current_heading = seg_heading

    if _heading_diff(current_heading, final_heading_deg) > DIRECTION_TOLERANCE_DEG:
        waypoints.append(TurnWaypoint(
            target_heading_deg=final_heading_deg,
            from_pose=current_pose,
        ))

    return waypoints
```

- [ ] **Step 2: Run tests**

```bash
pytest vision/tests/test_motion.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 3: Commit**

```bash
git add vision/src/planning/motion.py vision/tests/test_motion.py
git commit -m "feat(vision): add non-holonomic motion decomposition"
```

---

### Task 5.3: Task composition — tests + implementation

**Files:**
- Create: `vision/src/planning/task.py`
- Create: `vision/tests/test_task.py`

- [ ] **Step 1: Write `vision/tests/test_task.py`**

```python
"""Pick-and-place task composition tests."""
from vision.src.planning.task import plan_navigate_to, plan_pick_and_place
from vision.src.models import (
    Shelf, ApproachPoint, Pose2D, GrabWaypoint, PlaceWaypoint, DriveWaypoint,
)
from vision.tests.test_grid import make_settings


def _shelves():
    return [
        Shelf(
            id="shelf_A", x_m=0.5, y_m=1.25, width_m=0.5, length_m=0.5, rotation_deg=0,
            approach_point=ApproachPoint(x_m=1.125, y_m=1.25, heading_deg=180),
        ),
        Shelf(
            id="shelf_B", x_m=2.0, y_m=1.25, width_m=0.5, length_m=0.5, rotation_deg=0,
            approach_point=ApproachPoint(x_m=1.375, y_m=1.25, heading_deg=0),
        ),
    ]


def test_navigate_produces_waypoints():
    settings = make_settings(inflation=0.0)
    current = Pose2D(x_m=0.125, y_m=0.125, heading_deg=0)
    waypoints = plan_navigate_to(_shelves(), "shelf_A", current, settings)
    assert len(waypoints) > 0
    assert any(isinstance(w, DriveWaypoint) for w in waypoints)


def test_pick_and_place_stitches_grab_and_place():
    settings = make_settings(inflation=0.0)
    current = Pose2D(x_m=0.125, y_m=0.125, heading_deg=0)
    waypoints = plan_pick_and_place(_shelves(), "shelf_A", "shelf_B", current, settings)

    grabs = [w for w in waypoints if isinstance(w, GrabWaypoint)]
    places = [w for w in waypoints if isinstance(w, PlaceWaypoint)]
    assert len(grabs) == 1
    assert grabs[0].shelf_id == "shelf_A"
    assert len(places) == 1
    assert places[0].shelf_id == "shelf_B"

    grab_index = waypoints.index(grabs[0])
    place_index = waypoints.index(places[0])
    assert grab_index < place_index
```

- [ ] **Step 2: Write `vision/src/planning/task.py`**

```python
"""Task-level planning: navigate and pick-and-place."""
from vision.src.models import (
    Settings, Shelf, Pose2D, Waypoint, GrabWaypoint, PlaceWaypoint,
)
from vision.src.planning.grid import build_occupancy_grid, world_to_cell
from vision.src.planning.astar import a_star
from vision.src.planning.motion import decompose_to_waypoints


def _find_shelf(shelves: list[Shelf], shelf_id: str) -> Shelf:
    for s in shelves:
        if s.id == shelf_id:
            return s
    raise KeyError(f"Shelf not found: {shelf_id}")


def plan_navigate_to(
    shelves: list[Shelf],
    target_shelf_id: str,
    current_pose: Pose2D,
    settings: Settings,
) -> list[Waypoint]:
    target = _find_shelf(shelves, target_shelf_id)
    grid = build_occupancy_grid(shelves, settings)

    start_cell = world_to_cell((current_pose.x_m, current_pose.y_m), settings)
    goal_cell = world_to_cell(
        (target.approach_point.x_m, target.approach_point.y_m), settings
    )

    cell_path = a_star(grid, start_cell, goal_cell)
    return decompose_to_waypoints(
        cell_path,
        start_heading_deg=current_pose.heading_deg,
        final_heading_deg=target.approach_point.heading_deg,
        settings=settings,
    )


def plan_pick_and_place(
    shelves: list[Shelf],
    source_id: str,
    destination_id: str,
    current_pose: Pose2D,
    settings: Settings,
) -> list[Waypoint]:
    src = _find_shelf(shelves, source_id)

    to_source = plan_navigate_to(shelves, source_id, current_pose, settings)
    pose_at_source = Pose2D(
        x_m=src.approach_point.x_m,
        y_m=src.approach_point.y_m,
        heading_deg=src.approach_point.heading_deg,
    )
    to_dest = plan_navigate_to(shelves, destination_id, pose_at_source, settings)

    return (
        to_source
        + [GrabWaypoint(shelf_id=source_id)]
        + to_dest
        + [PlaceWaypoint(shelf_id=destination_id)]
    )
```

- [ ] **Step 3: Run tests**

```bash
pytest vision/tests/test_task.py -v
```

Expected: both tests pass.

- [ ] **Step 4: Commit**

```bash
git add vision/src/planning/task.py vision/tests/test_task.py
git commit -m "feat(vision): add navigate and pick-and-place task composition"
```

---

### Phase 6 — Rendering overlay

### Task 6.1: Overlay drawing

**Files:**
- Create: `vision/src/rendering/overlay.py`

No TDD test for this — rendering is visual and hard to unit test meaningfully. We rely on manual inspection during the web UI integration test.

- [ ] **Step 1: Write `overlay.py`**

```python
"""Draw shelves, robot pose, and path on an image."""
import math
import numpy as np
import cv2
from vision.src.models import (
    Settings, Shelf, RobotPose, Waypoint, DriveWaypoint, Intrinsics, Extrinsics,
)


def _project_world_to_pixel(
    world_xyz: np.ndarray,
    intrinsics: Intrinsics,
    extrinsics: Extrinsics,
) -> tuple[int, int] | None:
    R, _ = cv2.Rodrigues(extrinsics.rvec)
    cam = R @ world_xyz + extrinsics.tvec
    if cam[2] <= 0:
        return None
    K = intrinsics.camera_matrix
    u = K[0, 0] * (cam[0] / cam[2]) + K[0, 2]
    v = K[1, 1] * (cam[1] / cam[2]) + K[1, 2]
    return int(round(u)), int(round(v))


def draw_overlay(
    frame: np.ndarray,
    shelves: list[Shelf],
    robot_pose: RobotPose | None,
    waypoints: list[Waypoint],
    intrinsics: Intrinsics,
    extrinsics: Extrinsics,
    travel_height_m: float,
) -> np.ndarray:
    """Return a copy of `frame` with shelves, robot, and path drawn on it."""
    out = frame.copy()

    # --- Draw shelves as rectangles projected to pixel space.
    for shelf in shelves:
        corners_local = np.array([
            [-shelf.width_m / 2, -shelf.length_m / 2],
            [shelf.width_m / 2, -shelf.length_m / 2],
            [shelf.width_m / 2, shelf.length_m / 2],
            [-shelf.width_m / 2, shelf.length_m / 2],
        ])
        c = math.cos(math.radians(shelf.rotation_deg))
        s = math.sin(math.radians(shelf.rotation_deg))
        R2 = np.array([[c, -s], [s, c]])
        corners_world = (R2 @ corners_local.T).T + np.array([shelf.x_m, shelf.y_m])

        pixel_corners = []
        for (x, y) in corners_world:
            px = _project_world_to_pixel(np.array([x, y, 0.0]), intrinsics, extrinsics)
            if px is not None:
                pixel_corners.append(px)
        if len(pixel_corners) == 4:
            pts = np.array(pixel_corners, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(out, [pts], True, (255, 200, 0), 2)
            label_px = _project_world_to_pixel(
                np.array([shelf.x_m, shelf.y_m, 0.0]), intrinsics, extrinsics
            )
            if label_px:
                cv2.putText(out, shelf.id, label_px, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)

    # --- Draw robot pose.
    if robot_pose is not None:
        px = _project_world_to_pixel(
            np.array([robot_pose.x_m, robot_pose.y_m, travel_height_m]),
            intrinsics, extrinsics,
        )
        if px is not None:
            cv2.circle(out, px, 8, (0, 255, 255), -1)
            # Heading arrow
            tip_x = robot_pose.x_m + 0.2 * math.cos(math.radians(robot_pose.heading_deg))
            tip_y = robot_pose.y_m + 0.2 * math.sin(math.radians(robot_pose.heading_deg))
            tip_px = _project_world_to_pixel(
                np.array([tip_x, tip_y, travel_height_m]), intrinsics, extrinsics
            )
            if tip_px:
                cv2.arrowedLine(out, px, tip_px, (0, 255, 255), 2, tipLength=0.3)

    # --- Draw drive path segments.
    for wp in waypoints:
        if isinstance(wp, DriveWaypoint):
            from_px = _project_world_to_pixel(
                np.array([wp.from_pose.x_m, wp.from_pose.y_m, travel_height_m]),
                intrinsics, extrinsics,
            )
            to_px = _project_world_to_pixel(
                np.array([wp.to_pose.x_m, wp.to_pose.y_m, travel_height_m]),
                intrinsics, extrinsics,
            )
            if from_px and to_px:
                cv2.line(out, from_px, to_px, (0, 255, 0), 3)

    return out
```

- [ ] **Step 2: Commit**

```bash
git add vision/src/rendering/overlay.py
git commit -m "feat(vision): add rendering overlay for shelves, robot, and path"
```

---

### Phase 7 — FastAPI backend

### Task 7.1: Config loader and camera interface

**Files:**
- Create: `vision/src/api/config_loader.py`
- Create: `vision/src/api/camera.py`

- [ ] **Step 1: Write `vision/src/api/config_loader.py`**

```python
"""Load and validate settings.yaml and shelves.json."""
from pathlib import Path
import json
import yaml
from vision.src.models import (
    Settings, WorkspaceConfig, RobotConfig, RobotMarkers, CameraConfig,
    PlannerConfig, Shelf, ApproachPoint,
)


class ConfigError(Exception):
    pass


def load_settings(path: Path) -> Settings:
    with path.open("r") as f:
        data = yaml.safe_load(f)
    try:
        return Settings(
            workspace=WorkspaceConfig(
                width_m=float(data["workspace"]["width_m"]),
                height_m=float(data["workspace"]["height_m"]),
                cell_size_m=float(data["workspace"]["cell_size_m"]),
            ),
            robot=RobotConfig(
                footprint_m=tuple(data["robot"]["footprint_m"]),
                travel_height_m=float(data["robot"]["travel_height_m"]),
                markers=RobotMarkers(
                    front_color=str(data["robot"]["markers"]["front_color"]),
                    back_color=str(data["robot"]["markers"]["back_color"]),
                ),
            ),
            camera=CameraConfig(
                source=data["camera"]["source"],
                resolution=tuple(data["camera"]["resolution"]),
            ),
            planner=PlannerConfig(
                obstacle_inflation_m=float(data["planner"]["obstacle_inflation_m"]),
            ),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise ConfigError(f"Malformed settings.yaml: {e}") from e


def load_shelves(path: Path) -> list[Shelf]:
    with path.open("r") as f:
        data = json.load(f)
    shelves = []
    for raw in data["shelves"]:
        try:
            shelves.append(Shelf(
                id=str(raw["id"]),
                x_m=float(raw["x_m"]),
                y_m=float(raw["y_m"]),
                width_m=float(raw["width_m"]),
                length_m=float(raw["length_m"]),
                rotation_deg=float(raw["rotation_deg"]),
                approach_point=ApproachPoint(
                    x_m=float(raw["approach_point"]["x_m"]),
                    y_m=float(raw["approach_point"]["y_m"]),
                    heading_deg=float(raw["approach_point"]["heading_deg"]),
                ),
            ))
        except (KeyError, TypeError, ValueError) as e:
            raise ConfigError(f"Malformed shelf entry: {e}") from e
    return shelves


def save_shelves(shelves: list[Shelf], path: Path) -> None:
    data = {
        "shelves": [
            {
                "id": s.id,
                "x_m": s.x_m,
                "y_m": s.y_m,
                "width_m": s.width_m,
                "length_m": s.length_m,
                "rotation_deg": s.rotation_deg,
                "approach_point": {
                    "x_m": s.approach_point.x_m,
                    "y_m": s.approach_point.y_m,
                    "heading_deg": s.approach_point.heading_deg,
                },
            }
            for s in shelves
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(data, f, indent=2)
```

- [ ] **Step 2: Write `vision/src/api/camera.py`**

```python
"""Camera abstraction: real (OpenCV) and fake (fixture image) implementations."""
from abc import ABC, abstractmethod
from pathlib import Path
import numpy as np
import cv2


class CameraError(Exception):
    pass


class Camera(ABC):
    @abstractmethod
    def capture(self) -> np.ndarray:
        """Return a single BGR frame."""


class OpenCVCamera(Camera):
    def __init__(self, source: int | str, resolution: tuple[int, int]):
        self._source = source
        self._resolution = resolution

    def capture(self) -> np.ndarray:
        cap = cv2.VideoCapture(self._source)
        if not cap.isOpened():
            raise CameraError(f"Failed to open camera source: {self._source}")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolution[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolution[1])
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise CameraError("Camera opened but failed to read frame")
        return frame


class FakeCamera(Camera):
    """Camera that always returns a fixed image. For tests."""

    def __init__(self, image: np.ndarray):
        self._image = image

    def capture(self) -> np.ndarray:
        return self._image.copy()

    @classmethod
    def from_file(cls, path: Path) -> "FakeCamera":
        img = cv2.imread(str(path))
        if img is None:
            raise CameraError(f"Failed to load fake camera image: {path}")
        return cls(img)
```

- [ ] **Step 3: Commit**

```bash
git add vision/src/api/config_loader.py vision/src/api/camera.py
git commit -m "feat(vision): add config loader and camera interface"
```

---

### Task 7.2: Pydantic schemas

**Files:**
- Create: `vision/src/api/schemas.py`

- [ ] **Step 1: Write `schemas.py`**

```python
"""Pydantic request/response models for the FastAPI layer."""
from typing import Literal
from pydantic import BaseModel


# --- Settings / shelves -----------------------------------------------------

class ApproachPointSchema(BaseModel):
    x_m: float
    y_m: float
    heading_deg: float


class ShelfSchema(BaseModel):
    id: str
    x_m: float
    y_m: float
    width_m: float
    length_m: float
    rotation_deg: float
    approach_point: ApproachPointSchema


class ShelvesPayload(BaseModel):
    shelves: list[ShelfSchema]


# --- Calibration status -----------------------------------------------------

class CalibrationStatus(BaseModel):
    intrinsic: bool
    extrinsic: bool


class IntrinsicResult(BaseModel):
    calibration_error_px: float
    captured_images: int


class ExtrinsicResult(BaseModel):
    calibration_error_px: float


# --- Capture / detect -------------------------------------------------------

class CaptureResponse(BaseModel):
    image_base64: str
    timestamp: float


class RobotPoseSchema(BaseModel):
    x_m: float
    y_m: float
    heading_deg: float
    confidence: float


class DetectResponse(BaseModel):
    robot_pose: RobotPoseSchema | None
    reason: str | None = None
    annotated_image_base64: str


# --- Planning ---------------------------------------------------------------

class PlanRequest(BaseModel):
    task: Literal["navigate", "pick_place"]
    source_shelf_id: str | None = None
    destination_shelf_id: str


class Pose2DSchema(BaseModel):
    x_m: float
    y_m: float
    heading_deg: float


class WaypointSchema(BaseModel):
    type: Literal["turn", "drive", "grab", "place", "arrive"]
    # Optional fields depending on type:
    target_heading_deg: float | None = None
    distance_m: float | None = None
    from_pose: Pose2DSchema | None = None
    to_pose: Pose2DSchema | None = None
    shelf_id: str | None = None


class PlanMetrics(BaseModel):
    total_distance_m: float
    estimated_time_s: float


class PlanResponse(BaseModel):
    waypoints: list[WaypointSchema]
    annotated_image_base64: str
    metrics: PlanMetrics


# --- Errors -----------------------------------------------------------------

class ErrorResponse(BaseModel):
    error: str
    details: dict | None = None
```

- [ ] **Step 2: Commit**

```bash
git add vision/src/api/schemas.py
git commit -m "feat(vision): add FastAPI pydantic schemas"
```

---

### Task 7.3: Routes

**Files:**
- Create: `vision/src/api/routes.py`

This is a big file. We keep each endpoint focused and delegate to the domain modules.

- [ ] **Step 1: Write `routes.py`**

```python
"""FastAPI route handlers for the vision module."""
import base64
import time
import math
from pathlib import Path
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, UploadFile, File
from vision.src.api.schemas import (
    ShelvesPayload, ShelfSchema, ApproachPointSchema,
    CalibrationStatus, IntrinsicResult, ExtrinsicResult,
    CaptureResponse, DetectResponse, RobotPoseSchema,
    PlanRequest, PlanResponse, WaypointSchema, Pose2DSchema, PlanMetrics,
)
from vision.src.api.config_loader import (
    load_settings, load_shelves, save_shelves, ConfigError,
)
from vision.src.api.camera import Camera, CameraError
from vision.src.calibration.intrinsic import (
    calibrate_from_images, save_intrinsics, load_intrinsics, IntrinsicCalibrationError,
)
from vision.src.calibration.extrinsic import (
    calibrate_from_frame, save_extrinsics, load_extrinsics, ExtrinsicCalibrationError,
)
from vision.src.detection.robot import detect_robot
from vision.src.planning.task import plan_navigate_to, plan_pick_and_place
from vision.src.planning.errors import NoPathError, ApproachPointBlockedError
from vision.src.rendering.overlay import draw_overlay
from vision.src.models import (
    Shelf, ApproachPoint, ExtrinsicMarker, Pose2D,
    TurnWaypoint, DriveWaypoint, GrabWaypoint, PlaceWaypoint, ArriveWaypoint,
)


# Paths are injected from server.py
class Paths:
    settings: Path
    shelves: Path
    intrinsics: Path
    extrinsics: Path


# Camera singleton is injected from server.py
_camera: Camera | None = None


def set_state(paths: Paths, camera: Camera) -> None:
    global _camera
    Paths.settings = paths.settings
    Paths.shelves = paths.shelves
    Paths.intrinsics = paths.intrinsics
    Paths.extrinsics = paths.extrinsics
    _camera = camera


router = APIRouter(prefix="/api")


# --- Helpers ----------------------------------------------------------------

def _encode_image(frame: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", frame)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode image")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _require_intrinsics():
    if not Paths.intrinsics.exists():
        raise HTTPException(
            status_code=412,
            detail={"error": "intrinsic_calibration_missing"},
        )
    return load_intrinsics(Paths.intrinsics)


def _require_extrinsics():
    if not Paths.extrinsics.exists():
        raise HTTPException(
            status_code=412,
            detail={"error": "extrinsic_calibration_missing"},
        )
    return load_extrinsics(Paths.extrinsics)


def _capture_frame() -> np.ndarray:
    try:
        return _camera.capture()
    except CameraError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": "camera_unavailable", "message": str(e)},
        )


def _shelf_to_schema(s: Shelf) -> ShelfSchema:
    return ShelfSchema(
        id=s.id,
        x_m=s.x_m,
        y_m=s.y_m,
        width_m=s.width_m,
        length_m=s.length_m,
        rotation_deg=s.rotation_deg,
        approach_point=ApproachPointSchema(
            x_m=s.approach_point.x_m,
            y_m=s.approach_point.y_m,
            heading_deg=s.approach_point.heading_deg,
        ),
    )


def _schema_to_shelf(s: ShelfSchema) -> Shelf:
    return Shelf(
        id=s.id,
        x_m=s.x_m,
        y_m=s.y_m,
        width_m=s.width_m,
        length_m=s.length_m,
        rotation_deg=s.rotation_deg,
        approach_point=ApproachPoint(
            x_m=s.approach_point.x_m,
            y_m=s.approach_point.y_m,
            heading_deg=s.approach_point.heading_deg,
        ),
    )


def _waypoint_to_schema(w) -> WaypointSchema:
    if isinstance(w, TurnWaypoint):
        return WaypointSchema(
            type="turn",
            target_heading_deg=w.target_heading_deg,
            from_pose=Pose2DSchema(**w.from_pose.__dict__),
        )
    if isinstance(w, DriveWaypoint):
        return WaypointSchema(
            type="drive",
            distance_m=w.distance_m,
            from_pose=Pose2DSchema(**w.from_pose.__dict__),
            to_pose=Pose2DSchema(**w.to_pose.__dict__),
        )
    if isinstance(w, GrabWaypoint):
        return WaypointSchema(type="grab", shelf_id=w.shelf_id)
    if isinstance(w, PlaceWaypoint):
        return WaypointSchema(type="place", shelf_id=w.shelf_id)
    if isinstance(w, ArriveWaypoint):
        return WaypointSchema(type="arrive", shelf_id=w.shelf_id)
    raise ValueError(f"Unknown waypoint type: {type(w)}")


# --- Health and settings ----------------------------------------------------

@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/settings")
def get_settings():
    try:
        settings = load_settings(Paths.settings)
    except ConfigError as e:
        raise HTTPException(status_code=500, detail={"error": "config_error", "message": str(e)})
    return {
        "workspace": settings.workspace.__dict__,
        "robot": {
            "footprint_m": list(settings.robot.footprint_m),
            "travel_height_m": settings.robot.travel_height_m,
            "markers": settings.robot.markers.__dict__,
        },
        "camera": {
            "source": settings.camera.source,
            "resolution": list(settings.camera.resolution),
        },
        "planner": settings.planner.__dict__,
    }


# --- Shelves ----------------------------------------------------------------

@router.get("/shelves", response_model=ShelvesPayload)
def get_shelves():
    try:
        shelves = load_shelves(Paths.shelves)
    except ConfigError as e:
        raise HTTPException(status_code=500, detail={"error": "config_error", "message": str(e)})
    return ShelvesPayload(shelves=[_shelf_to_schema(s) for s in shelves])


@router.put("/shelves")
def put_shelves(payload: ShelvesPayload):
    shelves = [_schema_to_shelf(s) for s in payload.shelves]
    save_shelves(shelves, Paths.shelves)
    return {"ok": True}


# --- Calibration ------------------------------------------------------------

@router.get("/calibration/status", response_model=CalibrationStatus)
def calibration_status():
    return CalibrationStatus(
        intrinsic=Paths.intrinsics.exists(),
        extrinsic=Paths.extrinsics.exists(),
    )


@router.post("/calibration/intrinsic", response_model=IntrinsicResult)
async def calibration_intrinsic(files: list[UploadFile] = File(...)):
    images: list[np.ndarray] = []
    for f in files:
        data = await f.read()
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is not None:
            images.append(img)
    try:
        intrinsics = calibrate_from_images(images)
    except IntrinsicCalibrationError as e:
        raise HTTPException(status_code=422, detail={"error": "intrinsic_calibration_failed", "message": str(e)})
    save_intrinsics(intrinsics, Paths.intrinsics)
    return IntrinsicResult(
        calibration_error_px=intrinsics.calibration_error_px,
        captured_images=intrinsics.captured_images,
    )


@router.post("/calibration/extrinsic", response_model=ExtrinsicResult)
def calibration_extrinsic():
    intrinsics = _require_intrinsics()
    frame = _capture_frame()

    # Use the 4 corners of the workspace from settings.
    settings = load_settings(Paths.settings)
    expected = [
        ExtrinsicMarker(id=0, workspace_xy_m=(0.0, 0.0)),
        ExtrinsicMarker(id=1, workspace_xy_m=(settings.workspace.width_m, 0.0)),
        ExtrinsicMarker(id=2, workspace_xy_m=(settings.workspace.width_m, settings.workspace.height_m)),
        ExtrinsicMarker(id=3, workspace_xy_m=(0.0, settings.workspace.height_m)),
    ]
    try:
        extrinsics = calibrate_from_frame(frame, expected, intrinsics)
    except ExtrinsicCalibrationError as e:
        raise HTTPException(status_code=422, detail={"error": "aruco_not_found", "message": str(e)})
    save_extrinsics(extrinsics, Paths.extrinsics)
    return ExtrinsicResult(calibration_error_px=extrinsics.calibration_error_px)


# --- Capture / detect -------------------------------------------------------

@router.get("/capture", response_model=CaptureResponse)
def capture():
    frame = _capture_frame()
    return CaptureResponse(image_base64=_encode_image(frame), timestamp=time.time())


@router.post("/detect", response_model=DetectResponse)
def detect():
    intrinsics = _require_intrinsics()
    extrinsics = _require_extrinsics()
    settings = load_settings(Paths.settings)
    shelves = load_shelves(Paths.shelves)
    frame = _capture_frame()

    pose = detect_robot(frame, intrinsics, extrinsics, settings.robot.travel_height_m)
    annotated = draw_overlay(
        frame, shelves, pose, waypoints=[], intrinsics=intrinsics,
        extrinsics=extrinsics, travel_height_m=settings.robot.travel_height_m,
    )
    return DetectResponse(
        robot_pose=(
            RobotPoseSchema(
                x_m=pose.x_m, y_m=pose.y_m,
                heading_deg=pose.heading_deg, confidence=pose.confidence,
            ) if pose is not None else None
        ),
        reason=None if pose is not None else "markers_not_found",
        annotated_image_base64=_encode_image(annotated),
    )


# --- Plan -------------------------------------------------------------------

def _compute_metrics(waypoints: list) -> PlanMetrics:
    distance = sum(w.distance_m for w in waypoints if isinstance(w, DriveWaypoint))
    # Assume 0.25 m/s average speed for estimation.
    time_s = distance / 0.25 + 3.0 * sum(1 for w in waypoints if isinstance(w, TurnWaypoint))
    return PlanMetrics(total_distance_m=distance, estimated_time_s=time_s)


@router.post("/plan", response_model=PlanResponse)
def plan(request: PlanRequest):
    intrinsics = _require_intrinsics()
    extrinsics = _require_extrinsics()
    settings = load_settings(Paths.settings)
    shelves = load_shelves(Paths.shelves)
    frame = _capture_frame()

    pose = detect_robot(frame, intrinsics, extrinsics, settings.robot.travel_height_m)
    if pose is None:
        raise HTTPException(
            status_code=422,
            detail={"error": "robot_not_detected"},
        )
    current = Pose2D(x_m=pose.x_m, y_m=pose.y_m, heading_deg=pose.heading_deg)

    try:
        if request.task == "navigate":
            waypoints = plan_navigate_to(
                shelves, request.destination_shelf_id, current, settings,
            )
        else:
            if request.source_shelf_id is None:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "source_shelf_id_required"},
                )
            waypoints = plan_pick_and_place(
                shelves, request.source_shelf_id, request.destination_shelf_id,
                current, settings,
            )
    except (NoPathError, ApproachPointBlockedError) as e:
        raise HTTPException(
            status_code=422,
            detail={"error": "no_path", "message": str(e)},
        )

    annotated = draw_overlay(
        frame, shelves, pose, waypoints, intrinsics, extrinsics,
        settings.robot.travel_height_m,
    )
    return PlanResponse(
        waypoints=[_waypoint_to_schema(w) for w in waypoints],
        annotated_image_base64=_encode_image(annotated),
        metrics=_compute_metrics(waypoints),
    )
```

- [ ] **Step 2: Commit**

```bash
git add vision/src/api/routes.py
git commit -m "feat(vision): add FastAPI routes for calibration, capture, detect, plan"
```

---

### Task 7.4: Server wiring

**Files:**
- Create: `vision/src/api/server.py`

- [ ] **Step 1: Write `server.py`**

```python
"""FastAPI app entry point. Wires routes, paths, and camera."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from vision.src.api.routes import router, set_state, Paths
from vision.src.api.camera import OpenCVCamera
from vision.src.api.config_loader import load_settings


VISION_ROOT = Path(__file__).resolve().parents[2]  # vision/
CONFIG_DIR = VISION_ROOT / "config"


def build_paths() -> Paths:
    p = Paths()
    p.settings = CONFIG_DIR / "settings.yaml"
    p.shelves = CONFIG_DIR / "shelves.json"
    p.intrinsics = CONFIG_DIR / "camera_intrinsics.yaml"
    p.extrinsics = CONFIG_DIR / "camera_extrinsics.yaml"
    return p


def create_app(camera=None) -> FastAPI:
    app = FastAPI(title="DFP Vision API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    paths = build_paths()

    if camera is None:
        settings = load_settings(paths.settings)
        camera = OpenCVCamera(
            source=settings.camera.source,
            resolution=tuple(settings.camera.resolution),
        )

    set_state(paths, camera)
    app.include_router(router)
    return app


app = None  # Created by run_server.py


def get_app():
    global app
    if app is None:
        app = create_app()
    return app
```

- [ ] **Step 2: Commit**

```bash
git add vision/src/api/server.py
git commit -m "feat(vision): wire FastAPI server with CORS and paths"
```

---

### Task 7.5: API integration tests

**Files:**
- Create: `vision/tests/test_api.py`

- [ ] **Step 1: Write `test_api.py`**

```python
"""FastAPI integration tests with a FakeCamera."""
from pathlib import Path
import shutil
import pytest
import numpy as np
from fastapi.testclient import TestClient
from vision.src.api.server import create_app
from vision.src.api.camera import FakeCamera
from vision.src.api.routes import Paths, set_state
from vision.src.calibration.intrinsic import save_intrinsics
from vision.src.calibration.extrinsic import save_extrinsics
from vision.src.models import Intrinsics, Extrinsics, ExtrinsicMarker
from vision.tests.conftest import make_synthetic_robot_image


@pytest.fixture
def tmp_config(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    source_config = Path(__file__).resolve().parents[1] / "config"
    shutil.copy(source_config / "settings.yaml", config_dir / "settings.yaml")
    shutil.copy(source_config / "shelves.json", config_dir / "shelves.json")
    return config_dir


@pytest.fixture
def client(tmp_config, synthetic_intrinsics, synthetic_extrinsics):
    # Render a scene with the robot at (1.25, 1.25) facing 0° for the fake camera.
    frame = make_synthetic_robot_image(
        synthetic_intrinsics, synthetic_extrinsics,
        robot_xy_m=(1.25, 1.25), heading_deg=0.0, height_m=0.30,
    )
    camera = FakeCamera(frame)
    app = create_app(camera=camera)

    # Override Paths to use the tmp config dir.
    paths = Paths()
    paths.settings = tmp_config / "settings.yaml"
    paths.shelves = tmp_config / "shelves.json"
    paths.intrinsics = tmp_config / "camera_intrinsics.yaml"
    paths.extrinsics = tmp_config / "camera_extrinsics.yaml"
    save_intrinsics(synthetic_intrinsics, paths.intrinsics)
    save_extrinsics(synthetic_extrinsics, paths.extrinsics)
    set_state(paths, camera)

    return TestClient(app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_settings(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    data = r.json()
    assert data["workspace"]["width_m"] == 2.5


def test_shelves_get(client):
    r = client.get("/api/shelves")
    assert r.status_code == 200
    assert len(r.json()["shelves"]) == 2


def test_shelves_put_round_trip(client):
    payload = {
        "shelves": [
            {
                "id": "shelf_X",
                "x_m": 1.0, "y_m": 1.0, "width_m": 0.5, "length_m": 0.5,
                "rotation_deg": 0.0,
                "approach_point": {"x_m": 0.5, "y_m": 1.0, "heading_deg": 0.0},
            }
        ]
    }
    r = client.put("/api/shelves", json=payload)
    assert r.status_code == 200
    r2 = client.get("/api/shelves")
    assert len(r2.json()["shelves"]) == 1
    assert r2.json()["shelves"][0]["id"] == "shelf_X"


def test_calibration_status(client):
    r = client.get("/api/calibration/status")
    assert r.status_code == 200
    assert r.json() == {"intrinsic": True, "extrinsic": True}


def test_capture(client):
    r = client.get("/api/capture")
    assert r.status_code == 200
    assert "image_base64" in r.json()


def test_detect(client):
    r = client.post("/api/detect")
    assert r.status_code == 200
    data = r.json()
    assert data["robot_pose"] is not None
    assert abs(data["robot_pose"]["x_m"] - 1.25) < 0.05


def test_plan_pick_place(client):
    r = client.post("/api/plan", json={
        "task": "pick_place",
        "source_shelf_id": "shelf_A",
        "destination_shelf_id": "shelf_B",
    })
    assert r.status_code == 200
    data = r.json()
    waypoint_types = [w["type"] for w in data["waypoints"]]
    assert "grab" in waypoint_types
    assert "place" in waypoint_types
```

- [ ] **Step 2: Run tests**

```bash
pytest vision/tests/test_api.py -v
```

Expected: all 8 API tests pass.

- [ ] **Step 3: Commit**

```bash
git add vision/tests/test_api.py
git commit -m "test(vision): add FastAPI integration tests with fake camera"
```

---

### Task 7.6: Run-server script

**Files:**
- Create: `vision/scripts/run_server.py`
- Create: `vision/scripts/__init__.py`

- [ ] **Step 1: Write `vision/scripts/run_server.py`**

```python
"""Start the FastAPI server."""
import uvicorn
from vision.src.api.server import create_app


def main():
    app = create_app()
    uvicorn.run(app, host="127.0.0.1", port=8100)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify manually**

```bash
python -m vision.scripts.run_server
```

Expected: server starts on `http://localhost:8100`. Hit `http://localhost:8100/api/health` in browser → `{"status":"ok"}`. Kill with Ctrl+C.

- [ ] **Step 3: Commit**

```bash
git add vision/scripts/
git commit -m "feat(vision): add run-server entry point"
```

---

### Phase 8 — Next.js `/vision` route

### Task 8.1: Route scaffold and API client

**Files:**
- Create: `web-app/app/vision/page.tsx`
- Create: `web-app/app/vision/lib/api.ts`
- Create: `web-app/app/vision/lib/types.ts`

- [ ] **Step 1: Write `web-app/app/vision/lib/types.ts`**

```typescript
export type ApproachPoint = {
  x_m: number;
  y_m: number;
  heading_deg: number;
};

export type Shelf = {
  id: string;
  x_m: number;
  y_m: number;
  width_m: number;
  length_m: number;
  rotation_deg: number;
  approach_point: ApproachPoint;
};

export type CalibrationStatus = {
  intrinsic: boolean;
  extrinsic: boolean;
};

export type RobotPose = {
  x_m: number;
  y_m: number;
  heading_deg: number;
  confidence: number;
};

export type Pose2D = {
  x_m: number;
  y_m: number;
  heading_deg: number;
};

export type Waypoint = {
  type: "turn" | "drive" | "grab" | "place" | "arrive";
  target_heading_deg?: number;
  distance_m?: number;
  from_pose?: Pose2D;
  to_pose?: Pose2D;
  shelf_id?: string;
};

export type PlanMetrics = {
  total_distance_m: number;
  estimated_time_s: number;
};

export type Settings = {
  workspace: { width_m: number; height_m: number; cell_size_m: number };
  robot: {
    footprint_m: [number, number];
    travel_height_m: number;
    markers: { front_color: string; back_color: string };
  };
  camera: { source: number | string; resolution: [number, number] };
  planner: { obstacle_inflation_m: number };
};

export type ApiError = { error: string; message?: string; details?: unknown };
```

- [ ] **Step 2: Write `web-app/app/vision/lib/api.ts`**

```typescript
import type {
  Shelf, CalibrationStatus, RobotPose, Waypoint, PlanMetrics, Settings,
} from "./types";

const API_BASE = "http://localhost:8100/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let detail: unknown;
    try { detail = await res.json(); } catch { detail = await res.text(); }
    throw new Error(JSON.stringify(detail));
  }
  return res.json();
}

export async function getSettings(): Promise<Settings> {
  return request<Settings>("/settings");
}

export async function getShelves(): Promise<{ shelves: Shelf[] }> {
  return request<{ shelves: Shelf[] }>("/shelves");
}

export async function saveShelves(shelves: Shelf[]): Promise<void> {
  await request("/shelves", {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ shelves }),
  });
}

export async function getCalibrationStatus(): Promise<CalibrationStatus> {
  return request<CalibrationStatus>("/calibration/status");
}

export async function calibrateIntrinsic(files: File[]): Promise<{ calibration_error_px: number; captured_images: number }> {
  const form = new FormData();
  files.forEach(f => form.append("files", f));
  return request("/calibration/intrinsic", { method: "POST", body: form });
}

export async function calibrateExtrinsic(): Promise<{ calibration_error_px: number }> {
  return request("/calibration/extrinsic", { method: "POST" });
}

export async function capture(): Promise<{ image_base64: string }> {
  return request("/capture");
}

export async function detect(): Promise<{ robot_pose: RobotPose | null; reason: string | null; annotated_image_base64: string }> {
  return request("/detect", { method: "POST" });
}

export async function plan(body: { task: "navigate" | "pick_place"; source_shelf_id?: string; destination_shelf_id: string }): Promise<{
  waypoints: Waypoint[];
  annotated_image_base64: string;
  metrics: PlanMetrics;
}> {
  return request("/plan", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}
```

- [ ] **Step 3: Write `web-app/app/vision/page.tsx`**

```tsx
"use client";
import { useState } from "react";
import CalibrationTab from "./components/CalibrationTab";
import LayoutEditorTab from "./components/LayoutEditorTab";
import PlanRunTab from "./components/PlanRunTab";

type Tab = "calibration" | "layout" | "plan";

export default function VisionPage() {
  const [tab, setTab] = useState<Tab>("calibration");
  return (
    <div className="min-h-screen bg-black text-white p-6">
      <h1 className="text-2xl font-bold mb-4">Vision Control</h1>
      <nav className="flex gap-2 mb-6 border-b border-white/10">
        {(["calibration", "layout", "plan"] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 ${tab === t ? "border-b-2 border-blue-400 text-blue-400" : "text-white/60"}`}
          >
            {t === "calibration" ? "Calibration" : t === "layout" ? "Layout Editor" : "Plan & Run"}
          </button>
        ))}
      </nav>
      {tab === "calibration" && <CalibrationTab />}
      {tab === "layout" && <LayoutEditorTab />}
      {tab === "plan" && <PlanRunTab />}
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add web-app/app/vision/page.tsx web-app/app/vision/lib/
git commit -m "feat(web-app): add /vision route scaffold and API client"
```

---

### Task 8.2: Calibration tab

**Files:**
- Create: `web-app/app/vision/components/CalibrationTab.tsx`

- [ ] **Step 1: Write `CalibrationTab.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import {
  getCalibrationStatus, calibrateIntrinsic, calibrateExtrinsic,
} from "../lib/api";
import type { CalibrationStatus } from "../lib/types";

export default function CalibrationTab() {
  const [status, setStatus] = useState<CalibrationStatus | null>(null);
  const [message, setMessage] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    try { setStatus(await getCalibrationStatus()); }
    catch (e) { setMessage(String(e)); }
  };
  useEffect(() => { refresh(); }, []);

  const handleIntrinsic = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await calibrateIntrinsic(Array.from(files));
      setMessage(`Intrinsic OK — error ${result.calibration_error_px.toFixed(2)} px, ${result.captured_images} images`);
      await refresh();
    } catch (e) {
      setMessage(`Intrinsic failed: ${e}`);
    } finally {
      setBusy(false);
    }
  };

  const handleExtrinsic = async () => {
    setBusy(true);
    setMessage("");
    try {
      const result = await calibrateExtrinsic();
      setMessage(`Extrinsic OK — error ${result.calibration_error_px.toFixed(2)} px`);
      await refresh();
    } catch (e) {
      setMessage(`Extrinsic failed: ${e}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex gap-4">
        <div className="p-4 border border-white/10 rounded">
          <div className="text-sm text-white/60">Intrinsic</div>
          <div className={status?.intrinsic ? "text-green-400" : "text-red-400"}>
            {status?.intrinsic ? "✓ Calibrated" : "✗ Missing"}
          </div>
        </div>
        <div className="p-4 border border-white/10 rounded">
          <div className="text-sm text-white/60">Extrinsic</div>
          <div className={status?.extrinsic ? "text-green-400" : "text-red-400"}>
            {status?.extrinsic ? "✓ Calibrated" : "✗ Missing"}
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <label className="block font-semibold">Intrinsic calibration</label>
        <p className="text-sm text-white/60">Upload ≥8 photos of a printed 9×6 chessboard.</p>
        <input
          type="file"
          multiple
          accept="image/*"
          disabled={busy}
          onChange={(e) => handleIntrinsic(e.target.files)}
          className="block"
        />
      </div>

      <div className="space-y-2">
        <label className="block font-semibold">Extrinsic calibration</label>
        <p className="text-sm text-white/60">
          Place 4 ArUco markers (DICT_4X4_50, IDs 0-3) at workspace corners, then click:
        </p>
        <button
          disabled={busy || !status?.intrinsic}
          onClick={handleExtrinsic}
          className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
        >
          Run extrinsic calibration
        </button>
      </div>

      {message && (
        <div className="p-3 bg-white/5 border border-white/10 rounded text-sm">{message}</div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add web-app/app/vision/components/CalibrationTab.tsx
git commit -m "feat(web-app): add Calibration tab to /vision route"
```

---

### Task 8.3: Layout editor tab

**Files:**
- Create: `web-app/app/vision/components/LayoutEditorTab.tsx`

This is the most complex frontend task. It is intentionally scoped to the minimum viable editor: list shelves, click to select, edit in a side panel, save.

- [ ] **Step 1: Write `LayoutEditorTab.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { getShelves, saveShelves, getSettings } from "../lib/api";
import type { Shelf, Settings } from "../lib/types";

const PX_PER_M = 200;

function emptyShelf(id: string): Shelf {
  return {
    id,
    x_m: 1.25, y_m: 1.25, width_m: 0.5, length_m: 0.5, rotation_deg: 0,
    approach_point: { x_m: 0.75, y_m: 1.25, heading_deg: 0 },
  };
}

export default function LayoutEditorTab() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [shelves, setShelves] = useState<Shelf[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    (async () => {
      try {
        setSettings(await getSettings());
        const data = await getShelves();
        setShelves(data.shelves);
      } catch (e) { setMessage(String(e)); }
    })();
  }, []);

  const selected = shelves.find(s => s.id === selectedId) ?? null;

  const updateSelected = (patch: Partial<Shelf>) => {
    if (!selected) return;
    setShelves(shelves.map(s => s.id === selected.id ? { ...s, ...patch } : s));
    setDirty(true);
  };

  const updateApproach = (patch: Partial<Shelf["approach_point"]>) => {
    if (!selected) return;
    setShelves(shelves.map(s =>
      s.id === selected.id
        ? { ...s, approach_point: { ...s.approach_point, ...patch } }
        : s
    ));
    setDirty(true);
  };

  const addShelf = () => {
    const id = `shelf_${String.fromCharCode(65 + shelves.length)}`;
    setShelves([...shelves, emptyShelf(id)]);
    setSelectedId(id);
    setDirty(true);
  };

  const deleteSelected = () => {
    if (!selected) return;
    setShelves(shelves.filter(s => s.id !== selected.id));
    setSelectedId(null);
    setDirty(true);
  };

  const save = async () => {
    try {
      await saveShelves(shelves);
      setDirty(false);
      setMessage("Saved.");
    } catch (e) { setMessage(`Save failed: ${e}`); }
  };

  if (!settings) return <div>Loading…</div>;

  const W = settings.workspace.width_m * PX_PER_M;
  const H = settings.workspace.height_m * PX_PER_M;

  return (
    <div className="flex gap-6">
      <div>
        <div className="flex gap-2 mb-2">
          <button onClick={addShelf} className="px-3 py-1 bg-blue-600 rounded">Add Shelf</button>
          <button onClick={deleteSelected} disabled={!selected} className="px-3 py-1 bg-red-600 rounded disabled:opacity-50">Delete</button>
          <button onClick={save} disabled={!dirty} className="px-3 py-1 bg-green-600 rounded disabled:opacity-50">
            Save {dirty && "●"}
          </button>
        </div>
        <svg
          width={W}
          height={H}
          viewBox={`0 ${-H} ${W} ${H}`}
          className="border border-white/20 bg-black"
        >
          {/* Grid */}
          {Array.from({ length: Math.ceil(settings.workspace.width_m / 0.5) + 1 }).map((_, i) => (
            <line key={`v${i}`} x1={i * 0.5 * PX_PER_M} y1={-H} x2={i * 0.5 * PX_PER_M} y2={0} stroke="#222" />
          ))}
          {Array.from({ length: Math.ceil(settings.workspace.height_m / 0.5) + 1 }).map((_, i) => (
            <line key={`h${i}`} x1={0} y1={-i * 0.5 * PX_PER_M} x2={W} y2={-i * 0.5 * PX_PER_M} stroke="#222" />
          ))}
          {/* Shelves */}
          {shelves.map(s => (
            <g key={s.id}
              transform={`translate(${s.x_m * PX_PER_M} ${-s.y_m * PX_PER_M}) rotate(${-s.rotation_deg})`}
              onClick={() => setSelectedId(s.id)}
              className="cursor-pointer"
            >
              <rect
                x={-s.width_m * PX_PER_M / 2}
                y={-s.length_m * PX_PER_M / 2}
                width={s.width_m * PX_PER_M}
                height={s.length_m * PX_PER_M}
                fill={selectedId === s.id ? "#1e3a8a" : "#334155"}
                stroke="#60a5fa"
              />
              <text x={0} y={0} fill="white" fontSize={12} textAnchor="middle" alignmentBaseline="middle">
                {s.id}
              </text>
            </g>
          ))}
          {/* Approach points */}
          {shelves.map(s => {
            const ap = s.approach_point;
            const tipX = ap.x_m + 0.15 * Math.cos((ap.heading_deg * Math.PI) / 180);
            const tipY = ap.y_m + 0.15 * Math.sin((ap.heading_deg * Math.PI) / 180);
            return (
              <line
                key={`ap-${s.id}`}
                x1={ap.x_m * PX_PER_M} y1={-ap.y_m * PX_PER_M}
                x2={tipX * PX_PER_M} y2={-tipY * PX_PER_M}
                stroke="#facc15" strokeWidth={3}
              />
            );
          })}
        </svg>
      </div>

      {selected && (
        <div className="w-64 space-y-2 text-sm">
          <div className="font-bold">{selected.id}</div>
          {(["x_m", "y_m", "width_m", "length_m", "rotation_deg"] as const).map(field => (
            <label key={field} className="block">
              <span className="text-white/60">{field}</span>
              <input
                type="number" step="0.01"
                value={selected[field]}
                onChange={e => updateSelected({ [field]: parseFloat(e.target.value) } as Partial<Shelf>)}
                className="w-full bg-black border border-white/20 px-2 py-1"
              />
            </label>
          ))}
          <div className="pt-2 border-t border-white/10">Approach point</div>
          {(["x_m", "y_m", "heading_deg"] as const).map(field => (
            <label key={field} className="block">
              <span className="text-white/60">{field}</span>
              <input
                type="number" step="0.01"
                value={selected.approach_point[field]}
                onChange={e => updateApproach({ [field]: parseFloat(e.target.value) })}
                className="w-full bg-black border border-white/20 px-2 py-1"
              />
            </label>
          ))}
        </div>
      )}

      {message && <div className="ml-auto text-sm text-white/80">{message}</div>}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add web-app/app/vision/components/LayoutEditorTab.tsx
git commit -m "feat(web-app): add Layout Editor tab with SVG canvas"
```

---

### Task 8.4: Plan & Run tab

**Files:**
- Create: `web-app/app/vision/components/PlanRunTab.tsx`

- [ ] **Step 1: Write `PlanRunTab.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { getShelves, capture, detect, plan } from "../lib/api";
import type { Shelf, Waypoint, PlanMetrics } from "../lib/types";

type TaskType = "navigate" | "pick_place";

export default function PlanRunTab() {
  const [shelves, setShelves] = useState<Shelf[]>([]);
  const [taskType, setTaskType] = useState<TaskType>("pick_place");
  const [src, setSrc] = useState<string>("");
  const [dst, setDst] = useState<string>("");
  const [imageB64, setImageB64] = useState<string | null>(null);
  const [waypoints, setWaypoints] = useState<Waypoint[]>([]);
  const [metrics, setMetrics] = useState<PlanMetrics | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const data = await getShelves();
        setShelves(data.shelves);
        if (data.shelves.length >= 1) setDst(data.shelves[0].id);
        if (data.shelves.length >= 2) setSrc(data.shelves[0].id);
        if (data.shelves.length >= 2) setDst(data.shelves[1].id);
      } catch (e) { setMessage(String(e)); }
    })();
  }, []);

  const handleCapture = async () => {
    try {
      const r = await capture();
      setImageB64(r.image_base64);
      setWaypoints([]);
      setMetrics(null);
    } catch (e) { setMessage(String(e)); }
  };

  const handleDetect = async () => {
    try {
      const r = await detect();
      setImageB64(r.annotated_image_base64);
      setMessage(r.robot_pose ? `Robot at (${r.robot_pose.x_m.toFixed(2)}, ${r.robot_pose.y_m.toFixed(2)}) @ ${r.robot_pose.heading_deg.toFixed(0)}°` : "Markers not found");
    } catch (e) { setMessage(String(e)); }
  };

  const handlePlan = async () => {
    try {
      const r = await plan({
        task: taskType,
        source_shelf_id: taskType === "pick_place" ? src : undefined,
        destination_shelf_id: dst,
      });
      setImageB64(r.annotated_image_base64);
      setWaypoints(r.waypoints);
      setMetrics(r.metrics);
      setMessage("");
    } catch (e) { setMessage(String(e)); }
  };

  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-3 space-y-3">
        <label className="block">
          <span className="text-white/60 text-sm">Task</span>
          <select value={taskType} onChange={e => setTaskType(e.target.value as TaskType)} className="w-full bg-black border border-white/20 px-2 py-1">
            <option value="navigate">Navigate</option>
            <option value="pick_place">Pick &amp; Place</option>
          </select>
        </label>
        {taskType === "pick_place" && (
          <label className="block">
            <span className="text-white/60 text-sm">Source shelf</span>
            <select value={src} onChange={e => setSrc(e.target.value)} className="w-full bg-black border border-white/20 px-2 py-1">
              {shelves.map(s => <option key={s.id} value={s.id}>{s.id}</option>)}
            </select>
          </label>
        )}
        <label className="block">
          <span className="text-white/60 text-sm">Destination shelf</span>
          <select value={dst} onChange={e => setDst(e.target.value)} className="w-full bg-black border border-white/20 px-2 py-1">
            {shelves.map(s => <option key={s.id} value={s.id}>{s.id}</option>)}
          </select>
        </label>
      </div>

      <div className="col-span-6 space-y-2">
        <div className="flex gap-2">
          <button onClick={handleCapture} className="px-3 py-1 bg-gray-600 rounded">Capture</button>
          <button onClick={handleDetect} className="px-3 py-1 bg-blue-600 rounded">Detect</button>
          <button onClick={handlePlan} className="px-3 py-1 bg-green-600 rounded">Plan</button>
        </div>
        {imageB64 && (
          <img src={`data:image/png;base64,${imageB64}`} alt="vision feed" className="w-full border border-white/20" />
        )}
        {message && <div className="text-sm text-white/80">{message}</div>}
      </div>

      <div className="col-span-3 space-y-2">
        <div className="font-bold">Waypoints</div>
        <ol className="text-sm space-y-1 max-h-96 overflow-auto">
          {waypoints.map((w, i) => (
            <li key={i} className="border-l-2 border-blue-400 pl-2">
              <div className="text-white">{w.type}</div>
              {w.type === "turn" && <div className="text-white/60">→ {w.target_heading_deg?.toFixed(0)}°</div>}
              {w.type === "drive" && <div className="text-white/60">→ {w.distance_m?.toFixed(2)} m</div>}
              {(w.type === "grab" || w.type === "place") && <div className="text-white/60">{w.shelf_id}</div>}
            </li>
          ))}
        </ol>
        {metrics && (
          <div className="text-sm pt-2 border-t border-white/10">
            <div>Total distance: {metrics.total_distance_m.toFixed(2)} m</div>
            <div>Est. time: {metrics.estimated_time_s.toFixed(1)} s</div>
          </div>
        )}
        <button disabled className="px-3 py-1 bg-gray-700 rounded opacity-50" title="Hardware integration pending">
          Execute
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add web-app/app/vision/components/PlanRunTab.tsx
git commit -m "feat(web-app): add Plan & Run tab to /vision route"
```

---

### Phase 9 — End-to-end smoke test

### Task 9.1: Manual smoke test and README update

- [ ] **Step 1: Start the backend**

```bash
python -m vision.scripts.run_server
```

Expected: server on `http://localhost:8100`.

- [ ] **Step 2: Start the frontend**

```bash
cd web-app && npm run dev
```

- [ ] **Step 3: Open `http://localhost:3000/vision`**

Verify:
- Calibration tab loads and shows the correct status (both missing if no real camera + real calibration yet).
- Layout Editor tab loads the sample shelves from `shelves.json`, renders them on the SVG canvas, lets you click a shelf to edit its fields, and Save writes back to the file.
- Plan & Run tab loads the shelf dropdowns. Without calibration, the Plan button should return a clear error message; this is expected.

- [ ] **Step 4: Run the full pytest suite**

```bash
pytest vision/tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit any README tweaks**

Update `vision/README.md` with a final "Known limitations" section noting that (a) the HSV ranges probably need tuning for your specific lighting and (b) the robot must be in frame for `/api/plan` to succeed.

```bash
git add vision/README.md
git commit -m "docs(vision): note known prototype limitations"
```

---

## Reference: advisory notes from the spec review

The spec-document-reviewer flagged these minor items as non-blocking. They are addressed in this plan as follows:

1. **Display grid vs planner grid** — clarified in the Conventions section: the planner uses 25 cm cells (`settings.yaml`), the SVG overlay renders 50 cm lines purely for visual reference.
2. **Direction change tolerance** — fixed at 5° in `motion.py::DIRECTION_TOLERANCE_DEG`.
3. **Y-axis convention** — workspace +Y points away from the bottom-left ArUco marker. Headings are counter-clockwise-positive from +X. Documented in Conventions.
4. **`/api/detect` request body** — defined in `schemas.py` as an empty POST (no body required); the server captures a fresh frame internally.
5. **Chessboard `9x6`** — clarified as **inner corner count** in Conventions and in `intrinsic.py::CHESSBOARD_INNER_CORNERS`.

## Reference: advisory notes from the plan review

The plan reviewer flagged these advisory items. Resolved directly in the plan:

- **Silent zero inflation with default config.** Default `obstacle_inflation_m: 0.10` with `cell_size_m: 0.25` previously rounded to `0` cells. `build_occupancy_grid` now uses `math.ceil` so any non-zero inflation produces at least one cell of margin. Covered by `test_grid_small_inflation_rounds_up_not_down`.
- **Boundary rejection in `world_to_cell`.** A robot pose exactly on the far workspace edge used to raise `ValueError`. `world_to_cell` now clamps to the last cell.
- **`lib/types.ts::Settings` incomplete.** Now declares `camera` and `planner` in addition to `workspace` and `robot`.

Left as known limitations (acceptable for phase 1):

- Shelf validation happens per-request rather than at server startup or at PUT time. Malformed configs still surface as clean `412`/`422` errors; the spec's "refuse to start" behavior can be added later if it becomes friction.
- `test_extrinsic.py` only covers save/load round-trip. A synthetic-ArUco test for `calibrate_from_frame` can be added later; for phase 1 the FastAPI integration test in `test_api.py` exercises the stored extrinsics path.
- `routes.Paths` uses class-level attributes as a state container. Functional but fragile across concurrent tests. Can be moved to `app.state` during a later cleanup.
- `make_settings` is imported from `test_grid.py` by `test_motion.py` and `test_task.py`. Minor coupling; moving it to `conftest.py` is a cleanup opportunity.

---

## Testing summary

Running `pytest vision/tests -v` after Task 9.1 should produce the following passing tests:

- `test_parallax.py::test_parallax_height_zero_identity`
- `test_parallax.py::test_parallax_with_height`
- `test_parallax.py::test_parallax_across_workspace` (4 parametrized cases)
- `test_intrinsic.py::test_intrinsic_round_trip`
- `test_extrinsic.py::test_extrinsic_round_trip`
- `test_detection.py::test_detect_robot_position_and_heading` (4 parametrized cases)
- `test_detection.py::test_detect_robot_missing_markers`
- `test_grid.py` (5 tests)
- `test_astar.py` (5 tests)
- `test_motion.py` (5 tests)
- `test_task.py` (2 tests)
- `test_api.py` (8 tests)

**Total: ~40 unit/integration tests.** No frontend tests in phase 1 (manual smoke test in Task 9.1 covers the UI).
