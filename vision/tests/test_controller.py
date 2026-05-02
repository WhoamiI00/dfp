"""Tests for the closed-loop controller helpers."""
import pytest
from vision.src.models import (
    ClosedLoopConfig, Pose2D, Shelf, ApproachPoint,
    Settings, WorkspaceConfig, RobotConfig, RobotMarkers, CameraConfig, PlannerConfig,
)
from vision.src.planning.controller import (
    at_goal, heading_diff_deg, is_stuck, goal_pose_for_shelf, next_command,
    StepHistory,
)


def _cfg(**kw) -> ClosedLoopConfig:
    base = ClosedLoopConfig()
    return ClosedLoopConfig(**{**base.__dict__, **kw})


def _settings(cell_m: float = 0.25) -> Settings:
    return Settings(
        workspace=WorkspaceConfig(width_m=2.5, height_m=2.5, cell_size_m=cell_m),
        robot=RobotConfig(
            footprint_m=(0.4, 0.4),
            travel_height_m=0.30,
            markers=RobotMarkers(front_color="red", back_color="green"),
        ),
        camera=CameraConfig(source=0, resolution=(1280, 720)),
        planner=PlannerConfig(obstacle_inflation_m=0.05),
        closed_loop=ClosedLoopConfig(),
    )


# --- at_goal ----------------------------------------------------------------

def test_at_goal_exact_match():
    g = Pose2D(1.0, 1.0, 90.0)
    assert at_goal(Pose2D(1.0, 1.0, 90.0), g, _cfg()) is True


def test_at_goal_just_inside_position_tolerance():
    g = Pose2D(1.0, 1.0, 90.0)
    cfg = _cfg(arrival_tolerance_m=0.25)
    inside = Pose2D(1.0 + 0.24, 1.0, 90.0)
    assert at_goal(inside, g, cfg) is True


def test_at_goal_just_outside_position_tolerance():
    g = Pose2D(1.0, 1.0, 90.0)
    cfg = _cfg(arrival_tolerance_m=0.25)
    outside = Pose2D(1.0 + 0.26, 1.0, 90.0)
    assert at_goal(outside, g, cfg) is False


def test_at_goal_heading_within_tolerance():
    g = Pose2D(1.0, 1.0, 90.0)
    cfg = _cfg(arrival_heading_tolerance_deg=30.0)
    assert at_goal(Pose2D(1.0, 1.0, 110.0), g, cfg) is True
    assert at_goal(Pose2D(1.0, 1.0, 130.0), g, cfg) is False


def test_heading_diff_wraps_correctly():
    # 350 vs 10 should be 20, not 340.
    assert heading_diff_deg(350, 10) == pytest.approx(20.0)
    # -170 vs 170 should be 20.
    assert heading_diff_deg(-170, 170) == pytest.approx(20.0)


def test_at_goal_heading_wrap_safe():
    # Goal heading 180, robot at -180 — same direction, should match.
    g = Pose2D(0.0, 0.0, 180.0)
    cfg = _cfg(arrival_heading_tolerance_deg=5.0)
    assert at_goal(Pose2D(0.0, 0.0, -180.0), g, cfg) is True


# --- is_stuck ---------------------------------------------------------------

def test_is_stuck_returns_false_with_few_samples():
    h = StepHistory.empty()
    h.append("F", Pose2D(0.0, 0.0, 0.0))
    h.append("F", Pose2D(0.0, 0.0, 0.0))
    # window=3 needs 4 F samples to even consider stuck.
    assert is_stuck(h, _cfg(stuck_window_steps=3)) is False


def test_is_stuck_when_no_progress_over_window():
    h = StepHistory.empty()
    for _ in range(5):
        h.append("F", Pose2D(0.0, 0.0, 0.0))
    cfg = _cfg(stuck_window_steps=3, stuck_position_threshold_m=0.05)
    assert is_stuck(h, cfg) is True


def test_is_stuck_false_when_robot_moving():
    h = StepHistory.empty()
    for i in range(5):
        h.append("F", Pose2D(0.25 * i, 0.0, 0.0))
    cfg = _cfg(stuck_window_steps=3, stuck_position_threshold_m=0.05)
    assert is_stuck(h, cfg) is False


def test_is_stuck_ignores_turn_commands():
    # All turns (no F) -> can't be stuck on forward motion.
    h = StepHistory.empty()
    for _ in range(10):
        h.append("L", Pose2D(0.0, 0.0, 0.0))
    cfg = _cfg(stuck_window_steps=3, stuck_position_threshold_m=0.05)
    assert is_stuck(h, cfg) is False


# --- goal_pose_for_shelf ----------------------------------------------------

def test_goal_pose_lookup_returns_approach_point():
    shelves = [
        Shelf(
            id="shelfA", x_m=1.0, y_m=2.0, width_m=0.4, length_m=0.3,
            rotation_deg=0.0,
            approach_point=ApproachPoint(x_m=1.0, y_m=1.5, heading_deg=90.0),
        )
    ]
    g = goal_pose_for_shelf(shelves, "shelfA")
    assert g.x_m == 1.0 and g.y_m == 1.5 and g.heading_deg == 90.0


def test_goal_pose_unknown_shelf_raises():
    with pytest.raises(KeyError):
        goal_pose_for_shelf([], "missing")


# --- next_command -----------------------------------------------------------

def test_next_command_returns_first_protocol_char():
    settings = _settings()
    shelves = [
        Shelf(
            id="A", x_m=2.25, y_m=2.0, width_m=0.3, length_m=0.3,
            rotation_deg=0.0,
            approach_point=ApproachPoint(x_m=1.25, y_m=2.0, heading_deg=0.0),
        )
    ]
    # Robot at (0.25, 2.0) heading 0 — needs to drive +X to reach (1.5, 2.0).
    pose = Pose2D(x_m=0.25, y_m=2.0, heading_deg=0.0)
    cmd = next_command(pose, "A", shelves, settings)
    # Already aligned (heading 0 = +X) and clear path -> first action is forward.
    assert cmd == "F"


def test_next_command_already_at_goal_returns_none():
    settings = _settings()
    shelves = [
        Shelf(
            id="A", x_m=2.25, y_m=2.0, width_m=0.3, length_m=0.3,
            rotation_deg=0.0,
            approach_point=ApproachPoint(x_m=1.25, y_m=2.0, heading_deg=0.0),
        )
    ]
    pose = Pose2D(x_m=1.25, y_m=2.0, heading_deg=0.0)
    cmd = next_command(pose, "A", shelves, settings)
    assert cmd is None
