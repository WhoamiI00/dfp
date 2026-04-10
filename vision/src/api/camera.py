"""Camera abstraction: real (OpenCV) and fake (fixture image) implementations."""
from abc import ABC, abstractmethod
from pathlib import Path
import numpy as np
import cv2


class CameraError(Exception):
    pass


class Camera(ABC):
    @abstractmethod
    def capture(self) -> np.ndarray:
        """Return a single BGR frame."""


class OpenCVCamera(Camera):
    def __init__(self, source: int | str, resolution: tuple[int, int]):
        self._source = source
        self._resolution = resolution

    def capture(self) -> np.ndarray:
        cap = cv2.VideoCapture(self._source)
        if not cap.isOpened():
            raise CameraError(f"Failed to open camera source: {self._source}")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolution[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolution[1])
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise CameraError("Camera opened but failed to read frame")
        return frame


class FakeCamera(Camera):
    """Camera that always returns a fixed image. For tests."""

    def __init__(self, image: np.ndarray):
        self._image = image

    def capture(self) -> np.ndarray:
        return self._image.copy()

    @classmethod
    def from_file(cls, path: Path) -> "FakeCamera":
        img = cv2.imread(str(path))
        if img is None:
            raise CameraError(f"Failed to load fake camera image: {path}")
        return cls(img)
