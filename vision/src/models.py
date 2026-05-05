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
    # ArUco config — used when detector mode is "aruco" or "aruco_then_hsv".
    # tag_id 4 reserved for the robot (extrinsic calibration uses 0-3).
    tag_id: int = 4
    tag_size_m: float = 0.05  # 50 mm — fits a small robot, prints on A4


@dataclass(frozen=True)
class RobotConfig:
    footprint_m: tuple[float, float]
    travel_height_m: float
    markers: RobotMarkers
    # "aruco" -> ArUco only, fail if missing.
    # "hsv"   -> HSV only (the original behaviour).
    # "aruco_then_hsv" -> try ArUco first, fall back to HSV. Default — most
    #   robust to gradual sticker/tag transitions during dev.
    detector: str = "aruco_then_hsv"


@dataclass(frozen=True)
class CameraConfig:
    source: int | str
    resolution: tuple[int, int]


@dataclass(frozen=True)
class PlannerConfig:
    obstacle_inflation_m: float


@dataclass(frozen=True)
class ClosedLoopConfig:
    arrival_tolerance_m: float = 0.25
    arrival_heading_tolerance_deg: float = 30.0
    max_steps: int = 50
    stuck_position_threshold_m: float = 0.05
    stuck_window_steps: int = 3


@dataclass(frozen=True)
class RobotLinkConfig:
    """How the backend talks to the physical robot.

    type:
        wifi -> HTTP to ESP32 (default for new builds)
        sim  -> in-process fake link, no hardware needed
    """
    type: str = "wifi"
    host: str = "10.82.225.95"
    port: int = 80
    # Drive timing (motor pulses with no encoder feedback). Tuned empirically
    # against the cell size in workspace.cell_size_m. The closed-loop
    # controller compensates for drift via vision so these only need to be
    # close, not exact.
    cell_drive_ms: int = 800
    turn_90_ms: int = 600
    # Manipulator timing.
    slider_extend_ms: int = 1500
    slider_retract_ms: int = 1500
    gripper_settle_ms: int = 400
    # Move-between-shelves sequence (canned-execute, dead-reckoning).
    # After grabbing from source shelf, the robot needs to physically reach
    # the destination shelf. With no vision, we run a hardcoded 4-step
    # sequence and tune the timings empirically:
    #
    #   1. backward `move_back_after_grab_ms`  -- clear the source shelf
    #   2. turn `move_turn_dir` for `move_turn_ms`  -- face new direction
    #   3. forward `move_forward_to_dest_ms` -- approach destination
    #   4. turn opposite direction for `move_turn_ms`  -- align with shelf
    #
    # Each timing is a per-pair guess; tune by running once and watching
    # where the robot ends up.
    move_back_after_grab_ms: int = 1500
    move_turn_ms: int = 1000               # for ~90° turn
    move_turn_dir: str = "L"               # "L" or "R" for the first turn
    move_forward_to_dest_ms: int = 3000
    # Lift control. The ultrasonic on the carriage points up at the mast top.
    # Smaller distance = higher floor. travel_distance_cm is the rest position
    # (also doubles as the bottom-floor target).
    travel_distance_cm: float = 25.0
    lift_tolerance_cm: float = 2.0
    # Lift runs as long as the carriage is making progress. We check every
    # lift_stall_window_ms whether the sensor reading changed by at least
    # lift_min_progress_cm. If yes, keep going. If no (motor stalled, hit a
    # stop, sensor stuck), abort. lift_max_runtime_ms is a hard upper bound
    # that should only fire if both the stall check and the target check
    # somehow miss — generous so a slow real lift isn't a problem.
    lift_stall_window_ms: int = 1500
    lift_min_progress_cm: float = 0.5
    lift_max_runtime_ms: int = 30000
    # HTTP request timeout for /cmd and /distance.
    request_timeout_s: float = 1.5


@dataclass(frozen=True)
class Settings:
    workspace: WorkspaceConfig
    robot: RobotConfig
    camera: CameraConfig
    planner: PlannerConfig
    closed_loop: ClosedLoopConfig = field(default_factory=ClosedLoopConfig)
    robot_link: RobotLinkConfig = field(default_factory=RobotLinkConfig)


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
    # Inventory bookkeeping. Optional with safe defaults so existing
    # shelves.json files without SKU fields keep loading. A shelf with
    # sku_id=None is treated as a "transit" shelf — pickable but not
    # tracked by the auto-replenish brain.
    sku_id: str | None = None
    inventory_count: int = 0
    capacity: int = 0
    # Lift target as read by the upward-facing ultrasonic on the carriage.
    # Smaller cm = higher floor (carriage closer to mast top). None = single-
    # floor shelf, no lift step required (legacy + transit shelves).
    floor_distance_cm: float | None = None
    # Open-loop alternative: timed lift pulses, no sensor feedback. Operator
    # measures travel time per floor with the Manual UP button and bakes them
    # in. Canned-execute uses these. Both 0 for the bottom (rest) floor.
    lift_up_ms: int = 0
    lift_down_ms: int = 0


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


# --- Inventory orders -------------------------------------------------------

OrderStatus = Literal["pending", "running", "done", "failed", "cancelled"]


@dataclass(frozen=True)
class Order:
    """One pick-and-place order for the dispatcher.

    The dispatcher (added in a later phase) pulls pending orders FIFO,
    moves the robot to source -> grab -> dest -> place once per qty unit,
    and updates source/dest shelf inventory_count after each successful
    place. Orders are persisted in sqlite so a dispatcher crash doesn't
    lose pending work.
    """
    id: int                # auto-assigned by the queue
    sku_id: str
    source_shelf_id: str
    destination_shelf_id: str
    qty: int               # how many units to move; dispatcher loops
    status: OrderStatus
    created_at: float      # unix timestamp
    started_at: float | None = None
    finished_at: float | None = None
    error: str | None = None
    reason: str = ""       # e.g. "auto_replenish: shelfA below threshold"
