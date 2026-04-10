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
