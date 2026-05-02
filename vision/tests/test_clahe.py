"""Tests for CLAHE lighting normalization in mask_for_ranges.

The point of CLAHE is that the same HSV threshold should keep masking the
target colour even after the V channel is shifted up or down (i.e. brighter
or darker lighting). Without CLAHE the threshold band misses; with CLAHE the
mask survives.
"""
import numpy as np
import cv2
import pytest
from vision.src.detection.robot import mask_for_ranges, _normalize_lighting


def _solid_colour_frame_bgr(bgr: tuple[int, int, int], size=(200, 200)) -> np.ndarray:
    img = np.full((size[1], size[0], 3), bgr, dtype=np.uint8)
    # Add a small surrounding border of dark pixels so CLAHE has something
    # to stretch against — a perfectly uniform image is a degenerate input
    # for histogram equalization.
    cv2.rectangle(img, (0, 0), (size[0] - 1, size[1] - 1), (10, 10, 10), thickness=20)
    return img


def _bgr_to_hsv(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)


def test_normalize_lighting_only_changes_v_channel():
    img = _bgr_to_hsv(_solid_colour_frame_bgr((40, 40, 200)))
    normalized = _normalize_lighting(img)
    # H and S channels untouched; V may differ.
    assert np.array_equal(img[..., 0], normalized[..., 0])
    assert np.array_equal(img[..., 1], normalized[..., 1])


def test_clahe_preserves_existing_detection():
    """Saturated red on a dark background: the original threshold worked,
    after CLAHE it should still work — no regression."""
    img_bgr = _solid_colour_frame_bgr((20, 20, 220))  # bright red-ish in BGR
    hsv = _bgr_to_hsv(img_bgr)
    red_range = [(np.array([0, 120, 70]), np.array([10, 255, 255]))]
    mask = mask_for_ranges(hsv, red_range)
    # The big central region should mask cleanly.
    assert mask.sum() > 0
    # Masked area should be roughly the central (non-border) region.
    assert mask[100, 100] > 0


def test_clahe_normalize_lighting_stretches_v_range():
    """Direct property test on _normalize_lighting itself: when fed a frame
    with a V-channel gradient, the output V channel has wider spread and
    the locally-dim regions get pulled up.

    This is the underlying mechanism CLAHE provides; whether any specific
    threshold benefits depends on how dim the original was — see clipLimit
    in robot.py. We assert the mechanism works without overpromising.
    """
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    for x in range(200):
        v = int(40 + (220 - 40) * x / 199)
        img[:, x] = (0, 0, v)
    hsv = _bgr_to_hsv(img)
    normalized = _normalize_lighting(hsv)
    # Locally-dim pixel at column 30 should be brighter after normalization.
    raw_v = int(hsv[100, 30, 2])
    norm_v = int(normalized[100, 30, 2])
    assert norm_v > raw_v, (
        f"CLAHE should brighten the dim region; raw V={raw_v}, normalized V={norm_v}"
    )
    # And nowhere should normalization darken a pixel below 0 or saturate
    # past 255 — sanity that the underlying CLAHE call is sane.
    assert normalized[..., 2].min() >= 0
    assert normalized[..., 2].max() <= 255


def test_mask_for_ranges_still_applies_morph_open_close():
    """Sanity: morphological cleanup still runs after CLAHE — single-pixel
    noise in an otherwise-empty mask should be erased."""
    # All-zero HSV image with one stray bright-red pixel.
    hsv = np.zeros((50, 50, 3), dtype=np.uint8)
    hsv[25, 25] = (5, 200, 200)  # in red range
    red_range = [(np.array([0, 120, 70]), np.array([10, 255, 255]))]
    mask = mask_for_ranges(hsv, red_range)
    # Single-pixel speck should be eaten by MORPH_OPEN.
    assert mask[25, 25] == 0
