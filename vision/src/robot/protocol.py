"""Translate planner waypoints into the single-char protocol understood by
firmware/plan_executor/plan_executor.ino.

With 4-connected A* (see planning/task.py) every TurnWaypoint is exactly
±90°/180° and every DriveWaypoint distance is an integer multiple of the
workspace cell size, so the translation is exact — no rounding error.
"""
from vision.src.models import (
    Waypoint, TurnWaypoint, DriveWaypoint, GrabWaypoint, PlaceWaypoint,
)


def normalize_deg(d: float) -> float:
    """Wrap an angle to (-180, 180]."""
    return ((d + 180.0) % 360.0) - 180.0


def waypoint_to_chars(wp: Waypoint, cell_size_m: float) -> str:
    if isinstance(wp, TurnWaypoint):
        delta = normalize_deg(wp.target_heading_deg - wp.from_pose.heading_deg)
        steps = round(abs(delta) / 90.0)
        if steps == 0:
            return ""
        return ("L" if delta > 0 else "R") * steps  # +CCW = left
    if isinstance(wp, DriveWaypoint):
        cells = round(wp.distance_m / cell_size_m)
        return "F" * max(cells, 0)
    if isinstance(wp, GrabWaypoint):
        return "G"
    if isinstance(wp, PlaceWaypoint):
        return "P"
    return ""  # ArriveWaypoint / unknown


def plan_to_chars(waypoints: list[Waypoint], cell_size_m: float) -> str:
    return "".join(waypoint_to_chars(w, cell_size_m) for w in waypoints)
