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


class SwitchableCamera(Camera):
    """Delegates to a fallback camera, but can be overridden with a still image
    at runtime. Lets the UI temporarily feed a local file instead of the live
    camera for testing."""

    def __init__(self, fallback: Camera):
        self._fallback = fallback
        self._override: np.ndarray | None = None

    def set_image(self, image: np.ndarray) -> None:
        self._override = image.copy()

    def clear_image(self) -> None:
        self._override = None

    @property
    def mode(self) -> str:
        return "test_image" if self._override is not None else "live"

    def capture(self) -> np.ndarray:
        if self._override is not None:
            return self._override.copy()
        return self._fallback.capture()
