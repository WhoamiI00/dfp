"""Camera abstraction: real (OpenCV) and fake (fixture image) implementations.

The real camera supports both local USB webcams (`source: 0`) and network
streams like Android IP Webcam (`source: "http://192.168.137.19:8080/video"`).
For network streams the capture handle is kept open across captures and the
internal buffer is drained before each read so /detect always sees a fresh
frame, not a stale one from seconds ago.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Lock
import numpy as np
import cv2


class CameraError(Exception):
    pass


class Camera(ABC):
    @abstractmethod
    def capture(self, fresh: bool = True) -> np.ndarray:
        """Return a single BGR frame.

        `fresh=True` (default): drain stale buffered frames before reading,
            so the returned frame reflects the camera's current view. Slower
            on network cameras (each drained frame = one MJPEG decode) but
            mandatory for /detect, /plan and the closed-loop step controller.

        `fresh=False`: return the latest buffered frame instantly. Good
            enough for an interactive viewfinder where the user just wants
            to see "approximately what the camera sees right now" without
            paying the drain cost on every poll.
        """


# Number of frames to drain when fresh=True. On a 1920x1080 IP Webcam stream
# each grab() costs ~30-50 ms (full MJPEG decode), so 5 was adding ~200 ms
# per fresh capture — felt sluggish in interactive use. 3 is enough to flush
# OpenCV's typical 1-3 frame internal buffer while keeping the latency tax
# at ~100 ms instead of 200 ms.
_DRAIN_FRAMES = 3


def _is_network_source(source) -> bool:
    """Network sources (IP Webcam, RTSP, HTTP MJPEG) are strings starting with
    a scheme. Local USB webcams are integer indices."""
    return isinstance(source, str) and "://" in source


class OpenCVCamera(Camera):
    """OpenCV VideoCapture wrapper.

    Opens the source once and keeps it open across captures. Reopening on
    every frame works for USB cams (slow but functional) but is brutal for
    network MJPEG: each capture re-establishes the HTTP connection (500 ms
    to 2 s of latency, sometimes failure). Persistent capture cuts that to
    sub-100 ms per call.

    Thread-safe: a lock serializes capture() so concurrent /detect and
    /execute/stream calls don't read from the same VideoCapture at the same
    time (which OpenCV does not support and will return torn frames for).
    """

    def __init__(self, source: int | str, resolution: tuple[int, int]):
        self._source = source
        self._resolution = resolution
        self._cap: cv2.VideoCapture | None = None
        self._lock = Lock()
        self._is_network = _is_network_source(source)

    def _ensure_open(self) -> cv2.VideoCapture:
        if self._cap is not None and self._cap.isOpened():
            return self._cap
        cap = cv2.VideoCapture(self._source)
        if not cap.isOpened():
            raise CameraError(f"Failed to open camera source: {self._source}")
        # Resolution hints are best-effort — many network cams ignore them
        # (the source URL controls resolution there) and some USB cams
        # silently clamp to a supported mode. We set them anyway because
        # they help on standard webcams.
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolution[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolution[1])
        # Smallest possible internal buffer — backend may ignore but it
        # reduces latency on backends that honour it (V4L2, GStreamer).
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._cap = cap
        return cap

    def _reopen(self) -> cv2.VideoCapture:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        return self._ensure_open()

    def capture(self, fresh: bool = True) -> np.ndarray:
        with self._lock:
            cap = self._ensure_open()

            # Drain stale buffered frames before reading the live one only
            # when freshness matters. Cheap for USB (a few ms), critical for
            # network MJPEG (otherwise the returned frame can be 1-3 s old).
            # When `fresh=False` we skip the drain entirely — the returned
            # frame may be slightly stale but no decode work is done.
            if fresh:
                for _ in range(_DRAIN_FRAMES):
                    cap.grab()

            ret, frame = cap.read()
            if not ret or frame is None:
                # One retry after reopening — handles transient WiFi drops on
                # the phone-on-hotspot setup without bubbling a hard failure.
                cap = self._reopen()
                if fresh:
                    for _ in range(_DRAIN_FRAMES):
                        cap.grab()
                ret, frame = cap.read()
                if not ret or frame is None:
                    raise CameraError(
                        f"Camera opened but failed to read frame from {self._source!r}. "
                        "If using IP Webcam, check the phone is still streaming and on "
                        "the same network as this PC."
                    )
            return frame

    def close(self) -> None:
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None

    def __del__(self):
        # Best-effort cleanup when the app shuts down. Errors here are
        # ignored because __del__ runs during interpreter teardown when
        # cv2 may already be partially unloaded.
        try:
            self.close()
        except Exception:
            pass


class FakeCamera(Camera):
    """Camera that always returns a fixed image. For tests."""

    def __init__(self, image: np.ndarray):
        self._image = image

    def capture(self, fresh: bool = True) -> np.ndarray:
        # `fresh` is irrelevant for a static image, but accept it so the
        # signature matches the abstract base.
        del fresh
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

    def capture(self, fresh: bool = True) -> np.ndarray:
        if self._override is not None:
            return self._override.copy()
        return self._fallback.capture(fresh=fresh)
