"""HSV color ranges for robot markers. Tune per lighting setup."""
import numpy as np

HsvRange = tuple[np.ndarray, np.ndarray]


# Red hue wraps around 0/180 in OpenCV's HSV, so use two ranges.
RED_HSV_RANGES: list[HsvRange] = [
    (np.array([0, 120, 70]), np.array([10, 255, 255])),
    (np.array([170, 120, 70]), np.array([180, 255, 255])),
]

GREEN_HSV_RANGES: list[HsvRange] = [
    (np.array([40, 80, 70]), np.array([80, 255, 255])),
]

# Pink / magenta sticky-note range. Covers hot pink (hue ~160-175) and
# salmon-pink / red-pink (hue ~0-12). Low-ish saturation floor to tolerate
# faded sticky notes under overhead lighting.
PINK_HSV_RANGES: list[HsvRange] = [
    (np.array([0, 60, 120]), np.array([12, 220, 255])),
    (np.array([140, 60, 120]), np.array([180, 255, 255])),
]

# Sticky-note blue. Covers standard blue and lighter cyan-blue. Low
# saturation floor so pastel/faded blues still mask.
BLUE_HSV_RANGES: list[HsvRange] = [
    (np.array([85, 60, 60]), np.array([135, 255, 255])),
]

YELLOW_HSV_RANGES: list[HsvRange] = [
    (np.array([20, 100, 100]), np.array([35, 255, 255])),
]


NAMED_HSV_RANGES: dict[str, list[HsvRange]] = {
    "red": RED_HSV_RANGES,
    "green": GREEN_HSV_RANGES,
    "pink": PINK_HSV_RANGES,
    "magenta": PINK_HSV_RANGES,
    "blue": BLUE_HSV_RANGES,
    "yellow": YELLOW_HSV_RANGES,
}


def get_ranges(color_name: str) -> list[HsvRange]:
    key = color_name.strip().lower()
    if key not in NAMED_HSV_RANGES:
        raise ValueError(
            f"Unknown marker color '{color_name}'. "
            f"Available: {sorted(NAMED_HSV_RANGES.keys())}"
        )
    return NAMED_HSV_RANGES[key]


MIN_MARKER_AREA_PX = 200
