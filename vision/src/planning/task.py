"""Task-level planning: navigate and pick-and-place."""
from vision.src.models import (
    Settings, Shelf, Pose2D, Waypoint, GrabWaypoint, PlaceWaypoint,
)
from vision.src.planning.errors import NoPathError
from vision.src.planning.grid import (
    build_occupancy_grid, world_to_cell, snap_to_free_cell,
)
from vision.src.planning.astar import a_star
from vision.src.planning.motion import decompose_to_waypoints


def _find_shelf(shelves: list[Shelf], shelf_id: str) -> Shelf:
    for s in shelves:
        if s.id == shelf_id:
            return s
    raise KeyError(f"Shelf not found: {shelf_id}")


def plan_navigate_to(
    shelves: list[Shelf],
    target_shelf_id: str,
    current_pose: Pose2D,
    settings: Settings,
) -> list[Waypoint]:
    target = _find_shelf(shelves, target_shelf_id)
    grid = build_occupancy_grid(shelves, settings)

    start_cell = world_to_cell((current_pose.x_m, current_pose.y_m), settings)
    goal_cell = world_to_cell(
        (target.approach_point.x_m, target.approach_point.y_m), settings
    )

    # Snap the start to the nearest free cell if the detected pose lands
    # inside an inflated obstacle zone (happens with approximate calibration
    # or when the robot is physically right beside a shelf).
    snapped_start = snap_to_free_cell(grid, start_cell)
    if snapped_start is None:
        raise NoPathError(
            f"Start cell {start_cell} is blocked and no free cell is reachable nearby"
        )
    start_cell = snapped_start

    # 4-connected: the current robot can only do 90° in-place turns,
    # so diagonal grid steps would produce un-executable headings.
    cell_path = a_star(grid, start_cell, goal_cell, allow_diagonals=False)
    return decompose_to_waypoints(
        cell_path,
        start_heading_deg=current_pose.heading_deg,
        final_heading_deg=target.approach_point.heading_deg,
        settings=settings,
    )


def plan_pick_and_place(
    shelves: list[Shelf],
    source_id: str,
    destination_id: str,
    current_pose: Pose2D,
    settings: Settings,
) -> list[Waypoint]:
    src = _find_shelf(shelves, source_id)

    to_source = plan_navigate_to(shelves, source_id, current_pose, settings)
    pose_at_source = Pose2D(
        x_m=src.approach_point.x_m,
        y_m=src.approach_point.y_m,
        heading_deg=src.approach_point.heading_deg,
    )
    to_dest = plan_navigate_to(shelves, destination_id, pose_at_source, settings)

    return (
        to_source
        + [GrabWaypoint(shelf_id=source_id)]
        + to_dest
        + [PlaceWaypoint(shelf_id=destination_id)]
    )
