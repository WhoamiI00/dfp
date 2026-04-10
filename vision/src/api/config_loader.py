"""Load and validate settings.yaml and shelves.json."""
from pathlib import Path
import json
import yaml
from vision.src.models import (
    Settings, WorkspaceConfig, RobotConfig, RobotMarkers, CameraConfig,
    PlannerConfig, Shelf, ApproachPoint,
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
            robot=RobotConfig(
                footprint_m=tuple(data["robot"]["footprint_m"]),
                travel_height_m=float(data["robot"]["travel_height_m"]),
                markers=RobotMarkers(
                    front_color=str(data["robot"]["markers"]["front_color"]),
                    back_color=str(data["robot"]["markers"]["back_color"]),
                ),
            ),
            camera=CameraConfig(
                source=data["camera"]["source"],
                resolution=tuple(data["camera"]["resolution"]),
            ),
            planner=PlannerConfig(
                obstacle_inflation_m=float(data["planner"]["obstacle_inflation_m"]),
            ),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise ConfigError(f"Malformed settings.yaml: {e}") from e


def load_shelves(path: Path) -> list[Shelf]:
    with path.open("r") as f:
        data = json.load(f)
    shelves = []
    for raw in data["shelves"]:
        try:
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
            ))
        except (KeyError, TypeError, ValueError) as e:
            raise ConfigError(f"Malformed shelf entry: {e}") from e
    return shelves


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
            }
            for s in shelves
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(data, f, indent=2)
