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
