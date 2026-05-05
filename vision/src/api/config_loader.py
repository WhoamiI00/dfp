"""Load and validate settings.yaml and shelves.json."""
from pathlib import Path
import json
import numpy as np
import yaml
from vision.src.detection.hsv_ranges import HsvRange
from vision.src.models import (
    Settings, WorkspaceConfig, RobotConfig, RobotMarkers, CameraConfig,
    PlannerConfig, ClosedLoopConfig, RobotLinkConfig, Shelf, ApproachPoint,
)


class ConfigError(Exception):
    pass


def load_settings(path: Path) -> Settings:
    with path.open("r") as f:
        data = yaml.safe_load(f)
    try:
        return Settings(
            workspace=WorkspaceConfig(
                width_m=float(data["workspace"]["width_m"]),
                height_m=float(data["workspace"]["height_m"]),
                cell_size_m=float(data["workspace"]["cell_size_m"]),
            ),
            robot=_parse_robot(data["robot"]),
            camera=CameraConfig(
                source=data["camera"]["source"],
                resolution=tuple(data["camera"]["resolution"]),
            ),
            planner=PlannerConfig(
                obstacle_inflation_m=float(data["planner"]["obstacle_inflation_m"]),
            ),
            closed_loop=_parse_closed_loop(data.get("closed_loop") or {}),
            robot_link=_parse_robot_link(data.get("robot_link") or {}),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise ConfigError(f"Malformed settings.yaml: {e}") from e


_VALID_DETECTORS = {"aruco", "hsv", "aruco_then_hsv"}


def _parse_robot(data: dict) -> RobotConfig:
    """Robot config; markers + detector are optional with safe defaults so
    older settings.yaml files keep loading without changes."""
    markers_data = data.get("markers", {})
    marker_defaults = RobotMarkers(front_color="red", back_color="green")
    markers = RobotMarkers(
        front_color=str(markers_data.get("front_color", marker_defaults.front_color)),
        back_color=str(markers_data.get("back_color", marker_defaults.back_color)),
        tag_id=int(markers_data.get("tag_id", marker_defaults.tag_id)),
        tag_size_m=float(markers_data.get("tag_size_m", marker_defaults.tag_size_m)),
    )
    detector = str(data.get("detector", "aruco_then_hsv")).strip().lower()
    if detector not in _VALID_DETECTORS:
        raise ConfigError(
            f"robot.detector must be one of {sorted(_VALID_DETECTORS)}, got {detector!r}"
        )
    return RobotConfig(
        footprint_m=tuple(data["footprint_m"]),
        travel_height_m=float(data["travel_height_m"]),
        markers=markers,
        detector=detector,
    )


def _parse_closed_loop(data: dict) -> ClosedLoopConfig:
    """Closed-loop section is optional; missing keys fall back to dataclass defaults."""
    defaults = ClosedLoopConfig()
    return ClosedLoopConfig(
        arrival_tolerance_m=float(data.get("arrival_tolerance_m", defaults.arrival_tolerance_m)),
        arrival_heading_tolerance_deg=float(
            data.get("arrival_heading_tolerance_deg", defaults.arrival_heading_tolerance_deg)
        ),
        max_steps=int(data.get("max_steps", defaults.max_steps)),
        stuck_position_threshold_m=float(
            data.get("stuck_position_threshold_m", defaults.stuck_position_threshold_m)
        ),
        stuck_window_steps=int(data.get("stuck_window_steps", defaults.stuck_window_steps)),
    )


_VALID_LINK_TYPES = {"wifi", "sim"}


def _parse_robot_link(data: dict) -> RobotLinkConfig:
    """robot_link section is optional; missing keys fall back to dataclass defaults."""
    defaults = RobotLinkConfig()
    link_type = str(data.get("type", defaults.type)).strip().lower()
    if link_type not in _VALID_LINK_TYPES:
        raise ConfigError(
            f"robot_link.type must be one of {sorted(_VALID_LINK_TYPES)}, got {link_type!r}"
        )
    return RobotLinkConfig(
        type=link_type,
        host=str(data.get("host", defaults.host)),
        port=int(data.get("port", defaults.port)),
        cell_drive_ms=int(data.get("cell_drive_ms", defaults.cell_drive_ms)),
        turn_90_ms=int(data.get("turn_90_ms", defaults.turn_90_ms)),
        slider_extend_ms=int(data.get("slider_extend_ms", defaults.slider_extend_ms)),
        slider_retract_ms=int(data.get("slider_retract_ms", defaults.slider_retract_ms)),
        gripper_settle_ms=int(data.get("gripper_settle_ms", defaults.gripper_settle_ms)),
        move_back_after_grab_ms=int(data.get("move_back_after_grab_ms", defaults.move_back_after_grab_ms)),
        move_turn_ms=int(data.get("move_turn_ms", defaults.move_turn_ms)),
        move_turn_dir=str(data.get("move_turn_dir", defaults.move_turn_dir)).strip().upper(),
        move_forward_to_dest_ms=int(data.get("move_forward_to_dest_ms", defaults.move_forward_to_dest_ms)),
        travel_distance_cm=float(data.get("travel_distance_cm", defaults.travel_distance_cm)),
        lift_tolerance_cm=float(data.get("lift_tolerance_cm", defaults.lift_tolerance_cm)),
        lift_stall_window_ms=int(data.get("lift_stall_window_ms", defaults.lift_stall_window_ms)),
        lift_min_progress_cm=float(data.get("lift_min_progress_cm", defaults.lift_min_progress_cm)),
        lift_max_runtime_ms=int(data.get("lift_max_runtime_ms", defaults.lift_max_runtime_ms)),
        request_timeout_s=float(data.get("request_timeout_s", defaults.request_timeout_s)),
    )


def load_shelves(path: Path) -> list[Shelf]:
    with path.open("r") as f:
        data = json.load(f)
    shelves = []
    for raw in data["shelves"]:
        try:
            sku_id_raw = raw.get("sku_id")
            shelves.append(Shelf(
                id=str(raw["id"]),
                x_m=float(raw["x_m"]),
                y_m=float(raw["y_m"]),
                width_m=float(raw["width_m"]),
                length_m=float(raw["length_m"]),
                rotation_deg=float(raw["rotation_deg"]),
                approach_point=ApproachPoint(
                    x_m=float(raw["approach_point"]["x_m"]),
                    y_m=float(raw["approach_point"]["y_m"]),
                    heading_deg=float(raw["approach_point"]["heading_deg"]),
                ),
                # Inventory fields are optional — older shelves.json files
                # without them keep loading; new fields default to "untracked".
                sku_id=str(sku_id_raw) if sku_id_raw is not None else None,
                inventory_count=int(raw.get("inventory_count", 0)),
                capacity=int(raw.get("capacity", 0)),
                floor_distance_cm=(
                    float(raw["floor_distance_cm"])
                    if raw.get("floor_distance_cm") is not None
                    else None
                ),
                lift_up_ms=int(raw.get("lift_up_ms", 0)),
                lift_down_ms=int(raw.get("lift_down_ms", 0)),
            ))
        except (KeyError, TypeError, ValueError) as e:
            raise ConfigError(f"Malformed shelf entry: {e}") from e
    return shelves


def load_custom_hsv(path: Path) -> dict[str, list[HsvRange]]:
    """Load user-saved HSV ranges from custom_hsv.yaml.

    Missing file -> empty dict. Each entry is a list of 6-tuples
    (H_min, S_min, V_min, H_max, S_max, V_max).
    """
    if not path.exists():
        return {}
    with path.open("r") as f:
        data = yaml.safe_load(f) or {}
    raw = data.get("ranges") or {}
    out: dict[str, list[HsvRange]] = {}
    for name, entries in raw.items():
        ranges: list[HsvRange] = []
        for entry in entries:
            if len(entry) != 6:
                raise ConfigError(
                    f"custom_hsv.yaml entry '{name}' must have 6 values, got {len(entry)}"
                )
            lo = np.array(entry[:3], dtype=np.uint8)
            hi = np.array(entry[3:], dtype=np.uint8)
            ranges.append((lo, hi))
        out[str(name).lower()] = ranges
    return out


def save_custom_hsv(custom: dict[str, list[HsvRange]], path: Path) -> None:
    data = {
        "ranges": {
            name: [
                [int(x) for x in list(lo) + list(hi)]
                for lo, hi in ranges
            ]
            for name, ranges in custom.items()
        }
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.safe_dump(data, f, sort_keys=True)


def save_shelves(shelves: list[Shelf], path: Path) -> None:
    data = {
        "shelves": [
            {
                "id": s.id,
                "x_m": s.x_m,
                "y_m": s.y_m,
                "width_m": s.width_m,
                "length_m": s.length_m,
                "rotation_deg": s.rotation_deg,
                "approach_point": {
                    "x_m": s.approach_point.x_m,
                    "y_m": s.approach_point.y_m,
                    "heading_deg": s.approach_point.heading_deg,
                },
                # Always write inventory fields (even if defaults) so the
                # JSON shape is uniform across shelves and the dashboard
                # doesn't have to special-case missing keys.
                "sku_id": s.sku_id,
                "inventory_count": s.inventory_count,
                "capacity": s.capacity,
                "floor_distance_cm": s.floor_distance_cm,
                "lift_up_ms": s.lift_up_ms,
                "lift_down_ms": s.lift_down_ms,
            }
            for s in shelves
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(data, f, indent=2)
