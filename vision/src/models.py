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
