"""HSV color ranges for robot markers. Tune these per lighting setup."""
import numpy as np


# Red hue wraps around 0/180 in OpenCV's HSV, so use two ranges.
RED_HSV_RANGES = [
    (np.array([0, 120, 70]), np.array([10, 255, 255])),
    (np.array([170, 120, 70]), np.array([180, 255, 255])),
]

GREEN_HSV_RANGES = [
    (np.array([40, 80, 70]), np.array([80, 255, 255])),
]

MIN_MARKER_AREA_PX = 200
