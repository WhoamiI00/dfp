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
    # Inventory bookkeeping (optional). When omitted by older clients
    # (e.g. the Layout Editor that doesn't know about SKUs yet), the
    # PUT round-trip preserves None / 0 — same as a freshly auto-detected
    # shelf has.
    sku_id: str | None = None
    inventory_count: int = 0
    capacity: int = 0


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


class ManualExtrinsicRequest(BaseModel):
    # Four (u, v) pixel coordinates of the workspace corners, in this order:
    # (0, 0), (width, 0), (width, height), (0, height).
    corner_pixels: list[tuple[float, float]]


# --- Camera mode ------------------------------------------------------------

class CameraMode(BaseModel):
    mode: Literal["live", "test_image"]


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


class DetectDebugResponse(BaseModel):
    front_color_name: str
    back_color_name: str
    min_marker_area_px: int
    front_largest_area_px: int
    back_largest_area_px: int
    front_centroid_px: tuple[float, float] | None
    back_centroid_px: tuple[float, float] | None
    mask_overlay_base64: str


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


# --- Execute (stream plan over Bluetooth) -----------------------------------

class ExecuteRequest(BaseModel):
    task: Literal["navigate", "pick_place"]
    source_shelf_id: str | None = None
    destination_shelf_id: str
    port: str | None = None   # e.g. "COM6"; defaults to ROBOT_PORT env / COM6
    baud: int | None = None   # defaults to ROBOT_BAUD env / 9600


class ExecuteCommandLog(BaseModel):
    cmd: str
    reply: str
    elapsed_ms: int


class ExecuteResponse(BaseModel):
    ok: bool
    chars_sent: int
    sequence: str
    log: list[ExecuteCommandLog]
    error: str | None = None


class RobotSendRequest(BaseModel):
    sequence: str            # one or more protocol chars, e.g. "F" or "FFLR"
    port: str | None = None
    baud: int | None = None


# --- Layout auto-detect -----------------------------------------------------

class AutoDetectShelvesRequest(BaseModel):
    marker_color: str = "yellow"
    max_count: int = 3
    id_prefix: str = "shelf_"
    approach_offset_m: float = 0.75
    shelf_width_m: float = 0.4
    shelf_length_m: float = 0.3
    persist: bool = True


class AutoDetectedShelf(BaseModel):
    id: str
    pixel_cx: float
    pixel_cy: float
    pixel_area: int
    world_x_m: float
    world_y_m: float


class AutoDetectShelvesResponse(BaseModel):
    shelves: list[AutoDetectedShelf]
    annotated_image_base64: str
    persisted: bool


# --- HSV color picker / custom ranges --------------------------------------

class HsvSampleRequest(BaseModel):
    pixel_u: int
    pixel_v: int
    patch_size: int = 5


class HsvBand(BaseModel):
    h_min: int
    s_min: int
    v_min: int
    h_max: int
    s_max: int
    v_max: int


class HsvSampleResponse(BaseModel):
    median_h: int
    median_s: int
    median_v: int
    bands: list[HsvBand]


class CustomHsvUpsertRequest(BaseModel):
    bands: list[HsvBand]


class CustomHsvEntry(BaseModel):
    name: str
    bands: list[HsvBand]


class CustomHsvListResponse(BaseModel):
    entries: list[CustomHsvEntry]


# --- Robot mode (sim / live) -----------------------------------------------

class RobotMode(BaseModel):
    sim: bool


class RobotModeRequest(BaseModel):
    sim: bool


# --- Closed-loop execute ----------------------------------------------------

class ExecuteStreamRequest(BaseModel):
    task: Literal["navigate", "pick_place"]
    source_shelf_id: str | None = None
    destination_shelf_id: str
    port: str | None = None
    baud: int | None = None


# --- Inventory orders -------------------------------------------------------

class OrderSchema(BaseModel):
    id: int
    sku_id: str
    source_shelf_id: str
    destination_shelf_id: str
    qty: int
    status: Literal["pending", "running", "done", "failed", "cancelled"]
    created_at: float
    started_at: float | None = None
    finished_at: float | None = None
    error: str | None = None
    reason: str = ""


class OrderCreateRequest(BaseModel):
    sku_id: str
    source_shelf_id: str
    destination_shelf_id: str
    qty: int = 1
    reason: str = ""


class OrdersListResponse(BaseModel):
    orders: list[OrderSchema]


# --- Inventory state --------------------------------------------------------

class ShelfInventory(BaseModel):
    shelf_id: str
    sku_id: str | None
    inventory_count: int
    capacity: int


class SkuTotal(BaseModel):
    sku_id: str
    total: int
    capacity: int
    shelves: list[str]


class InventoryResponse(BaseModel):
    shelves: list[ShelfInventory]
    skus: list[SkuTotal]


# --- Auto-replenish ---------------------------------------------------------

class ReplenishProposalSchema(BaseModel):
    sku_id: str
    source_shelf_id: str
    destination_shelf_id: str
    qty: int
    reason: str


class ReplenishPreviewResponse(BaseModel):
    proposals: list[ReplenishProposalSchema]


class ReplenishRunRequest(BaseModel):
    threshold_fraction: float | None = None  # default in replenish.py


class ReplenishRunResponse(BaseModel):
    enqueued: list[OrderSchema]
    skipped: list[ReplenishProposalSchema]  # proposed but not enqueued (e.g. duplicate)


# --- Errors -----------------------------------------------------------------

class ErrorResponse(BaseModel):
    error: str
    details: dict | None = None
