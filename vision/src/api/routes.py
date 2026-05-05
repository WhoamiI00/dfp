"""FastAPI route handlers for the vision module."""
import base64
import json
import threading
import time
from pathlib import Path
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from vision.src.api.schemas import (
    ShelvesPayload, ShelfSchema, ApproachPointSchema,
    CalibrationStatus, IntrinsicResult, ExtrinsicResult, ManualExtrinsicRequest,
    CaptureResponse, DetectResponse, DetectDebugResponse, RobotPoseSchema,
    PlanRequest, PlanResponse, WaypointSchema, Pose2DSchema, PlanMetrics,
    ExecuteRequest, ExecuteResponse, ExecuteCommandLog, RobotSendRequest,
    CameraMode, RobotMode, RobotModeRequest, ExecuteStreamRequest,
    AutoDetectShelvesRequest, AutoDetectShelvesResponse, AutoDetectedShelf,
    HsvSampleRequest, HsvSampleResponse, HsvBand,
    CustomHsvUpsertRequest, CustomHsvEntry, CustomHsvListResponse,
    OrderSchema, OrderCreateRequest, OrdersListResponse,
    InventoryResponse, ShelfInventory, SkuTotal, ShelfInventoryUpdate,
    ReplenishProposalSchema, ReplenishPreviewResponse,
    ReplenishRunRequest, ReplenishRunResponse,
    CannedExecuteRequest, CannedExecuteResponse, CannedExecuteStep,
    RunNextOrderResponse,
    MovementStepSchema, MovementPlanSchema,
    MovementPlansListResponse, MovementPlanRunResponse,
)
from vision.src.api.config_loader import (
    load_settings, load_shelves, save_shelves, ConfigError,
    load_custom_hsv, save_custom_hsv,
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
from vision.src.detection.aruco_robot import detect_robot_aruco
from vision.src.detection.shelves import detect_shelf_candidates
from vision.src.detection.hsv_ranges import (
    HsvRange, get_ranges, MIN_MARKER_AREA_PX, sample_hsv_range_from_pixel,
)
from vision.src.planning.task import plan_navigate_to, plan_pick_and_place
from vision.src.planning.errors import NoPathError, ApproachPointBlockedError
from vision.src.planning.controller import (
    at_goal, is_stuck, goal_pose_for_shelf, next_command, pose_from_detection,
    StepHistory,
)
from vision.src.rendering.overlay import draw_overlay
from vision.src.robot.protocol import plan_to_chars
from vision.src.robot.link import send_sequence, is_sim_mode, set_sim_mode
from vision.src.robot.wifi_link import WifiLink
from vision.src.models import (
    Shelf, ApproachPoint, Extrinsics, ExtrinsicMarker, Pose2D,
    TurnWaypoint, DriveWaypoint, GrabWaypoint, PlaceWaypoint, ArriveWaypoint,
    Order,
)
from vision.src.inventory.orders import OrderQueue, OrderQueueError
from vision.src.inventory.replenish import replenish_plan, ReplenishProposal


# Paths are injected from server.py
class Paths:
    settings: Path
    shelves: Path
    intrinsics: Path
    extrinsics: Path
    custom_hsv: Path
    orders_db: Path
    movement_plans: Path


# Camera singleton is injected from server.py
_camera: Camera | None = None
# Order queue singleton is injected from server.py too. None when no
# inventory feature is wired up — endpoints check and 503 if missing.
_orders: "OrderQueue | None" = None


def set_state(paths: Paths, camera: Camera, orders: "OrderQueue | None" = None) -> None:
    global _camera, _orders
    Paths.settings = paths.settings
    Paths.shelves = paths.shelves
    Paths.intrinsics = paths.intrinsics
    Paths.extrinsics = paths.extrinsics
    Paths.custom_hsv = paths.custom_hsv
    Paths.orders_db = paths.orders_db
    # Movement plans path is optional — older test setups inject a Paths
    # object without it. Default to a sibling of orders_db so plans land
    # in the same state dir.
    Paths.movement_plans = getattr(
        paths, "movement_plans",
        paths.orders_db.parent / "movement_plans.json",
    )
    _camera = camera
    _orders = orders


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


def _capture_frame(fresh: bool = True) -> np.ndarray:
    """Capture a frame for an HTTP request.

    `fresh=True` is the default — used for /detect, /plan, /execute, and the
    closed-loop step controller, which all depend on the frame reflecting
    the robot's current physical state.

    Pass `fresh=False` for viewfinder-style endpoints (the bare /capture and
    /detect/debug) where the user is just looking, and the per-call drain
    cost (~100 ms on a 1080p IP Webcam) makes the UI feel laggy.
    """
    try:
        return _camera.capture(fresh=fresh)
    except CameraError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": "camera_unavailable", "message": str(e)},
        )


def _detect_robot_dispatch(frame, intrinsics, extrinsics, settings):
    """Pick the detector based on settings.robot.detector and run it.

    Centralised so /detect, /plan, /execute, /execute/stream all behave the
    same way without duplicating the if/else. Returns a RobotPose or None.
    """
    mode = settings.robot.detector
    travel_h = settings.robot.travel_height_m
    tag_id = settings.robot.markers.tag_id

    if mode in ("aruco", "aruco_then_hsv"):
        pose = detect_robot_aruco(frame, intrinsics, extrinsics, travel_h, tag_id)
        if pose is not None:
            return pose
        if mode == "aruco":
            return None  # explicit aruco-only -> no fallback

    # HSV path (mode == "hsv" or aruco_then_hsv with no tag found).
    return detect_robot(
        frame, intrinsics, extrinsics, travel_h,
        front_ranges=_resolve_color(settings.robot.markers.front_color),
        back_ranges=_resolve_color(settings.robot.markers.back_color),
    )


def _resolve_color(name: str) -> list[HsvRange]:
    """Look up an HSV range by colour name, checking user-saved custom
    colours first (from custom_hsv.yaml) then falling back to the
    built-in NAMED_HSV_RANGES in hsv_ranges.py."""
    key = name.strip().lower()
    try:
        custom = load_custom_hsv(Paths.custom_hsv) if Paths.custom_hsv else {}
    except ConfigError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "custom_hsv_config_error", "message": str(e)},
        )
    if key in custom:
        return custom[key]
    try:
        return get_ranges(name)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "unknown_marker_color", "message": str(e)},
        )


def _has_shelf(shelves: list[Shelf], shelf_id: str) -> bool:
    return any(s.id == shelf_id for s in shelves)


def _run_manipulator_sequence(
    wifi_link, link_cfg, action: str, shelf: Shelf | None,
):
    """Run a grab or place sequence and return a list of SubAcks for the log.

    Routes through the WiFi link when one is available, else falls back to
    the fake link (sim mode) which just emits a single "OK" SubAck.
    """
    from vision.src.robot.wifi_link import SubAck
    floor_cm = shelf.floor_distance_cm if shelf is not None else None

    if wifi_link is not None:
        if action == "grab":
            return wifi_link.grab_at(floor_cm)
        return wifi_link.place_at(floor_cm)

    # Sim path: pretend the whole multi-step sequence happened in one beat.
    # Mirrors the legacy single-char G/P semantics so existing sim tests
    # don't have to know about the new lift/slider/gripper plumbing.
    from vision.src.robot.fake_link import send_sequence_fake
    ch = "G" if action == "grab" else "P"
    fake = send_sequence_fake(ch)
    log_entry = fake.log[0] if fake.log else None
    return [SubAck(
        cmd=ch,
        reply=log_entry.reply if log_entry else "OK",
        elapsed_ms=log_entry.elapsed_ms if log_entry else 0,
        ok=fake.ok, error=fake.error,
    )]


def _refresh_shelves_from_frame(intrinsics, extrinsics, settings) -> list[Shelf]:
    """Detect shelves in the current frame and persist them.

    Uses the configured robot front-marker colour as the shelf marker colour
    (single-colour shelves are the common case; multi-colour cells need
    explicit `/layout/auto_detect` calls per colour).

    Returns [] on any failure (camera dead, no blobs, unknown colour). Caller
    decides whether to fall back to disk.
    """
    try:
        frame = _capture_frame()
    except CameraError:
        return []

    marker_color = settings.robot.markers.front_color
    try:
        marker_ranges = _resolve_color(marker_color)
    except HTTPException:
        return []

    candidates = detect_shelf_candidates(
        frame,
        marker_ranges=marker_ranges,
        intrinsics=intrinsics,
        extrinsics=extrinsics,
        max_count=16,
    )
    if not candidates:
        return []

    shelves = _shelves_from_candidates(
        candidates, settings,
        id_prefix="cell_",
        approach_offset_m=0.30,
        shelf_width_m=0.30,
        shelf_length_m=0.30,
    )
    save_shelves(shelves, Paths.shelves)
    return shelves


def _shelves_from_candidates(
    candidates,
    settings,
    *,
    id_prefix: str,
    approach_offset_m: float,
    shelf_width_m: float,
    shelf_length_m: float,
) -> list[Shelf]:
    """Build full Shelf objects from auto-detected candidates.

    Picks the approach side (north/south) per shelf based on which side has
    more free workspace — better than a hardcoded north-only default for
    layouts where shelves are near a wall. Approach heading is set so
    "drive forward" moves the robot toward the shelf.
    """
    ws = settings.workspace
    shelves: list[Shelf] = []
    for i, cand in enumerate(candidates):
        shelf_id = f"{id_prefix}{chr(ord('A') + i)}"
        space_south = cand.world_y_m
        space_north = ws.height_m - cand.world_y_m
        if space_north >= space_south:
            approach_y = min(ws.height_m, cand.world_y_m + approach_offset_m)
            heading = 270.0
        else:
            approach_y = max(0.0, cand.world_y_m - approach_offset_m)
            heading = 90.0
        shelves.append(
            Shelf(
                id=shelf_id,
                x_m=cand.world_x_m,
                y_m=cand.world_y_m,
                width_m=shelf_width_m,
                length_m=shelf_length_m,
                rotation_deg=0.0,
                approach_point=ApproachPoint(
                    x_m=cand.world_x_m,
                    y_m=approach_y,
                    heading_deg=heading,
                ),
            )
        )
    return shelves


def _band_from_range(rng: HsvRange) -> HsvBand:
    lo, hi = rng
    return HsvBand(
        h_min=int(lo[0]), s_min=int(lo[1]), v_min=int(lo[2]),
        h_max=int(hi[0]), s_max=int(hi[1]), v_max=int(hi[2]),
    )


def _range_from_band(band: HsvBand) -> HsvRange:
    return (
        np.array([band.h_min, band.s_min, band.v_min], dtype=np.uint8),
        np.array([band.h_max, band.s_max, band.v_max], dtype=np.uint8),
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
        sku_id=s.sku_id,
        inventory_count=s.inventory_count,
        capacity=s.capacity,
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
        sku_id=s.sku_id,
        inventory_count=s.inventory_count,
        capacity=s.capacity,
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
        # Exposed so the Manual tab can build the ESP32 URL without
        # hardcoding it. Browser fetches /cmd directly (skips backend).
        "robot_link": {
            "type": settings.robot_link.type,
            "host": settings.robot_link.host,
            "port": settings.robot_link.port,
        },
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

    marker_ranges = _resolve_color(request.marker_color)

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

    shelves = _shelves_from_candidates(
        candidates, settings,
        id_prefix=request.id_prefix,
        approach_offset_m=request.approach_offset_m,
        shelf_width_m=request.shelf_width_m,
        shelf_length_m=request.shelf_length_m,
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


# --- HSV color picker / custom ranges --------------------------------------

@router.post("/hsv/sample", response_model=HsvSampleResponse)
def hsv_sample(request: HsvSampleRequest):
    """Sample the current camera frame at (pixel_u, pixel_v) and return
    the median HSV plus a suggested forgiving range. Used by the Calibration
    tab's color picker to build a tolerant marker range from a single click.
    """
    # The user just clicked on the displayed frame — they expect to sample
    # what they saw, which means the buffered frame, not whatever the next
    # drained frame turns out to be.
    frame = _capture_frame(fresh=False)
    try:
        ranges, median = sample_hsv_range_from_pixel(
            frame,
            pixel_uv=(request.pixel_u, request.pixel_v),
            patch_size=max(1, request.patch_size),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_pixel", "message": str(e)},
        )
    return HsvSampleResponse(
        median_h=median[0],
        median_s=median[1],
        median_v=median[2],
        bands=[_band_from_range(r) for r in ranges],
    )


@router.get("/hsv/custom_ranges", response_model=CustomHsvListResponse)
def list_custom_hsv_ranges():
    try:
        custom = load_custom_hsv(Paths.custom_hsv) if Paths.custom_hsv else {}
    except ConfigError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "custom_hsv_config_error", "message": str(e)},
        )
    return CustomHsvListResponse(
        entries=[
            CustomHsvEntry(name=name, bands=[_band_from_range(r) for r in ranges])
            for name, ranges in sorted(custom.items())
        ]
    )


@router.put("/hsv/custom_ranges/{name}", response_model=CustomHsvEntry)
def upsert_custom_hsv_range(name: str, request: CustomHsvUpsertRequest):
    key = name.strip().lower()
    if not key or not key.replace("_", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_color_name",
                "message": "Color names must be non-empty alphanumeric (underscores allowed).",
            },
        )
    if not request.bands:
        raise HTTPException(
            status_code=400,
            detail={"error": "empty_bands", "message": "At least one HSV band required."},
        )

    custom = load_custom_hsv(Paths.custom_hsv) if Paths.custom_hsv.exists() else {}
    custom[key] = [_range_from_band(b) for b in request.bands]
    save_custom_hsv(custom, Paths.custom_hsv)

    return CustomHsvEntry(
        name=key,
        bands=[_band_from_range(r) for r in custom[key]],
    )


@router.delete("/hsv/custom_ranges/{name}")
def delete_custom_hsv_range(name: str):
    key = name.strip().lower()
    if not Paths.custom_hsv.exists():
        raise HTTPException(
            status_code=404,
            detail={"error": "custom_hsv_not_found"},
        )
    custom = load_custom_hsv(Paths.custom_hsv)
    if key not in custom:
        raise HTTPException(
            status_code=404,
            detail={"error": "custom_hsv_not_found", "name": key},
        )
    del custom[key]
    save_custom_hsv(custom, Paths.custom_hsv)
    return {"ok": True, "removed": key}


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
def capture(fresh: bool = False):
    """Return a single frame as base64 PNG. Default `fresh=False` skips the
    drain step so the viewfinder feels snappy on a 1080p IP Webcam (~30 ms
    instead of ~100 ms per call). Pass `?fresh=true` if you specifically
    need a guaranteed-current frame."""
    frame = _capture_frame(fresh=fresh)
    return CaptureResponse(image_base64=_encode_image(frame), timestamp=time.time())


@router.post("/detect/debug", response_model=DetectDebugResponse)
def detect_debug():
    """Run the color masks on the current frame and return an annotated
    overlay showing what the detector actually picks up. Used for tuning
    HSV ranges or diagnosing 'markers not found' failures."""
    settings = load_settings(Paths.settings)
    # Debug view — the user is iterating on thresholds, latency matters
    # more than guaranteed-fresh frames here.
    frame = _capture_frame(fresh=False)
    front_ranges = _resolve_color(settings.robot.markers.front_color)
    back_ranges = _resolve_color(settings.robot.markers.back_color)

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

    pose = _detect_robot_dispatch(frame, intrinsics, extrinsics, settings)
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

    pose = _detect_robot_dispatch(frame, intrinsics, extrinsics, settings)
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


# --- Robot mode (sim / live) -----------------------------------------------

@router.get("/robot/mode", response_model=RobotMode)
def robot_mode_get():
    return RobotMode(sim=is_sim_mode())


@router.post("/robot/mode", response_model=RobotMode)
def robot_mode_set(request: RobotModeRequest):
    set_sim_mode(request.sim)
    return RobotMode(sim=is_sim_mode())


@router.post("/execute", response_model=ExecuteResponse)
def execute(request: ExecuteRequest):
    """Re-plan from the current camera frame, translate the waypoints into the
    single-char robot protocol, and stream them over HC-05 Bluetooth.

    Re-planning (rather than accepting a pre-computed waypoint list from the
    client) means detection runs against a fresh frame right before motion,
    so stale poses from an earlier Plan click don't cause the robot to start
    from the wrong place.

    Blocks for the full motion duration — a typical 15-char plan takes
    20-25 s — and returns a per-command log when done.
    """
    intrinsics = _require_intrinsics()
    extrinsics = _require_extrinsics()
    settings = load_settings(Paths.settings)
    shelves = load_shelves(Paths.shelves)
    frame = _capture_frame()

    pose = _detect_robot_dispatch(frame, intrinsics, extrinsics, settings)
    if pose is None:
        raise HTTPException(
            status_code=422,
            detail={"error": "robot_not_detected"},
        )

    ws = settings.workspace
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

    sequence = plan_to_chars(waypoints, ws.cell_size_m)
    result = send_sequence(sequence, link_cfg=settings.robot_link)
    return ExecuteResponse(
        ok=result.ok,
        chars_sent=result.chars_sent,
        sequence=sequence,
        log=[
            ExecuteCommandLog(cmd=e.cmd, reply=e.reply, elapsed_ms=e.elapsed_ms)
            for e in result.log
        ],
        error=result.error,
    )


# --- Closed-loop execute (Server-Sent Events) ------------------------------
#
# The open-loop /execute endpoint above plans once and blasts the whole
# sequence. Closed-loop re-detects the pose after every single char so motor
# drift and approximate firmware timing self-correct instead of accumulating.
#
# One run at a time, guarded by a lock. The abort flag lets the UI stop a
# run mid-stream (POST /execute/abort).

_run_lock = threading.Lock()
_abort_event = threading.Event()


def _sse_event(name: str, payload: dict) -> bytes:
    """Format a single Server-Sent Event frame."""
    return f"event: {name}\ndata: {json.dumps(payload)}\n\n".encode("utf-8")


def _build_step_payload(
    step_idx: int,
    pose,
    next_cmd: str | None,
    sequence_so_far: str,
    annotated_b64: str,
) -> dict:
    return {
        "step_idx": step_idx,
        "pose": (
            None if pose is None
            else {"x_m": pose.x_m, "y_m": pose.y_m, "heading_deg": pose.heading_deg}
        ),
        "next_cmd": next_cmd,
        "sequence_so_far": sequence_so_far,
        "frame_b64": annotated_b64,
    }


@router.post("/execute/abort")
def execute_abort():
    """Signal the active /execute/stream run to stop after its current step.

    No-op if no run is in flight. The flag is auto-cleared at the start of
    the next run, so spurious aborts don't leak into the next button-press.
    """
    _abort_event.set()
    return {"ok": True, "running": _run_lock.locked()}


@router.post("/execute/stream")
def execute_stream(request: ExecuteStreamRequest):
    """Closed-loop execute: capture -> detect -> plan one char -> send -> repeat.

    Streams progress as Server-Sent Events. Event types:
      - step:                {step_idx, pose, next_cmd, sequence_so_far, frame_b64}
      - ack:                 {step_idx, cmd, reply, elapsed_ms, ok, error?}
      - done:                {sequence, steps, message}
      - aborted:             {sequence, steps}
      - stuck:               {sequence, steps, pose}
      - step_budget_exceeded:{sequence, steps, max_steps}
      - error:               {error, message?, sequence?, steps?}

    Re-planning every step is sub-millisecond on a 10x10 grid, so transient
    detection noise can't lock in a bad plan.
    """
    if _run_lock.locked():
        raise HTTPException(
            status_code=409,
            detail={"error": "execute_already_running"},
        )

    intrinsics = _require_intrinsics()
    extrinsics = _require_extrinsics()
    settings = load_settings(Paths.settings)
    cfg = settings.closed_loop
    ws = settings.workspace

    # Try the saved layout first. Only re-derive from the frame if the saved
    # shelves don't include the destination — that's the signal that the
    # saved state is stale or wrong for the current scene. Avoids stomping
    # on a manual `PUT /shelves` whenever someone executes.
    shelves = load_shelves(Paths.shelves)
    if not _has_shelf(shelves, request.destination_shelf_id):
        refreshed = _refresh_shelves_from_frame(intrinsics, extrinsics, settings)
        if refreshed:
            shelves = refreshed

    # Resolve the destination (and source for pick_place) early so a typo
    # errors out before streaming.
    try:
        dest_goal = goal_pose_for_shelf(shelves, request.destination_shelf_id)
    except KeyError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": "unknown_shelf", "message": str(e)},
        )

    is_pick_place = request.task == "pick_place"
    src_shelf_id: str | None = None
    src_goal = None
    src_shelf: Shelf | None = None
    dest_shelf: Shelf | None = None
    if is_pick_place:
        src_shelf_id = request.source_shelf_id
        if not src_shelf_id:
            raise HTTPException(
                status_code=400,
                detail={"error": "source_shelf_id_required"},
            )
        try:
            src_goal = goal_pose_for_shelf(shelves, src_shelf_id)
        except KeyError as e:
            raise HTTPException(
                status_code=404,
                detail={"error": "unknown_shelf", "message": str(e)},
            )
        src_shelf = next(s for s in shelves if s.id == src_shelf_id)
        dest_shelf = next(s for s in shelves if s.id == request.destination_shelf_id)

    link_cfg = settings.robot_link
    # Build a dedicated WifiLink for this run when needed. /execute/stream
    # calls grab_at / place_at on it for grab/place waypoints; bare drive
    # chars still go through send_sequence (which routes the same way).
    wifi_link = WifiLink(cfg=link_cfg) if link_cfg.type == "wifi" and not is_sim_mode() else None

    def gen():
        # Acquire here (not in the endpoint body) so the lock is released after
        # the generator finishes streaming, even if the client disconnects.
        if not _run_lock.acquire(blocking=False):
            yield _sse_event("error", {"error": "execute_already_running"})
            return
        _abort_event.clear()
        history = StepHistory.empty()
        sequence_so_far = ""
        step_idx = 0

        # Phase machine. For pick_place we navigate to source, run grab,
        # navigate to dest, run place, done. For navigate we just go to dest.
        phase = "to_source" if is_pick_place else "to_dest"

        try:
            while True:
                if _abort_event.is_set():
                    yield _sse_event("aborted", {
                        "sequence": sequence_so_far,
                        "steps": step_idx,
                    })
                    return

                if step_idx >= cfg.max_steps:
                    yield _sse_event("step_budget_exceeded", {
                        "sequence": sequence_so_far,
                        "steps": step_idx,
                        "max_steps": cfg.max_steps,
                    })
                    return

                # --- Perceive ---
                # fresh=True: closed-loop only works if each iteration sees
                # the post-action state, not a stale buffered frame.
                try:
                    frame = _camera.capture(fresh=True)
                except CameraError as e:
                    yield _sse_event("error", {
                        "error": "camera_unavailable",
                        "message": str(e),
                        "sequence": sequence_so_far,
                        "steps": step_idx,
                    })
                    return

                detected = _detect_robot_dispatch(frame, intrinsics, extrinsics, settings)
                if detected is None:
                    annotated = draw_overlay(
                        frame, shelves, robot_pose=None, waypoints=[],
                        intrinsics=intrinsics, extrinsics=extrinsics,
                        travel_height_m=settings.robot.travel_height_m,
                    )
                    yield _sse_event("error", {
                        "error": "robot_not_detected",
                        "frame_b64": _encode_image(annotated),
                        "sequence": sequence_so_far,
                        "steps": step_idx,
                    })
                    return

                pose = pose_from_detection(detected, ws.width_m, ws.height_m)

                # --- Decide ---
                # Pick the active goal/shelf based on the current phase.
                if phase == "to_source":
                    active_goal = src_goal
                    active_shelf_id = src_shelf_id
                    active_shelf = src_shelf
                else:
                    active_goal = dest_goal
                    active_shelf_id = request.destination_shelf_id
                    active_shelf = dest_shelf

                if at_goal(pose, active_goal, cfg):
                    annotated = draw_overlay(
                        frame, shelves, detected, waypoints=[],
                        intrinsics=intrinsics, extrinsics=extrinsics,
                        travel_height_m=settings.robot.travel_height_m,
                    )
                    yield _sse_event("step", _build_step_payload(
                        step_idx, pose, None, sequence_so_far, _encode_image(annotated),
                    ))

                    # Reached the active goal. For pick_place phases, run
                    # grab/place sequence and advance phase. For navigate
                    # task, we're done.
                    if not is_pick_place:
                        yield _sse_event("done", {
                            "sequence": sequence_so_far,
                            "steps": step_idx,
                            "message": f"arrived at {request.destination_shelf_id}",
                        })
                        return

                    if phase == "to_source":
                        action_label = "grab"
                        ack_subs = _run_manipulator_sequence(
                            wifi_link, link_cfg, action_label, active_shelf,
                        )
                    else:
                        action_label = "place"
                        ack_subs = _run_manipulator_sequence(
                            wifi_link, link_cfg, action_label, active_shelf,
                        )

                    for sub in ack_subs:
                        yield _sse_event("ack", {
                            "step_idx": step_idx,
                            "cmd": f"{action_label}:{sub.cmd}",
                            "reply": sub.reply,
                            "elapsed_ms": sub.elapsed_ms,
                            "ok": sub.ok,
                            **({"error": sub.error} if sub.error else {}),
                        })

                    if any(not sub.ok for sub in ack_subs):
                        first_err = next(sub for sub in ack_subs if not sub.ok)
                        yield _sse_event("error", {
                            "error": f"{action_label}_failed",
                            "message": first_err.error or f"{action_label} sequence failed at {first_err.cmd}",
                            "sequence": sequence_so_far,
                            "steps": step_idx,
                        })
                        return

                    sequence_so_far += action_label[0].upper()  # 'G' or 'P'

                    if phase == "to_source":
                        phase = "to_dest"
                        # Loop back to top — next iter will perceive and start
                        # planning toward the destination.
                        continue
                    else:
                        yield _sse_event("done", {
                            "sequence": sequence_so_far,
                            "steps": step_idx,
                            "message": (
                                f"picked from {src_shelf_id}, placed at "
                                f"{request.destination_shelf_id}"
                            ),
                        })
                        return

                try:
                    cmd = next_command(pose, active_shelf_id, shelves, settings)
                except (NoPathError, ApproachPointBlockedError) as e:
                    yield _sse_event("error", {
                        "error": "no_path",
                        "message": str(e),
                        "sequence": sequence_so_far,
                        "steps": step_idx,
                    })
                    return

                if cmd is None:
                    # Planner says we're done but at_goal disagreed — treat as done
                    # to avoid an infinite loop. Tolerance is the source of truth.
                    yield _sse_event("done", {
                        "sequence": sequence_so_far,
                        "steps": step_idx,
                        "message": "planner returned no waypoints",
                    })
                    return

                # Render before sending so the UI sees the pose+plan that
                # produced this command, not the one after it executed.
                annotated = draw_overlay(
                    frame, shelves, detected, waypoints=[],
                    intrinsics=intrinsics, extrinsics=extrinsics,
                    travel_height_m=settings.robot.travel_height_m,
                )
                yield _sse_event("step", _build_step_payload(
                    step_idx, pose, cmd, sequence_so_far, _encode_image(annotated),
                ))

                # --- Act ---
                result = send_sequence(cmd, link_cfg=link_cfg)
                ack_payload = {
                    "step_idx": step_idx,
                    "cmd": cmd,
                    "reply": result.log[0].reply if result.log else "",
                    "elapsed_ms": result.log[0].elapsed_ms if result.log else 0,
                    "ok": result.ok,
                }
                if result.error:
                    ack_payload["error"] = result.error
                yield _sse_event("ack", ack_payload)

                if not result.ok:
                    yield _sse_event("error", {
                        "error": "send_failed",
                        "message": result.error or "send_sequence reported failure",
                        "sequence": sequence_so_far + cmd,
                        "steps": step_idx + 1,
                    })
                    return

                sequence_so_far += cmd
                history.append(cmd, pose)
                step_idx += 1

                # --- Stuck check (after appending so the new sample is included) ---
                if is_stuck(history, cfg):
                    yield _sse_event("stuck", {
                        "sequence": sequence_so_far,
                        "steps": step_idx,
                        "pose": {
                            "x_m": pose.x_m, "y_m": pose.y_m,
                            "heading_deg": pose.heading_deg,
                        },
                    })
                    return
        finally:
            _abort_event.clear()
            _run_lock.release()

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # disables proxy buffering on nginx etc
    })


@router.post("/robot/send", response_model=ExecuteResponse)
def robot_send(request: RobotSendRequest):
    """Send one or more protocol chars directly to the robot, bypassing the
    planner. Used by the manual-control buttons in the web UI and by any
    low-level debugging / motor calibration flow.

    Drive chars (F/B/L/R/S) go through the WiFi link's drive composites.
    Multi-step grab/place sequences are not exposed via /robot/send — use
    /execute/stream for those. /robot/send is for low-level motor checks
    only.
    """
    sequence = request.sequence or ""
    settings = load_settings(Paths.settings)
    result = send_sequence(sequence, link_cfg=settings.robot_link)
    return ExecuteResponse(
        ok=result.ok,
        chars_sent=result.chars_sent,
        sequence=sequence,
        log=[
            ExecuteCommandLog(cmd=e.cmd, reply=e.reply, elapsed_ms=e.elapsed_ms)
            for e in result.log
        ],
        error=result.error,
    )


# --- Canned (no-vision) pick-place ----------------------------------------
#
# For physical bringup before ArUco markers are installed. The operator
# places the robot at a known starting pose (gripper-back facing the source
# shelf) and clicks "Run Planned". The backend dead-reckons the move using
# cell_drive_ms × cells from saved shelf coords. No planner, no vision, no
# closed loop. Drift is not corrected. Use only as a smoke test.

@router.post("/execute/canned", response_model=CannedExecuteResponse)
def execute_canned(request: CannedExecuteRequest):
    """Run a hardcoded pick-place sequence between two shelves.

    Sequence (gripper mounted on robot's back):
      1. grab_at(from.floor_distance_cm)  -- lift, slider out, close, slider in, lift to travel
      2. drive forward by Δy / cell_size cells  -- robot drives away from source toward dest
      3. place_at(to.floor_distance_cm)   -- lift, slider out, open, slider in, lift to travel

    The operator is responsible for the starting pose and orientation.
    """
    if _run_lock.locked():
        raise HTTPException(
            status_code=409,
            detail={"error": "execute_already_running"},
        )

    settings = load_settings(Paths.settings)
    if settings.robot_link.type == "sim":
        # Sim mode would silently "succeed" and do nothing physical, which is
        # misleading for a button labeled "Run Planned". Force the user to
        # flip robot_link.type=wifi before running real moves.
        raise HTTPException(
            status_code=400,
            detail={
                "error": "sim_mode",
                "message": "robot_link.type is 'sim' — set type=wifi in settings.yaml to run on real hardware.",
            },
        )

    shelves = load_shelves(Paths.shelves)
    src = next((s for s in shelves if s.id == request.from_shelf), None)
    dst = next((s for s in shelves if s.id == request.to_shelf), None)
    if src is None or dst is None:
        missing = [
            sid for sid, s in
            ((request.from_shelf, src), (request.to_shelf, dst)) if s is None
        ]
        raise HTTPException(
            status_code=404,
            detail={"error": "unknown_shelf", "message": f"unknown shelf id(s): {missing}"},
        )

    from vision.src.robot.wifi_link import WifiLink

    if not _run_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail={"error": "execute_already_running"},
        )

    steps: list[CannedExecuteStep] = []

    def push(label: str, ack) -> bool:
        steps.append(CannedExecuteStep(
            label=label, ok=ack.ok, elapsed_ms=ack.elapsed_ms,
            reply=ack.reply, error=ack.error,
        ))
        return ack.ok

    try:
        link = WifiLink(cfg=settings.robot_link)

        # 1. Grab from source. Closed-loop lift via the carriage's upward-facing
        #    ultrasonic — drive the lift until the sensor reports the target
        #    floor_distance_cm (5 cm = top, 15 cm = mid, 25 cm = bottom). Falls
        #    back to no-lift when floor_distance_cm is None (legacy / transit).
        for sub in link.grab_at(src.floor_distance_cm):
            if not push(f"grab:{sub.cmd}", sub):
                return CannedExecuteResponse(
                    ok=False, from_shelf=request.from_shelf, to_shelf=request.to_shelf,
                    steps=steps, error=f"grab failed at {sub.cmd}: {sub.error or sub.reply}",
                )

        # 2. Move from source shelf to destination shelf. Hardcoded 4-step
        #    sequence with timings tuned per workspace. Skipped entirely if
        #    the two shelves share the same approach point (different floors
        #    of the same physical shelf — robot doesn't need to move).
        rl = settings.robot_link
        same_column = (
            src.approach_point.x_m == dst.approach_point.x_m
            and src.approach_point.y_m == dst.approach_point.y_m
        )
        if not same_column:
            move_steps = [
                ("move:back", lambda: link.drive_backward(rl.move_back_after_grab_ms)),
                (
                    "move:turn1",
                    (
                        lambda: link.turn_left(rl.move_turn_ms)
                        if rl.move_turn_dir == "L"
                        else link.turn_right(rl.move_turn_ms)
                    ),
                ),
                ("move:forward", lambda: link.drive_forward(rl.move_forward_to_dest_ms)),
                (
                    "move:turn2",
                    (
                        lambda: link.turn_right(rl.move_turn_ms)
                        if rl.move_turn_dir == "L"
                        else link.turn_left(rl.move_turn_ms)
                    ),
                ),
            ]
            for label, action in move_steps:
                ack = action()
                if not push(label, ack):
                    return CannedExecuteResponse(
                        ok=False, from_shelf=request.from_shelf, to_shelf=request.to_shelf,
                        steps=steps,
                        error=f"{label} failed: {ack.error or ack.reply}",
                    )

        # 3. Place at destination — closed-loop lift to dst.floor_distance_cm.
        for sub in link.place_at(dst.floor_distance_cm):
            if not push(f"place:{sub.cmd}", sub):
                return CannedExecuteResponse(
                    ok=False, from_shelf=request.from_shelf, to_shelf=request.to_shelf,
                    steps=steps, error=f"place failed at {sub.cmd}: {sub.error or sub.reply}",
                )

        return CannedExecuteResponse(
            ok=True, from_shelf=request.from_shelf, to_shelf=request.to_shelf, steps=steps,
        )
    finally:
        _run_lock.release()


# --- Inventory: orders + state + auto-replenish ----------------------------
#
# Phase 1a — order queue and inventory bookkeeping. Phase 1b (the
# dispatcher that actually consumes orders and drives the robot) will be
# added once physical testing of the closed-loop is done so we know what
# failure handling needs to look like. Right now orders just sit on the
# queue waiting to be dispatched; manual /execute or /execute/stream
# remains the way to actually move the robot.

def _require_orders() -> OrderQueue:
    if _orders is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "orders_not_configured"},
        )
    return _orders


def _order_to_schema(o: Order) -> OrderSchema:
    return OrderSchema(
        id=o.id, sku_id=o.sku_id,
        source_shelf_id=o.source_shelf_id,
        destination_shelf_id=o.destination_shelf_id,
        qty=o.qty, status=o.status,
        created_at=o.created_at,
        started_at=o.started_at,
        finished_at=o.finished_at,
        error=o.error, reason=o.reason,
    )


def _proposal_to_schema(p: ReplenishProposal) -> ReplenishProposalSchema:
    return ReplenishProposalSchema(
        sku_id=p.sku_id,
        source_shelf_id=p.source_shelf_id,
        destination_shelf_id=p.destination_shelf_id,
        qty=p.qty, reason=p.reason,
    )


@router.get("/orders", response_model=OrdersListResponse)
def orders_list(status: str | None = None, limit: int = 100):
    """List orders, newest first. Optional `status` filter (one of
    pending/running/done/failed/cancelled)."""
    orders = _require_orders()
    if status is not None and status not in (
        "pending", "running", "done", "failed", "cancelled"
    ):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_status", "value": status},
        )
    items = orders.list_orders(status=status, limit=limit)
    return OrdersListResponse(orders=[_order_to_schema(o) for o in items])


@router.post("/orders", response_model=OrderSchema, status_code=201)
def orders_create(request: OrderCreateRequest):
    """Enqueue a new pick-and-place order. Validates that source and
    destination shelves exist before accepting."""
    orders = _require_orders()
    shelves = {s.id: s for s in load_shelves(Paths.shelves)}
    for shelf_id in (request.source_shelf_id, request.destination_shelf_id):
        if shelf_id not in shelves:
            raise HTTPException(
                status_code=404,
                detail={"error": "unknown_shelf", "shelf_id": shelf_id},
            )
    try:
        order = orders.enqueue(
            sku_id=request.sku_id,
            source_shelf_id=request.source_shelf_id,
            destination_shelf_id=request.destination_shelf_id,
            qty=request.qty,
            reason=request.reason,
        )
    except OrderQueueError as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_order", "message": str(e)})
    return _order_to_schema(order)


@router.get("/orders/{order_id}", response_model=OrderSchema)
def orders_get(order_id: int):
    orders = _require_orders()
    try:
        return _order_to_schema(orders.get(order_id))
    except OrderQueueError:
        raise HTTPException(status_code=404, detail={"error": "unknown_order", "id": order_id})


@router.delete("/orders/{order_id}", response_model=OrderSchema)
def orders_cancel(order_id: int):
    """Cancel a pending order. Returns 409 if it's already running/done."""
    orders = _require_orders()
    try:
        cancelled = orders.cancel(order_id)
    except OrderQueueError as e:
        msg = str(e)
        if "unknown" in msg:
            raise HTTPException(status_code=404, detail={"error": "unknown_order", "id": order_id})
        raise HTTPException(status_code=409, detail={"error": "cannot_cancel", "message": msg})
    return _order_to_schema(cancelled)


@router.get("/inventory", response_model=InventoryResponse)
def inventory_get():
    """Current per-shelf and per-SKU stock totals.

    Source of truth is shelves.json. The dispatcher (Phase 1b) will update
    the file after each successful place; for now you can edit shelves
    manually via the Layout Editor or PUT /shelves."""
    shelves = load_shelves(Paths.shelves)
    shelf_inv = [
        ShelfInventory(
            shelf_id=s.id, sku_id=s.sku_id,
            inventory_count=s.inventory_count, capacity=s.capacity,
        )
        for s in shelves
    ]
    by_sku: dict[str, dict] = {}
    for s in shelves:
        if s.sku_id is None:
            continue
        bucket = by_sku.setdefault(
            s.sku_id, {"total": 0, "capacity": 0, "shelves": []},
        )
        bucket["total"] += s.inventory_count
        bucket["capacity"] += s.capacity
        bucket["shelves"].append(s.id)
    skus = [
        SkuTotal(sku_id=k, total=v["total"], capacity=v["capacity"], shelves=v["shelves"])
        for k, v in sorted(by_sku.items())
    ]
    return InventoryResponse(shelves=shelf_inv, skus=skus)


@router.post("/replenish/preview", response_model=ReplenishPreviewResponse)
def replenish_preview(request: ReplenishRunRequest):
    """Dry-run the auto-replenish brain — returns what it *would* enqueue
    without actually creating orders. Useful for the dashboard's "preview"
    button so the user sees the plan before committing."""
    shelves = load_shelves(Paths.shelves)
    kwargs = {}
    if request.threshold_fraction is not None:
        kwargs["threshold_fraction"] = request.threshold_fraction
    try:
        proposals = replenish_plan(shelves, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_threshold", "message": str(e)})
    return ReplenishPreviewResponse(
        proposals=[_proposal_to_schema(p) for p in proposals],
    )


@router.post("/replenish/run", response_model=ReplenishRunResponse)
def replenish_run(request: ReplenishRunRequest):
    """Run the brain and enqueue its proposals. Skips proposals that
    would duplicate an already-pending order (same source/dest/SKU) so
    repeatedly clicking the button doesn't pile up identical orders."""
    orders = _require_orders()
    shelves = load_shelves(Paths.shelves)
    kwargs = {}
    if request.threshold_fraction is not None:
        kwargs["threshold_fraction"] = request.threshold_fraction
    try:
        proposals = replenish_plan(shelves, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": "invalid_threshold", "message": str(e)})

    pending = orders.list_orders(status="pending", limit=1000)
    pending_keys = {
        (o.sku_id, o.source_shelf_id, o.destination_shelf_id) for o in pending
    }

    enqueued: list[OrderSchema] = []
    skipped: list[ReplenishProposalSchema] = []
    for p in proposals:
        key = (p.sku_id, p.source_shelf_id, p.destination_shelf_id)
        if key in pending_keys:
            skipped.append(_proposal_to_schema(p))
            continue
        try:
            order = orders.enqueue(
                sku_id=p.sku_id,
                source_shelf_id=p.source_shelf_id,
                destination_shelf_id=p.destination_shelf_id,
                qty=p.qty,
                reason=p.reason,
            )
            enqueued.append(_order_to_schema(order))
            pending_keys.add(key)
        except OrderQueueError:
            skipped.append(_proposal_to_schema(p))

    return ReplenishRunResponse(enqueued=enqueued, skipped=skipped)


# --- Manual inventory edits + dispatcher -----------------------------------

@router.put("/inventory/shelf/{shelf_id}", response_model=ShelfInventory)
def inventory_update_shelf(shelf_id: str, request: ShelfInventoryUpdate):
    """Set the SKU + count on one shelf and persist to shelves.json.

    Used by the Inventory tab to mark slots filled/empty manually (demo /
    operator override). Clamps count to [0, capacity]."""
    shelves = load_shelves(Paths.shelves)
    target = next((s for s in shelves if s.id == shelf_id), None)
    if target is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "unknown_shelf", "shelf_id": shelf_id},
        )
    new_count = max(0, request.inventory_count)
    if target.capacity > 0:
        new_count = min(new_count, target.capacity)
    new_sku = request.sku_id if new_count > 0 else (target.sku_id if request.sku_id is None else request.sku_id)
    updated = [
        Shelf(
            id=s.id, x_m=s.x_m, y_m=s.y_m,
            width_m=s.width_m, length_m=s.length_m,
            rotation_deg=s.rotation_deg,
            approach_point=s.approach_point,
            sku_id=new_sku if s.id == shelf_id else s.sku_id,
            inventory_count=new_count if s.id == shelf_id else s.inventory_count,
            capacity=s.capacity,
            floor_distance_cm=s.floor_distance_cm,
            lift_up_ms=s.lift_up_ms,
            lift_down_ms=s.lift_down_ms,
        )
        for s in shelves
    ]
    save_shelves(updated, Paths.shelves)
    edited = next(s for s in updated if s.id == shelf_id)
    return ShelfInventory(
        shelf_id=edited.id, sku_id=edited.sku_id,
        inventory_count=edited.inventory_count, capacity=edited.capacity,
    )


def _adjust_shelf_count(shelf_id: str, delta: int) -> None:
    """Increment / decrement a shelf's inventory_count and persist. Clamps
    to [0, capacity]. Used after a successful dispatched pick-place."""
    shelves = load_shelves(Paths.shelves)
    updated: list[Shelf] = []
    for s in shelves:
        if s.id != shelf_id:
            updated.append(s)
            continue
        new_count = max(0, s.inventory_count + delta)
        if s.capacity > 0:
            new_count = min(new_count, s.capacity)
        updated.append(Shelf(
            id=s.id, x_m=s.x_m, y_m=s.y_m,
            width_m=s.width_m, length_m=s.length_m,
            rotation_deg=s.rotation_deg,
            approach_point=s.approach_point,
            sku_id=s.sku_id,
            inventory_count=new_count,
            capacity=s.capacity,
            floor_distance_cm=s.floor_distance_cm,
            lift_up_ms=s.lift_up_ms,
            lift_down_ms=s.lift_down_ms,
        ))
    save_shelves(updated, Paths.shelves)


@router.post("/orders/run-next", response_model=RunNextOrderResponse)
def orders_run_next():
    """Pop the oldest pending order, run it via canned-execute, update
    shelf inventory_count on success.

    Single-shot: one click = one order. If the order has qty>1 we still
    only run a single move and decrement qty by 1 (so repeated clicks chip
    away at it). Sim mode is rejected the same way /execute/canned is —
    the button is meant to drive real hardware."""
    orders = _require_orders()
    pending = orders.next_pending()
    if pending is None:
        return RunNextOrderResponse(ok=True, message="No pending orders.")

    # execute_canned validates lock + sim-mode itself, but we pre-check sim
    # so we don't mark the order running just to fail validation.
    settings = load_settings(Paths.settings)
    if settings.robot_link.type == "sim":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "sim_mode",
                "message": "robot_link.type is 'sim' — flip to wifi in settings.yaml first.",
            },
        )

    orders.update_status(pending.id, "running")
    try:
        executed = execute_canned(
            CannedExecuteRequest(
                from_shelf=pending.source_shelf_id,
                to_shelf=pending.destination_shelf_id,
            )
        )
    except HTTPException as e:
        orders.update_status(pending.id, "failed", error=str(e.detail))
        raise
    except Exception as e:
        orders.update_status(pending.id, "failed", error=f"{type(e).__name__}: {e}")
        raise

    if not executed.ok:
        final = orders.update_status(
            pending.id, "failed", error=executed.error or "canned_execute_failed",
        )
        return RunNextOrderResponse(
            ok=False, order=_order_to_schema(final), executed=executed,
            message=executed.error or "Robot move failed.",
        )

    # Move succeeded: bookkeeping. -1 from source, +1 to destination.
    _adjust_shelf_count(pending.source_shelf_id, -1)
    _adjust_shelf_count(pending.destination_shelf_id, +1)

    # If the order asked for more than 1 unit, leave a follow-up pending
    # order with qty-1 so a future click keeps moving units. Simpler than
    # mutating qty in place + re-pending.
    if pending.qty > 1:
        orders.enqueue(
            sku_id=pending.sku_id,
            source_shelf_id=pending.source_shelf_id,
            destination_shelf_id=pending.destination_shelf_id,
            qty=pending.qty - 1,
            reason=f"continuation of #{pending.id}",
        )
    final = orders.update_status(pending.id, "done")
    return RunNextOrderResponse(
        ok=True, order=_order_to_schema(final), executed=executed,
        message=f"Order #{pending.id} completed.",
    )


# --- Movement plans (named operator-built sequences) -----------------------
#
# Editor lives in the Calibration tab; the operator builds a plan as an
# ordered list of low-level steps (drive, lift, slider, gripper, wait) and
# saves it under a name. Plans are persisted in vision/state/movement_plans
# .json and run sequentially. Sim is allowed (uses FakeMovementLink).

from vision.src.robot.movement_plans import (  # noqa: E402
    MovementPlan, MovementStep, MovementPlansError,
    list_plans as mp_list, get_plan as mp_get,
    save_plan as mp_save, delete_plan as mp_delete,
    execute_plan as mp_execute, FakeMovementLink,
)


def _plan_to_schema(p: MovementPlan) -> MovementPlanSchema:
    return MovementPlanSchema(
        name=p.name,
        steps=[
            MovementStepSchema(
                type=s.type, duration_ms=s.duration_ms,
                target_cm=s.target_cm, note=s.note,
            )
            for s in p.steps
        ],
        note=p.note,
    )


def _schema_to_plan(s: MovementPlanSchema) -> MovementPlan:
    return MovementPlan(
        name=s.name,
        steps=[
            MovementStep(
                type=st.type, duration_ms=st.duration_ms,
                target_cm=st.target_cm, note=st.note,
            )
            for st in s.steps
        ],
        note=s.note,
    )


@router.get("/plans", response_model=MovementPlansListResponse)
def plans_list():
    """List all saved movement plans, sorted by name."""
    return MovementPlansListResponse(
        plans=[_plan_to_schema(p) for p in mp_list(Paths.movement_plans)],
    )


@router.put("/plans/{name}", response_model=MovementPlanSchema)
def plans_upsert(name: str, request: MovementPlanSchema):
    """Save a plan under `name`. The body's name field is ignored — the URL
    path is authoritative so the UI can rename without doing a delete + put."""
    plan = _schema_to_plan(MovementPlanSchema(
        name=name, steps=request.steps, note=request.note,
    ))
    try:
        mp_save(Paths.movement_plans, plan)
    except MovementPlansError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_plan", "message": str(e)},
        )
    return _plan_to_schema(plan)


@router.delete("/plans/{name}")
def plans_delete(name: str):
    try:
        mp_delete(Paths.movement_plans, name)
    except MovementPlansError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": "unknown_plan", "message": str(e)},
        )
    return {"ok": True}


@router.post("/plans/{name}/run", response_model=MovementPlanRunResponse)
def plans_run(name: str):
    """Execute a saved plan against the configured robot link.

    Sim is allowed: when robot_link.type is 'sim' (or _sim_override is True
    via /robot/mode) we run against an in-process FakeMovementLink that
    sleeps for realistic durations but doesn't touch hardware. Useful for
    rehearsing a plan before flipping to wifi.
    """
    if _run_lock.locked():
        raise HTTPException(
            status_code=409,
            detail={"error": "execute_already_running"},
        )
    try:
        plan = mp_get(Paths.movement_plans, name)
    except MovementPlansError:
        raise HTTPException(
            status_code=404,
            detail={"error": "unknown_plan", "name": name},
        )

    settings = load_settings(Paths.settings)
    sim = is_sim_mode() or settings.robot_link.type == "sim"
    if sim:
        link = FakeMovementLink()
    else:
        link = WifiLink(cfg=settings.robot_link)

    if not _run_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail={"error": "execute_already_running"},
        )

    steps_out: list[CannedExecuteStep] = []
    error: str | None = None
    ok = True
    try:
        for result in mp_execute(link, plan):
            steps_out.append(CannedExecuteStep(
                label=result.label, ok=result.ok,
                elapsed_ms=result.elapsed_ms, reply=result.reply,
                error=result.error,
            ))
            if not result.ok:
                ok = False
                error = result.error or f"{result.label} failed"
                break
    except MovementPlansError as e:
        ok = False
        error = str(e)
    finally:
        _run_lock.release()

    return MovementPlanRunResponse(
        ok=ok, plan_name=name, steps=steps_out, error=error, sim=sim,
    )
