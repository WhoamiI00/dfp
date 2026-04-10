"""Pick-and-place task composition tests."""
from vision.src.planning.task import plan_navigate_to, plan_pick_and_place
from vision.src.models import (
    Shelf, ApproachPoint, Pose2D, GrabWaypoint, PlaceWaypoint, DriveWaypoint,
)
from vision.tests.test_grid import make_settings


def _shelves():
    return [
        Shelf(
            id="shelf_A", x_m=0.5, y_m=1.25, width_m=0.5, length_m=0.5, rotation_deg=0,
            approach_point=ApproachPoint(x_m=1.125, y_m=1.25, heading_deg=180),
        ),
        Shelf(
            id="shelf_B", x_m=2.0, y_m=1.25, width_m=0.5, length_m=0.5, rotation_deg=0,
            approach_point=ApproachPoint(x_m=1.375, y_m=1.25, heading_deg=0),
        ),
    ]


def test_navigate_produces_waypoints():
    settings = make_settings(inflation=0.0)
    current = Pose2D(x_m=0.125, y_m=0.125, heading_deg=0)
    waypoints = plan_navigate_to(_shelves(), "shelf_A", current, settings)
    assert len(waypoints) > 0
    assert any(isinstance(w, DriveWaypoint) for w in waypoints)


def test_pick_and_place_stitches_grab_and_place():
    settings = make_settings(inflation=0.0)
    current = Pose2D(x_m=0.125, y_m=0.125, heading_deg=0)
    waypoints = plan_pick_and_place(_shelves(), "shelf_A", "shelf_B", current, settings)

    grabs = [w for w in waypoints if isinstance(w, GrabWaypoint)]
    places = [w for w in waypoints if isinstance(w, PlaceWaypoint)]
    assert len(grabs) == 1
    assert grabs[0].shelf_id == "shelf_A"
    assert len(places) == 1
    assert places[0].shelf_id == "shelf_B"

    grab_index = waypoints.index(grabs[0])
    place_index = waypoints.index(places[0])
    assert grab_index < place_index
