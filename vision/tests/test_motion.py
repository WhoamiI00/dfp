"""Non-holonomic motion decomposition tests."""
from vision.src.planning.motion import decompose_to_waypoints
from vision.src.models import TurnWaypoint, DriveWaypoint
from vision.tests.test_grid import make_settings


def test_straight_line_single_drive():
    settings = make_settings(cell_size=0.25)
    cell_path = [(0, 0), (0, 1), (0, 2), (0, 3)]
    waypoints = decompose_to_waypoints(
        cell_path, start_heading_deg=0.0, final_heading_deg=0.0, settings=settings,
    )
    # Expect: no initial turn (already facing right), one drive, no final turn.
    drives = [w for w in waypoints if isinstance(w, DriveWaypoint)]
    turns = [w for w in waypoints if isinstance(w, TurnWaypoint)]
    assert len(drives) == 1
    assert abs(drives[0].distance_m - 0.75) < 1e-6  # 3 cells * 0.25 m
    assert len(turns) == 0


def test_right_angle_one_turn_two_drives():
    settings = make_settings(cell_size=0.25)
    cell_path = [(0, 0), (0, 1), (0, 2), (1, 2), (2, 2)]
    waypoints = decompose_to_waypoints(
        cell_path, start_heading_deg=0.0, final_heading_deg=90.0, settings=settings,
    )
    drives = [w for w in waypoints if isinstance(w, DriveWaypoint)]
    turns = [w for w in waypoints if isinstance(w, TurnWaypoint)]
    assert len(drives) == 2
    assert len(turns) == 1
    assert abs(turns[0].target_heading_deg - 90.0) < 1e-6


def test_initial_turn_when_starting_heading_wrong():
    settings = make_settings(cell_size=0.25)
    cell_path = [(0, 0), (0, 1), (0, 2)]
    waypoints = decompose_to_waypoints(
        cell_path, start_heading_deg=180.0, final_heading_deg=0.0, settings=settings,
    )
    turns = [w for w in waypoints if isinstance(w, TurnWaypoint)]
    drives = [w for w in waypoints if isinstance(w, DriveWaypoint)]
    # Expect: initial turn from 180 to 0, one drive, no final turn (already at 0)
    assert len(turns) == 1
    assert len(drives) == 1


def test_final_turn_to_match_approach_heading():
    settings = make_settings(cell_size=0.25)
    cell_path = [(0, 0), (0, 1)]
    waypoints = decompose_to_waypoints(
        cell_path, start_heading_deg=0.0, final_heading_deg=270.0, settings=settings,
    )
    turns = [w for w in waypoints if isinstance(w, TurnWaypoint)]
    drives = [w for w in waypoints if isinstance(w, DriveWaypoint)]
    # Expect: no initial turn, one drive, one final turn to 270.
    assert len(drives) == 1
    assert len(turns) == 1
    assert abs(turns[0].target_heading_deg - 270.0) < 1e-6


def test_single_cell_path_no_drive():
    settings = make_settings(cell_size=0.25)
    waypoints = decompose_to_waypoints(
        [(3, 3)], start_heading_deg=45.0, final_heading_deg=45.0, settings=settings,
    )
    # No movement, no turns.
    assert waypoints == []
