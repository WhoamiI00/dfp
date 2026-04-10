"""HSV color ranges for robot markers. Tune per lighting setup."""
import cv2
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
    (np.array([15, 50, 180]), np.array([35, 255, 255])),
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


# --- HSV sampling -----------------------------------------------------------

# Tolerance added on each side of the median HSV value when building a
# range from a sampled patch. Broader than the patch's own min/max so the
# resulting range survives small lighting/shadow variation across the scene.
_H_TOLERANCE = 8
_S_TOLERANCE = 40
_V_TOLERANCE = 40

# How close to the hue axis (0 / 180) a sampled red counts as "near-wrap"
# — in that case we emit two ranges so both sides of the hue wheel are
# covered, matching the style of RED_HSV_RANGES above.
_HUE_WRAP_MARGIN = _H_TOLERANCE + 2


def sample_hsv_range_from_pixel(
    frame_bgr: np.ndarray,
    pixel_uv: tuple[int, int],
    patch_size: int = 5,
) -> tuple[list[HsvRange], tuple[int, int, int]]:
    """Sample a small neighbourhood around `pixel_uv` in `frame_bgr` and
    build an HSV range that covers the marker colour with tolerance.

    Returns `(ranges, median_hsv)` where `ranges` is the list of
    (lo, hi) tuples suitable for `mask_for_ranges` / `get_ranges`, and
    `median_hsv` is the sampled centre colour in OpenCV HSV
    (H: 0-179, S: 0-255, V: 0-255). Emits two hue-split ranges when the
    sample lies near the 0/180 wrap boundary so reds work out of the box.
    """
    h, w = frame_bgr.shape[:2]
    u, v = int(pixel_uv[0]), int(pixel_uv[1])
    if not (0 <= u < w and 0 <= v < h):
        raise ValueError(
            f"Pixel ({u}, {v}) is outside frame of size {w}x{h}"
        )
    half = max(0, patch_size // 2)
    u0, u1 = max(0, u - half), min(w, u + half + 1)
    v0, v1 = max(0, v - half), min(h, v + half + 1)

    patch = frame_bgr[v0:v1, u0:u1]
    hsv_patch = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    # Median across the patch is robust to a one-pixel misclick on an edge.
    med = np.median(hsv_patch.reshape(-1, 3), axis=0)
    h_med, s_med, v_med = int(round(med[0])), int(round(med[1])), int(round(med[2]))

    s_lo = max(0, s_med - _S_TOLERANCE)
    s_hi = min(255, s_med + _S_TOLERANCE)
    v_lo = max(0, v_med - _V_TOLERANCE)
    v_hi = min(255, v_med + _V_TOLERANCE)

    ranges: list[HsvRange] = []
    if h_med < _HUE_WRAP_MARGIN or h_med > (180 - _HUE_WRAP_MARGIN):
        # Near red wrap — emit two ranges bracketing the hue wheel.
        low_hi = min(179, (h_med + _H_TOLERANCE) % 180 + (180 if h_med > 90 else 0))
        # Easier: just hand-build both halves.
        ranges.append((
            np.array([0, s_lo, v_lo], dtype=np.uint8),
            np.array([_H_TOLERANCE, s_hi, v_hi], dtype=np.uint8),
        ))
        ranges.append((
            np.array([180 - _H_TOLERANCE, s_lo, v_lo], dtype=np.uint8),
            np.array([179, s_hi, v_hi], dtype=np.uint8),
        ))
    else:
        h_lo = max(0, h_med - _H_TOLERANCE)
        h_hi = min(179, h_med + _H_TOLERANCE)
        ranges.append((
            np.array([h_lo, s_lo, v_lo], dtype=np.uint8),
            np.array([h_hi, s_hi, v_hi], dtype=np.uint8),
        ))
    return ranges, (h_med, s_med, v_med)
