"""Closed-loop step controller.

Wraps the existing planner so the API layer can run a perceive->plan->act
loop one char at a time. After each robot command we re-detect the pose and
re-plan, so motor drift and approximate `CELL_FORWARD_MS` timing don't
accumulate the way they do in the open-loop /execute endpoint.
"""
from __future__ import annotations
import math
from dataclasses import dataclass

from vision.src.models import (
    ClosedLoopConfig, Pose2D, RobotPose, Settings, Shelf,
)
from vision.src.planning.errors import NoPathError, ApproachPointBlockedError
from vision.src.planning.task import plan_navigate_to
from vision.src.robot.protocol import plan_to_chars


def _normalize_deg(d: float) -> float:
    return ((d + 180.0) % 360.0) - 180.0


def heading_diff_deg(a: float, b: float) -> float:
    """Smallest absolute angle between two headings, in degrees."""
    return abs(_normalize_deg(a - b))


def at_goal(pose: Pose2D, goal: Pose2D, cfg: ClosedLoopConfig) -> bool:
    """True when both the position and the heading are within tolerance."""
    dx = pose.x_m - goal.x_m
    dy = pose.y_m - goal.y_m
    if math.hypot(dx, dy) > cfg.arrival_tolerance_m:
        return False
    if heading_diff_deg(pose.heading_deg, goal.heading_deg) > cfg.arrival_heading_tolerance_deg:
        return False
    return True


@dataclass
class StepHistory:
    """Records (cmd, pose) per step so is_stuck can spot stalled motion."""
    entries: list[tuple[str, Pose2D]]

    @classmethod
    def empty(cls) -> "StepHistory":
        return cls(entries=[])

    def append(self, cmd: str, pose: Pose2D) -> None:
        self.entries.append((cmd, pose))


def is_stuck(history: StepHistory, cfg: ClosedLoopConfig) -> bool:
    """True when the last `stuck_window_steps` F commands moved less than
    `stuck_position_threshold_m` total. Only F commands count — turns and
    grab/place are expected to move zero or near-zero distance.

    A stalled robot (dead motor, BT drop, wheels off the ground) is the
    most common failure mode and we want to abort rather than spin forever.
    """
    window = cfg.stuck_window_steps
    if window <= 0:
        return False
    forwards = [e for e in history.entries if e[0] == "F"]
    if len(forwards) < window + 1:
        return False  # not enough samples yet — give it a chance
    recent = forwards[-(window + 1):]  # need a baseline pose to diff against
    p0 = recent[0][1]
    pN = recent[-1][1]
    travelled = math.hypot(pN.x_m - p0.x_m, pN.y_m - p0.y_m)
    return travelled < cfg.stuck_position_threshold_m * window


def goal_pose_for_shelf(shelves: list[Shelf], shelf_id: str) -> Pose2D:
    """The destination pose for navigation: a shelf's approach point."""
    for s in shelves:
        if s.id == shelf_id:
            return Pose2D(
                x_m=s.approach_point.x_m,
                y_m=s.approach_point.y_m,
                heading_deg=s.approach_point.heading_deg,
            )
    raise KeyError(f"Shelf not found: {shelf_id}")


def next_command(
    current_pose: Pose2D,
    destination_shelf_id: str,
    shelves: list[Shelf],
    settings: Settings,
) -> str | None:
    """Plan from `current_pose` to the destination shelf and return the first
    protocol char to execute, or None if there's nothing to do.

    Replanning every step is cheap on a 10x10 grid (sub-millisecond A*) and
    means transient detection noise doesn't lock in a bad plan. Raises
    NoPathError / ApproachPointBlockedError to bubble back to the caller.
    """
    waypoints = plan_navigate_to(shelves, destination_shelf_id, current_pose, settings)
    if not waypoints:
        return None
    chars = plan_to_chars(waypoints, settings.workspace.cell_size_m)
    if not chars:
        # All waypoints decoded to empty strings (e.g. zero-degree turns).
        return None
    return chars[0]


def pose_from_detection(detected: RobotPose, ws_w: float, ws_h: float) -> Pose2D:
    """Clamp the detected pose to the workspace before feeding it to the planner.

    Mirrors the clamp in routes.py /plan so the controller and the one-shot
    plan endpoint behave the same way at workspace edges.
    """
    return Pose2D(
        x_m=min(max(detected.x_m, 0.0), ws_w),
        y_m=min(max(detected.y_m, 0.0), ws_h),
        heading_deg=detected.heading_deg,
    )


__all__ = [
    "at_goal",
    "heading_diff_deg",
    "is_stuck",
    "goal_pose_for_shelf",
    "next_command",
    "pose_from_detection",
    "StepHistory",
    "NoPathError",
    "ApproachPointBlockedError",
]
