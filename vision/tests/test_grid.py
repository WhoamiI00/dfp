"""Occupancy grid construction tests."""
import pytest
from vision.src.planning.grid import build_occupancy_grid, world_to_cell, cell_to_world
from vision.src.planning.errors import ApproachPointBlockedError
from vision.src.models import (
    Settings, WorkspaceConfig, RobotConfig, RobotMarkers, CameraConfig, PlannerConfig,
    Shelf, ApproachPoint,
)


def make_settings(cell_size=0.25, inflation=0.0):
    return Settings(
        workspace=WorkspaceConfig(width_m=2.5, height_m=2.5, cell_size_m=cell_size),
        robot=RobotConfig(
            footprint_m=(0.5, 0.5),
            travel_height_m=0.30,
            markers=RobotMarkers(front_color="red", back_color="green"),
        ),
        camera=CameraConfig(source=0, resolution=(1280, 720)),
        planner=PlannerConfig(obstacle_inflation_m=inflation),
    )


def test_empty_grid_no_shelves():
    settings = make_settings()
    grid = build_occupancy_grid([], settings)
    assert grid.shape == (10, 10)
    assert not grid.any()


def test_grid_marks_shelf_cells():
    settings = make_settings(cell_size=0.25, inflation=0.0)
    shelf = Shelf(
        id="s", x_m=0.5, y_m=0.5, width_m=0.5, length_m=0.5, rotation_deg=0,
        approach_point=ApproachPoint(x_m=1.0, y_m=0.5, heading_deg=180),
    )
    grid = build_occupancy_grid([shelf], settings)
    # Shelf center (0.5, 0.5) with 0.5x0.5 footprint should mark cells around (2,2).
    assert grid[2, 2] == 1
    assert grid[0, 0] == 0  # corner cell should be free


def test_grid_inflation_widens_obstacle():
    inflated = build_occupancy_grid(
        [Shelf(
            id="s", x_m=1.25, y_m=1.25, width_m=0.25, length_m=0.25, rotation_deg=0,
            approach_point=ApproachPoint(x_m=0.5, y_m=1.25, heading_deg=0),
        )],
        make_settings(cell_size=0.25, inflation=0.25),
    )
    # A 0.25x0.25 shelf at (1.25, 1.25) inflated by 0.25 should occupy the center
    # 3x3 block around cell (5, 5).
    assert inflated[5, 5] == 1
    assert inflated[4, 5] == 1
    assert inflated[5, 4] == 1


def test_grid_small_inflation_rounds_up_not_down():
    """0.10 m inflation at 0.25 m cells should ceil to 1 cell, not floor to 0."""
    inflated = build_occupancy_grid(
        [Shelf(
            id="s", x_m=1.25, y_m=1.25, width_m=0.25, length_m=0.25, rotation_deg=0,
            approach_point=ApproachPoint(x_m=0.5, y_m=1.25, heading_deg=0),
        )],
        make_settings(cell_size=0.25, inflation=0.10),
    )
    # The shelf cell is (5, 5) and must have at least one ring of inflation.
    assert inflated[5, 5] == 1
    assert inflated[4, 5] == 1 or inflated[6, 5] == 1


def test_grid_raises_on_blocked_approach_point():
    settings = make_settings(cell_size=0.25, inflation=0.25)
    shelf = Shelf(
        id="blocked", x_m=1.25, y_m=1.25, width_m=1.0, length_m=1.0, rotation_deg=0,
        approach_point=ApproachPoint(x_m=1.25, y_m=1.25, heading_deg=0),
    )
    with pytest.raises(ApproachPointBlockedError):
        build_occupancy_grid([shelf], settings)


def test_world_to_cell_and_back():
    settings = make_settings(cell_size=0.25)
    row, col = world_to_cell((1.125, 1.625), settings)
    assert (row, col) == (6, 4)
    x, y = cell_to_world((6, 4), settings)
    assert abs(x - 1.125) < 1e-9
    assert abs(y - 1.625) < 1e-9
