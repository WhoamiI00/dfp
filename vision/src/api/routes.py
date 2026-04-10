"""FastAPI route handlers for the vision module."""
import base64
import time
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
