# Vision Module Design — Robot Detection, Shelf Layout, Path Planning

**Date:** 2026-04-10
**Status:** Draft — pending review
**Scope:** Phase 1 of the DFP (Design and Fabrication Project) reimplementation

---

## 1. Context and background

The DFP project currently contains a `router/` module that implements overhead path planning using a pure top-down camera view. For the reimplementation, the physical setup is changing: the camera will be mounted in a **corner of the room**, providing a **top-side (angled) view** rather than a top-down view. This invalidates several assumptions in the existing code, most importantly the direct pixel-to-floor mapping via a flat homography.

Rather than patching `router/`, this spec defines a **new, self-contained module at `dfp/vision/`** that is built from scratch for the corner-camera setup. The existing `router/` module will be left untouched and can be deprecated later.

The vision module is **phase 1** of a larger robotics prototype. Later phases will integrate the robot's motor controller and grasping mechanism (currently in development). Phase 1's deliverable is:

1. A working vision pipeline that detects the robot and plans paths on snapshots from the corner camera.
2. A web UI (integrated into the existing `web-app/` Next.js project as a new `/vision` route) for editing shelf layouts, triggering captures, and visualizing plans.
3. A task-level planner that produces pick-and-place plans (with stubbed grab/place actions) so the interface is already shaped for future hardware integration.

## 2. Goals

- Detect the robot's pose `(x, y, θ)` in floor-plane coordinates from a single camera snapshot, correcting for perspective and marker height.
- Represent the shelf layout as a JSON config that can be edited through a web UI.
- Plan collision-free paths on a grid, decomposed into turn-and-drive primitives suitable for a non-holonomic (differential drive) robot.
- Plan pick-and-place tasks as compositions of navigation plans with stub grab/place actions.
- Provide a `/vision` route in the existing Next.js web app with three tabs: calibration, layout editor, plan & run.
- Work in **snapshot mode** — the user triggers each capture/plan manually. No continuous video pipeline in phase 1.

## 3. Non-goals

- **Continuous video analysis.** Deferred to a future phase; explicitly out of scope.
- **Robot motor control / hardware integration.** Grab/place actions are stubs. No serial/WiFi to a physical robot.
- **Fixing or migrating the existing `router/` module.** Left as-is; may be deprecated later.
- **Multi-robot support.** One robot, always.
- **Dynamic obstacles.** Shelves are static; no people or moving objects expected.
- **Training a deep learning detector.** Classical CV (HSV + ArUco) only.
- **Automatic shelf detection from the image.** Shelves come from the config file.

## 4. Physical setup assumptions

- **Workspace:** 2.5 m × 2.5 m floor area (5 × 5 cells at 50 cm each, abstractly).
- **Camera:** fixed in one corner of the room, USB webcam or similar. No prior calibration. Will be calibrated per this spec.
- **Robot:** ~50 cm × 50 cm footprint, differential drive (non-holonomic), pulley-based adjustable-height arm. Two colored markers on top — **red** in front ("the head"), **green** in back. Vector between them gives heading.
- **Travel height:** the robot always travels at a fixed configurable height (default 30 cm). Height only changes during grab/place, when the robot is stationary at an approach point.
- **Shelves:** ~50 cm × 100 cm rectangles, static during a run, positions defined in config.
- **ArUco markers:** 4 floor markers placed at known workspace corners for extrinsic calibration.

## 5. Architecture overview

```
                ┌─────────────────────────────────────┐
                │    Next.js web-app (/vision route)   │
                │  ┌───────────┐  ┌──────┐  ┌───────┐  │
                │  │Calibration│  │Layout│  │Plan&Run│  │
                │  └─────┬─────┘  └───┬──┘  └────┬──┘  │
                └────────┼────────────┼──────────┼─────┘
                         │ HTTP/JSON  │          │
                ┌────────▼────────────▼──────────▼─────┐
                │       FastAPI backend (vision/)       │
                │  routes → calibration / detection /   │
                │           planning / rendering        │
                └────────┬──────────────────────────────┘
                         │
                ┌────────▼──────────┐
                │  Camera (OpenCV)   │
                └────────────────────┘
```

- **Vision module** is a self-contained Python package with its own FastAPI server. It never talks to `web-app/` directly — only via HTTP.
- **web-app** gets a new route at `/vision` that is a thin client fetching from the Python backend.
- **Config files** (`settings.yaml`, `shelves.json`, `camera_intrinsics.yaml`, `camera_extrinsics.yaml`) are the single source of truth. The backend reads and writes them; the frontend only knows about them through API responses.

## 6. Module structure

```
dfp/vision/
├── README.md
├── requirements.txt
├── config/
│   ├── settings.yaml
│   ├── camera_intrinsics.yaml   # generated
│   ├── camera_extrinsics.yaml   # generated
│   └── shelves.json             # edited via UI
├── src/
│   ├── __init__.py
│   ├── calibration/
│   │   ├── __init__.py
│   │   ├── intrinsic.py         # chessboard calibration
│   │   ├── extrinsic.py         # ArUco floor marker calibration
│   │   └── parallax.py          # pixel → floor projection with height correction
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── robot.py             # HSV two-marker detector
│   │   └── hsv_ranges.py        # tunable HSV thresholds
│   ├── planning/
│   │   ├── __init__.py
│   │   ├── grid.py              # occupancy grid construction
│   │   ├── astar.py             # A* path search
│   │   ├── motion.py            # non-holonomic decomposition
│   │   └── task.py              # pick-and-place composition
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py            # FastAPI app entry point
│   │   ├── routes.py            # endpoint handlers
│   │   └── schemas.py           # pydantic request/response models
│   └── rendering/
│       ├── __init__.py
│       └── overlay.py           # draw shelves, robot, path on images
├── scripts/
│   ├── capture_chessboard.py    # helper for intrinsic calibration
│   └── run_server.py            # start FastAPI server
└── tests/
    ├── fixtures/                # sample images, mock configs
    ├── test_parallax.py
    ├── test_detection.py
    ├── test_planning.py
    └── test_api.py
```

Each subdirectory has one clear job. Any module can be tested in isolation against fixtures without the other modules running.

## 7. Data models

### 7.1 `config/settings.yaml`

```yaml
workspace:
  width_m: 2.5
  height_m: 2.5
  cell_size_m: 0.25        # planner grid resolution (finer than the 50 cm display grid)
robot:
  footprint_m: [0.5, 0.5]
  travel_height_m: 0.30    # constant height during navigation; used for parallax correction
  markers:
    front_color: red
    back_color: green
camera:
  source: 0                # OpenCV VideoCapture index or RTSP URL
  resolution: [1280, 720]
planner:
  obstacle_inflation_m: 0.10  # safety margin around shelves
```

### 7.2 `config/shelves.json`

```json
{
  "shelves": [
    {
      "id": "shelf_A",
      "x_m": 1.0,
      "y_m": 0.5,
      "width_m": 0.5,
      "length_m": 1.0,
      "rotation_deg": 0,
      "approach_point": {
        "x_m": 1.0,
        "y_m": 1.0,
        "heading_deg": 270
      }
    }
  ]
}
```

- `(x_m, y_m)` is the shelf center in workspace coordinates.
- `rotation_deg` rotates the rectangle about its center (counter-clockwise, 0 = width along X axis).
- `approach_point` is an `(x, y, θ)` pose; the planner routes the robot to arrive at `(x, y)` facing `heading_deg`. The approach point must lie on a free (non-obstacle) cell after inflation — validated at load time.

### 7.3 Camera calibration files

**`camera_intrinsics.yaml`**:
```yaml
image_size: [1280, 720]
camera_matrix: [[fx, 0, cx], [0, fy, cy], [0, 0, 1]]
dist_coeffs: [k1, k2, p1, p2, k3]
calibration_error_px: 0.42
captured_images: 15
```

**`camera_extrinsics.yaml`**:
```yaml
rvec: [r1, r2, r3]
tvec: [t1, t2, t3]
floor_reference_markers:
  - id: 0
    workspace_xy_m: [0.0, 0.0]
  - id: 1
    workspace_xy_m: [2.5, 0.0]
  - id: 2
    workspace_xy_m: [2.5, 2.5]
  - id: 3
    workspace_xy_m: [0.0, 2.5]
calibration_error_px: 1.1
```

### 7.4 Plan output (from `/api/plan`)

```json
{
  "waypoints": [
    {"type": "turn",  "target_heading_deg": 90, "from": {"x_m": 0.5, "y_m": 0.5, "heading_deg": 0}},
    {"type": "drive", "distance_m": 1.0, "from": {...}, "to": {...}},
    {"type": "turn",  "target_heading_deg": 180, "from": {...}},
    {"type": "grab",  "shelf_id": "shelf_A"},
    {"type": "drive", "distance_m": 0.75, "from": {...}, "to": {...}},
    {"type": "place", "shelf_id": "shelf_B"}
  ],
  "annotated_image_base64": "...",
  "metrics": {
    "total_distance_m": 3.2,
    "estimated_time_s": 12.5
  }
}
```

Five waypoint types: `turn`, `drive`, `grab`, `place`, and (for navigate-only tasks) `arrive`.

## 8. Calibration

### 8.1 Intrinsic (one-time)

- User prints a 9×6 chessboard, takes ~15 photos from varied angles (via helper script or through the web UI).
- `cv2.findChessboardCorners` on each image.
- `cv2.calibrateCamera` → camera matrix + distortion coefficients + reprojection error.
- Save to `camera_intrinsics.yaml`.
- Fails with a clear error if reprojection error > 2 px or < 8 valid images.
- Exposed via `POST /api/calibration/intrinsic` accepting multipart-uploaded images.

### 8.2 Extrinsic (per-setup)

- 4 ArUco markers (DICT_4X4_50) placed at known workspace corners.
- Single fresh frame → `cv2.aruco.detectMarkers`.
- Match detected IDs against the 4 expected IDs from `settings.yaml`.
- Build 4 world-point ↔ image-point correspondences.
- `cv2.solvePnP` → `rvec`, `tvec`.
- Save to `camera_extrinsics.yaml`.
- Fails with `422` if any marker is missing, returning `{expected_ids, found_ids}` so the UI can display which ones need repositioning.
- Exposed via `POST /api/calibration/extrinsic`.

### 8.3 Parallax correction (the critical function)

Single function in `calibration/parallax.py`:

```python
def project_pixel_to_floor(
    pixel_uv: tuple[float, float],
    height_above_floor_m: float,
    intrinsics: Intrinsics,
    extrinsics: Extrinsics,
) -> tuple[float, float]:
    """Back-project a pixel observed at a known height above the floor
    to the corresponding point on the floor (z = 0) in workspace coordinates.
    """
```

Math:
1. Undistort the pixel with `cv2.undistortPoints`.
2. Build a 3D ray in camera coordinates: `ray = K^(-1) · [u, v, 1]^T`, normalized.
3. Transform to world coordinates using `rvec`, `tvec`.
4. Intersect the ray with the plane `z = height_above_floor_m` in world space → 3D world point.
5. Project that world point down to `z = 0` → `(x, y)` on the floor.

This is the single load-bearing math function in the system. It is unit-tested against a synthetic camera with known ground truth.

## 9. Detection

Robot detection pipeline (`detection/robot.py`):

1. Load frame from camera.
2. `cv2.undistort` using intrinsic calibration.
3. Convert BGR → HSV.
4. Build two masks using HSV ranges from `hsv_ranges.py`:
   - Red (handles the wrap-around hue: `H ∈ [0,10] ∪ [170,180]`)
   - Green (`H ∈ [40,80]` roughly)
5. Morphological `open` (remove noise) then `close` (fill gaps).
6. Find the largest connected component in each mask → centroid `(u, v)`. If either mask has zero area or the largest blob is below a minimum threshold, abort and return `robot_pose = None`.
7. For each centroid: `project_pixel_to_floor(centroid, travel_height_m)` → floor point.
8. `position = midpoint(floor_red, floor_green)`.
9. `heading_deg = degrees(atan2(floor_red.y - floor_green.y, floor_red.x - floor_green.x))`.
10. Return `RobotPose(x_m, y_m, heading_deg, confidence)`.

Confidence is a simple function of the smaller mask's area relative to the expected marker size. The UI only displays the pose if confidence > 0.5.

HSV ranges are configurable in `hsv_ranges.py` as constants; tuning them once per lighting setup is a manual step.

## 10. Planning

### 10.1 Grid construction (`planning/grid.py`)

- Grid size: `workspace.width_m / cell_size_m` by `workspace.height_m / cell_size_m` (10 × 10 at 25 cm cells by default).
- For each shelf, rasterize its rotated rectangle into grid cells by testing cell centers against the rotated rectangle. Mark those cells as obstacles.
- Inflate obstacles by `obstacle_inflation_m` — every obstacle cell gets its neighbors within the inflation radius also marked as obstacles.
- Validate at construction time: for each shelf, its approach point must be on a free cell. If not, raise `ApproachPointBlockedError(shelf_id)`.

### 10.2 A* (`planning/astar.py`)

Standard A*:
- 8-connected grid (diagonals allowed).
- Step cost = Euclidean distance between adjacent cells (1.0 for cardinal, √2 for diagonal).
- Heuristic = Euclidean distance to goal.
- Returns a list of `(cell_row, cell_col)` from start to goal, inclusive.
- Raises `NoPathError` if the open set is exhausted without reaching the goal.

### 10.3 Non-holonomic decomposition (`planning/motion.py`)

Takes the A* cell list + the robot's current heading and produces the waypoint sequence:

1. Convert cell path to a list of world-coordinate points at cell centers.
2. Collapse consecutive segments in the same direction into one long `drive` segment.
3. At each direction change, emit a `turn` primitive with the new target heading.
4. Prepend a `turn` to align from the current heading to the first segment's direction.
5. Append a `turn` to match the final approach heading.
6. Emit the final `arrive` waypoint for navigate-only tasks.

### 10.4 Task layer (`planning/task.py`)

```python
def plan_navigate_to(shelf_id, current_pose) -> list[Waypoint]: ...

def plan_pick_and_place(src_id, dst_id, current_pose) -> list[Waypoint]:
    to_src = plan_navigate_to(src_id, current_pose)
    pose_at_src = shelves[src_id].approach_point
    to_dst = plan_navigate_to(dst_id, pose_at_src)
    return to_src + [GrabAction(src_id)] + to_dst + [PlaceAction(dst_id)]
```

Grab and Place are stub actions with just `{type, shelf_id}`. The robot controller (future work) will consume them.

## 11. FastAPI contract

All endpoints mounted under `/api`. CORS enabled for `http://localhost:3000` (Next.js dev server). Request/response bodies are pydantic models in `api/schemas.py`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/settings` | Read `settings.yaml` as JSON |
| GET | `/api/shelves` | Read `shelves.json` |
| PUT | `/api/shelves` | Validate and write `shelves.json` |
| GET | `/api/calibration/status` | `{intrinsic: bool, extrinsic: bool}` |
| POST | `/api/calibration/intrinsic` | Multipart images → calibrate → save file |
| POST | `/api/calibration/extrinsic` | Use fresh camera frame → calibrate → save file |
| GET | `/api/capture` | Fresh frame → `{image_base64, timestamp}` |
| POST | `/api/detect` | Fresh frame + detection → `{robot_pose, annotated_image}` |
| POST | `/api/plan` | Body: `{task: "navigate"\|"pick_place", src?, dst}` → full plan |

## 12. Frontend design

New route: `web-app/app/vision/page.tsx`. Single page with three tabs.

### 12.1 Tab: Calibration

- Status badges: `Intrinsic ✓/✗` and `Extrinsic ✓/✗`, loaded from `GET /api/calibration/status`.
- Upload widget: drop or pick ~15 chessboard images → `POST /api/calibration/intrinsic` → show reprojection error on success.
- "Run extrinsic calibration" button → `POST /api/calibration/extrinsic` → show reprojection error. If markers missing, display expected vs. found IDs.
- Other tabs are disabled (greyed out with tooltip) until both are present.

### 12.2 Tab: Layout editor

- SVG canvas at 100 px/m scale (250×250 px viewBox for the 2.5×2.5 m workspace, CSS-scaled for display).
- Workspace rectangle border.
- Optional 50 cm grid overlay toggle.
- Shelves rendered as rotatable rectangles with drag handles.
- Approach points rendered as arrow glyphs at their `(x, y, θ)` pose.
- Right-side property panel: editable number inputs for `id`, `x_m`, `y_m`, `width_m`, `length_m`, `rotation_deg`, `approach_point.x_m`, `approach_point.y_m`, `approach_point.heading_deg`.
- Buttons: `Add Shelf`, `Delete Selected`, `Save`.
- Unsaved-changes indicator in header. `Save` sends `PUT /api/shelves` and refreshes.

### 12.3 Tab: Plan & Run

Three-column layout:

- **Left — task inputs**: task type dropdown (`Navigate` / `Pick & Place`), source shelf dropdown (hidden if Navigate), destination shelf dropdown.
- **Middle — camera view**: Large panel with three action buttons above it:
  - `Capture` → `GET /api/capture` → show raw frame.
  - `Detect` → `POST /api/detect` → show frame with robot overlay.
  - `Plan` → `POST /api/plan` → show frame with full plan overlay (robot + shelves + path).
- **Right — plan details**: collapsible waypoint list (each with type, distance, heading), metrics block (total distance, estimated time), disabled `Execute` button with tooltip "Hardware integration pending".

Tech: plain React `useState` (no global store), SVG for the layout editor, `fetch` for backend calls, Tailwind for styling (already in the project).

## 13. Error handling

Errors happen at external boundaries. Each returns a typed error code the UI maps to a specific message.

| Situation | Endpoint | Response |
|---|---|---|
| Camera unplugged / busy | `/api/capture` | `503 {error: "camera_unavailable"}` |
| Intrinsic calibration missing | any that needs it | `412 {error: "intrinsic_calibration_missing"}` |
| Extrinsic calibration missing | any that needs it | `412 {error: "extrinsic_calibration_missing"}` |
| ArUco markers not detected | `/api/calibration/extrinsic` | `422 {error: "aruco_not_found", expected_ids, found_ids}` |
| Robot markers not detected | `/api/detect` | `200 {robot_pose: null, reason: "markers_not_found"}` (not an error, just a retry) |
| Path not found | `/api/plan` | `422 {error: "no_path", reason}` |
| Approach point blocked by inflated obstacle | startup or plan | `422 {error: "approach_point_blocked", shelf_id}` |
| Malformed `shelves.json` | any that reads it | pydantic validation error at load time, server refuses to start |

Internal code paths trust each other — no defensive validation between modules. All validation happens once at the boundary.

## 14. Testing plan

Tests use pytest. Each module has its own test file with fixtures under `tests/fixtures/`.

- **`test_parallax.py`** — synthetic camera (hand-constructed intrinsics + extrinsics) + synthetic marker at known floor positions and heights. Assert reconstructed floor position is within 1 cm for heights 0 to 50 cm. Include the degenerate height = 0 case.
- **`test_detection.py`** — sample rendered JPEG fixtures showing the robot at known poses (generated with OpenCV drawing primitives, since no hardware yet). Assert detected position within 2 cm and heading within 5°.
- **`test_planning.py`** —
  - A* finds the known optimal path on an empty grid.
  - A* routes around a shelf rectangle.
  - Non-holonomic decomposition of a diagonal path produces the correct turn+drive sequence.
  - Unreachable goal raises `NoPathError`.
  - `plan_pick_and_place` produces stitched plan with grab and place actions in the right positions.
  - Blocked approach point raises `ApproachPointBlockedError` at grid construction.
- **`test_api.py`** — FastAPI `TestClient` with a mock `FakeCamera` that returns a fixture image. Hit each endpoint, assert response shape, assert error codes for missing calibrations.

Fixtures: ~5 rendered images, 3 `shelves.json` configurations, 1 mock calibration pair.

No frontend tests in phase 1 — UI is smoke-tested by clicking through. Playwright may be added later if the UI grows.

## 15. Open questions and deferred items

**Open (ask before implementation if unclear):**
- Exact camera hardware (affects intrinsic calibration assumptions). Spec assumes a generic USB webcam at 1280×720.
- HSV ranges for red and green markers. Will need to be tuned once per lighting setup; starting values in `hsv_ranges.py` are a best guess.

**Explicitly deferred to later phases:**
- Continuous video / live tracking (user noted "would be very heavy", saving for later).
- Real robot motor control and grab/place mechanism integration.
- Automatic HSV tuning UI.
- Deprecation or removal of the existing `router/` module.
- Multi-robot support.
- Any frontend tests.

## 16. Success criteria for phase 1

The phase 1 prototype is considered working when:

1. Calibration tab successfully calibrates intrinsics and extrinsics from the physical setup.
2. Layout editor successfully creates, edits, and saves a shelf layout.
3. Plan & Run tab, given a capture with the robot visible in frame, detects the robot pose within ~2 cm / ~5° of ground truth, plans a pick-and-place path between two shelves, and renders the full plan overlay on the annotated image.
4. All unit tests and the API integration test pass.

Hardware integration is explicitly **not** a phase 1 success criterion.
