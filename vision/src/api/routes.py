"""FastAPI route handlers for the vision module."""
import base64
import time
from pathlib import Path
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, UploadFile, File
from vision.src.api.schemas import (
    ShelvesPayload, ShelfSchema, ApproachPointSchema,
    CalibrationStatus, IntrinsicResult, ExtrinsicResult, ManualExtrinsicRequest,
    CaptureResponse, DetectResponse, DetectDebugResponse, RobotPoseSchema,
    PlanRequest, PlanResponse, WaypointSchema, Pose2DSchema, PlanMetrics,
    CameraMode,
    AutoDetectShelvesRequest, AutoDetectShelvesResponse, AutoDetectedShelf,
)
from vision.src.api.config_loader import (
    load_settings, load_shelves, save_shelves, ConfigError,
)
from vision.src.api.camera import Camera, CameraError, SwitchableCamera
from vision.src.calibration.intrinsic import (
    calibrate_from_images, save_intrinsics, load_intrinsics, IntrinsicCalibrationError,
)
from vision.src.calibration.extrinsic import (
    calibrate_from_frame, save_extrinsics, load_extrinsics, ExtrinsicCalibrationError,
)
from vision.src.calibration.synthetic import (
    build_synthetic_calibration, SYNTHETIC_CAMERA_HEIGHT_M,
)
from vision.src.detection.robot import detect_robot, mask_for_ranges, largest_blob
from vision.src.detection.shelves import detect_shelf_candidates
from vision.src.detection.hsv_ranges import get_ranges, MIN_MARKER_AREA_PX
from vision.src.planning.task import plan_navigate_to, plan_pick_and_place
from vision.src.planning.errors import NoPathError, ApproachPointBlockedError
from vision.src.rendering.overlay import draw_overlay
from vision.src.models import (
    Shelf, ApproachPoint, Extrinsics, ExtrinsicMarker, Pose2D,
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


@router.post("/layout/auto_detect", response_model=AutoDetectShelvesResponse)
def auto_detect_shelves(request: AutoDetectShelvesRequest):
    """Detect coloured shelf markers in the current frame, project them to
    world coordinates, and optionally persist as shelves.json.

    The detector takes the top `max_count` blobs by area and sorts them
    left-to-right. Shelf IDs are generated as `<id_prefix>A`, `<id_prefix>B`,
    ... Approach points are placed `approach_offset_m` metres below each
    shelf (toward the robot) with heading 90 degrees — good enough for a
    top-row layout; override with PUT /shelves for anything fancier.
    """
    intrinsics = _require_intrinsics()
    extrinsics = _require_extrinsics()
    settings = load_settings(Paths.settings)
    frame = _capture_frame()

    try:
        marker_ranges = get_ranges(request.marker_color)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "unknown_marker_color", "message": str(e)},
        )

    candidates = detect_shelf_candidates(
        frame,
        marker_ranges=marker_ranges,
        intrinsics=intrinsics,
        extrinsics=extrinsics,
        max_count=request.max_count,
    )
    if not candidates:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "no_shelf_markers_found",
                "message": (
                    f"No {request.marker_color} blobs above the minimum area "
                    "threshold were found in the current frame. Check lighting, "
                    "marker colour, or widen the HSV range in hsv_ranges.py."
                ),
            },
        )

    ws = settings.workspace
    shelves: list[Shelf] = []
    for i, cand in enumerate(candidates):
        shelf_id = f"{request.id_prefix}{chr(ord('A') + i)}"
        approach_y = max(0.0, min(ws.height_m, cand.world_y_m - request.approach_offset_m))
        shelves.append(
            Shelf(
                id=shelf_id,
                x_m=cand.world_x_m,
                y_m=cand.world_y_m,
                width_m=request.shelf_width_m,
                length_m=request.shelf_length_m,
                rotation_deg=0.0,
                approach_point=ApproachPoint(
                    x_m=cand.world_x_m,
                    y_m=approach_y,
                    heading_deg=90.0,
                ),
            )
        )

    if request.persist:
        save_shelves(shelves, Paths.shelves)

    annotated = draw_overlay(
        frame, shelves, robot_pose=None, waypoints=[],
        intrinsics=intrinsics, extrinsics=extrinsics,
        travel_height_m=settings.robot.travel_height_m,
    )

    return AutoDetectShelvesResponse(
        shelves=[
            AutoDetectedShelf(
                id=shelves[i].id,
                pixel_cx=cand.pixel_cx,
                pixel_cy=cand.pixel_cy,
                pixel_area=cand.pixel_area,
                world_x_m=cand.world_x_m,
                world_y_m=cand.world_y_m,
            )
            for i, cand in enumerate(candidates)
        ],
        annotated_image_base64=_encode_image(annotated),
        persisted=request.persist,
    )


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


@router.post("/calibration/extrinsic/manual", response_model=ExtrinsicResult)
def calibration_extrinsic_manual(request: ManualExtrinsicRequest):
    """Compute extrinsics from 4 manually clicked workspace corners."""
    intrinsics = _require_intrinsics()
    if len(request.corner_pixels) != 4:
        raise HTTPException(
            status_code=400,
            detail={"error": "need_exactly_4_corners"},
        )
    settings = load_settings(Paths.settings)
    ws_w = settings.workspace.width_m
    ws_h = settings.workspace.height_m

    object_points = np.array(
        [
            [0.0, 0.0, 0.0],
            [ws_w, 0.0, 0.0],
            [ws_w, ws_h, 0.0],
            [0.0, ws_h, 0.0],
        ],
        dtype=np.float64,
    )
    image_points = np.array(request.corner_pixels, dtype=np.float64)

    ok, rvec, tvec = cv2.solvePnP(
        object_points,
        image_points,
        intrinsics.camera_matrix,
        intrinsics.dist_coeffs,
        flags=cv2.SOLVEPNP_IPPE,
    )
    if not ok:
        raise HTTPException(
            status_code=422,
            detail={"error": "solvepnp_failed"},
        )

    projected, _ = cv2.projectPoints(
        object_points, rvec, tvec, intrinsics.camera_matrix, intrinsics.dist_coeffs
    )
    error = float(np.linalg.norm(projected.reshape(-1, 2) - image_points, axis=1).mean())

    markers = [
        ExtrinsicMarker(id=0, workspace_xy_m=(0.0, 0.0)),
        ExtrinsicMarker(id=1, workspace_xy_m=(ws_w, 0.0)),
        ExtrinsicMarker(id=2, workspace_xy_m=(ws_w, ws_h)),
        ExtrinsicMarker(id=3, workspace_xy_m=(0.0, ws_h)),
    ]
    extrinsics = Extrinsics(
        rvec=rvec.flatten(),
        tvec=tvec.flatten(),
        floor_reference_markers=markers,
        calibration_error_px=error,
    )
    save_extrinsics(extrinsics, Paths.extrinsics)
    return ExtrinsicResult(calibration_error_px=error)


@router.post("/calibration/synthetic")
def calibration_synthetic():
    """Dev-only: inject synthetic intrinsics + extrinsics for a top-down
    overhead view of the workspace, using the current camera frame's
    dimensions. Lets the full pipeline run without real calibration.
    """
    settings = load_settings(Paths.settings)
    frame = _capture_frame()
    intrinsics, extrinsics = build_synthetic_calibration(frame, settings)
    save_intrinsics(intrinsics, Paths.intrinsics)
    save_extrinsics(extrinsics, Paths.extrinsics)
    return {
        "ok": True,
        "image_size": list(intrinsics.image_size),
        "focal_length_px": float(intrinsics.camera_matrix[0, 0]),
        "synthetic_camera_height_m": SYNTHETIC_CAMERA_HEIGHT_M,
    }


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


# --- Camera mode (test image override) -------------------------------------

@router.get("/camera/mode", response_model=CameraMode)
def camera_mode():
    if isinstance(_camera, SwitchableCamera):
        return CameraMode(mode=_camera.mode)
    return CameraMode(mode="live")


@router.post("/camera/image", response_model=CameraMode)
async def camera_set_image(file: UploadFile = File(...)):
    if not isinstance(_camera, SwitchableCamera):
        raise HTTPException(
            status_code=409,
            detail={"error": "camera_not_switchable"},
        )
    data = await file.read()
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_image"},
        )
    _camera.set_image(img)
    return CameraMode(mode=_camera.mode)


@router.delete("/camera/image", response_model=CameraMode)
def camera_clear_image():
    if not isinstance(_camera, SwitchableCamera):
        raise HTTPException(
            status_code=409,
            detail={"error": "camera_not_switchable"},
        )
    _camera.clear_image()
    return CameraMode(mode=_camera.mode)


# --- Capture / detect -------------------------------------------------------

@router.get("/capture", response_model=CaptureResponse)
def capture():
    frame = _capture_frame()
    return CaptureResponse(image_base64=_encode_image(frame), timestamp=time.time())


@router.post("/detect/debug", response_model=DetectDebugResponse)
def detect_debug():
    """Run the color masks on the current frame and return an annotated
    overlay showing what the detector actually picks up. Used for tuning
    HSV ranges or diagnosing 'markers not found' failures."""
    settings = load_settings(Paths.settings)
    frame = _capture_frame()
    front_ranges = get_ranges(settings.robot.markers.front_color)
    back_ranges = get_ranges(settings.robot.markers.back_color)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    front_mask = mask_for_ranges(hsv, front_ranges)
    back_mask = mask_for_ranges(hsv, back_ranges)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    overlay = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    overlay[front_mask > 0] = (180, 80, 255)   # magenta for front mask
    overlay[back_mask > 0] = (255, 150, 40)    # blue for back mask

    front_blob = largest_blob(front_mask)
    back_blob = largest_blob(back_mask)

    # Draw a crosshair at each centroid if found.
    for blob, color in ((front_blob, (0, 0, 255)), (back_blob, (255, 0, 0))):
        if blob is not None:
            cx, cy, _ = blob
            cv2.drawMarker(overlay, (int(cx), int(cy)), color,
                           markerType=cv2.MARKER_CROSS, markerSize=30, thickness=2)

    return DetectDebugResponse(
        front_color_name=settings.robot.markers.front_color,
        back_color_name=settings.robot.markers.back_color,
        min_marker_area_px=MIN_MARKER_AREA_PX,
        front_largest_area_px=(front_blob[2] if front_blob else 0),
        back_largest_area_px=(back_blob[2] if back_blob else 0),
        front_centroid_px=(
            (float(front_blob[0]), float(front_blob[1])) if front_blob else None
        ),
        back_centroid_px=(
            (float(back_blob[0]), float(back_blob[1])) if back_blob else None
        ),
        mask_overlay_base64=_encode_image(overlay),
    )


@router.post("/detect", response_model=DetectResponse)
def detect():
    intrinsics = _require_intrinsics()
    extrinsics = _require_extrinsics()
    settings = load_settings(Paths.settings)
    shelves = load_shelves(Paths.shelves)
    frame = _capture_frame()

    pose = detect_robot(
        frame, intrinsics, extrinsics, settings.robot.travel_height_m,
        front_ranges=get_ranges(settings.robot.markers.front_color),
        back_ranges=get_ranges(settings.robot.markers.back_color),
    )
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

    pose = detect_robot(
        frame, intrinsics, extrinsics, settings.robot.travel_height_m,
        front_ranges=get_ranges(settings.robot.markers.front_color),
        back_ranges=get_ranges(settings.robot.markers.back_color),
    )
    if pose is None:
        raise HTTPException(
            status_code=422,
            detail={"error": "robot_not_detected"},
        )

    # Clamp small calibration-induced overshoots to the workspace edge so the
    # planner doesn't hard-fail on slightly-off extrinsics. Only error out if
    # the pose is wildly outside — more than 1 workspace width/height away —
    # which almost certainly means calibration is fundamentally wrong.
    ws = settings.workspace
    tolerance_w = ws.width_m
    tolerance_h = ws.height_m
    if (
        pose.x_m < -tolerance_w
        or pose.x_m > 2 * ws.width_m
        or pose.y_m < -tolerance_h
        or pose.y_m > 2 * ws.height_m
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "robot_outside_workspace",
                "message": (
                    f"Detected robot pose ({pose.x_m:.2f}, {pose.y_m:.2f}) m is "
                    f"far outside the {ws.width_m:.2f} x {ws.height_m:.2f} m "
                    "workspace. Extrinsic calibration is wrong for this image — "
                    "re-run the manual 4-corner calibration."
                ),
                "pose": {"x_m": pose.x_m, "y_m": pose.y_m},
            },
        )

    clamped_x = min(max(pose.x_m, 0.0), ws.width_m)
    clamped_y = min(max(pose.y_m, 0.0), ws.height_m)
    current = Pose2D(x_m=clamped_x, y_m=clamped_y, heading_deg=pose.heading_deg)

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
