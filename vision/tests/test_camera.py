"""Tests for the camera abstraction.

The real OpenCV path is hard to exercise without a live camera, so we test
the source-classification helper, the FakeCamera, and verify the persistent-
handle behaviour by stubbing cv2.VideoCapture.
"""
import numpy as np
import pytest
from vision.src.api.camera import (
    Camera, CameraError, FakeCamera, SwitchableCamera, OpenCVCamera,
    _is_network_source,
)


def test_is_network_source_recognises_http_url():
    assert _is_network_source("http://192.168.137.19:8080/video") is True


def test_is_network_source_recognises_rtsp_url():
    assert _is_network_source("rtsp://cam.local/stream") is True


def test_is_network_source_rejects_integer_index():
    assert _is_network_source(0) is False
    assert _is_network_source(1) is False


def test_is_network_source_rejects_plain_string():
    assert _is_network_source("0") is False
    assert _is_network_source("/dev/video0") is False


def test_fake_camera_returns_copy_not_aliased():
    img = np.full((10, 10, 3), 42, dtype=np.uint8)
    cam = FakeCamera(img)
    out = cam.capture()
    out[0, 0] = 0
    # Original must be untouched — capture() returns a copy.
    assert cam.capture()[0, 0, 0] == 42


def test_switchable_camera_falls_back_when_no_override():
    fallback = FakeCamera(np.full((4, 4, 3), 7, dtype=np.uint8))
    cam = SwitchableCamera(fallback)
    assert cam.mode == "live"
    assert cam.capture()[0, 0, 0] == 7


def test_switchable_camera_uses_override_when_set():
    fallback = FakeCamera(np.full((4, 4, 3), 7, dtype=np.uint8))
    cam = SwitchableCamera(fallback)
    cam.set_image(np.full((4, 4, 3), 99, dtype=np.uint8))
    assert cam.mode == "test_image"
    assert cam.capture()[0, 0, 0] == 99
    cam.clear_image()
    assert cam.mode == "live"
    assert cam.capture()[0, 0, 0] == 7


# --- OpenCVCamera with a stubbed cv2.VideoCapture ---------------------------
# We swap cv2.VideoCapture for a class that records its calls so we can
# verify the camera doesn't reopen the source on every capture (Fix A) and
# does drain the buffer (Fix B).

class _StubCapture:
    """Minimal VideoCapture replacement. Records grab/read counts."""
    instances: list["_StubCapture"] = []

    def __init__(self, source):
        self.source = source
        self.opened = True
        self.grab_calls = 0
        self.read_calls = 0
        self.set_calls: list[tuple[int, float]] = []
        self.released = False
        _StubCapture.instances.append(self)

    def isOpened(self):
        return self.opened

    def set(self, prop, value):
        self.set_calls.append((prop, value))
        return True

    def grab(self):
        self.grab_calls += 1
        return True

    def read(self):
        self.read_calls += 1
        return True, np.full((4, 4, 3), 1, dtype=np.uint8)

    def release(self):
        self.released = True
        self.opened = False


@pytest.fixture
def stub_videocapture(monkeypatch):
    _StubCapture.instances.clear()
    import vision.src.api.camera as camera_mod
    monkeypatch.setattr(camera_mod.cv2, "VideoCapture", _StubCapture)
    return _StubCapture


def test_opencv_camera_opens_once_across_captures(stub_videocapture):
    cam = OpenCVCamera(source="http://x/video", resolution=(640, 480))
    cam.capture()
    cam.capture()
    cam.capture()
    # Three captures, one VideoCapture instance — Fix A holds.
    assert len(stub_videocapture.instances) == 1
    cam.close()


def test_opencv_camera_drains_buffer_before_each_read(stub_videocapture):
    from vision.src.api.camera import _DRAIN_FRAMES
    cam = OpenCVCamera(source="http://x/video", resolution=(640, 480))
    cam.capture()
    inst = stub_videocapture.instances[0]
    # Drain count == _DRAIN_FRAMES, then one read for the actual frame.
    assert inst.grab_calls == _DRAIN_FRAMES
    assert inst.read_calls == 1
    cam.close()


def test_opencv_camera_skips_drain_when_fresh_false(stub_videocapture):
    cam = OpenCVCamera(source="http://x/video", resolution=(640, 480))
    cam.capture(fresh=False)
    inst = stub_videocapture.instances[0]
    # No drain when fresh=False — viewfinder path.
    assert inst.grab_calls == 0
    assert inst.read_calls == 1
    cam.close()


def test_opencv_camera_fresh_true_drains_explicitly(stub_videocapture):
    from vision.src.api.camera import _DRAIN_FRAMES
    cam = OpenCVCamera(source="http://x/video", resolution=(640, 480))
    cam.capture(fresh=True)
    inst = stub_videocapture.instances[0]
    assert inst.grab_calls == _DRAIN_FRAMES
    cam.close()


def test_switchable_camera_forwards_fresh_flag(stub_videocapture):
    cam = SwitchableCamera(OpenCVCamera(source="http://x/video", resolution=(640, 480)))
    cam.capture(fresh=False)
    inst = stub_videocapture.instances[0]
    assert inst.grab_calls == 0
    cam.close = getattr(cam, "close", lambda: None)
    cam._fallback.close()


def test_opencv_camera_reopens_after_failed_read(stub_videocapture, monkeypatch):
    # Make the first instance fail on read, second succeed.
    original_read = _StubCapture.read
    call_state = {"first": True}

    def flaky_read(self):
        if call_state["first"] and self is _StubCapture.instances[0]:
            call_state["first"] = False
            self.read_calls += 1
            return False, None
        return original_read(self)

    monkeypatch.setattr(_StubCapture, "read", flaky_read)

    cam = OpenCVCamera(source="http://x/video", resolution=(640, 480))
    frame = cam.capture()  # should retry transparently
    assert frame is not None
    # First instance was released, second instance was created and read OK.
    assert len(stub_videocapture.instances) == 2
    assert stub_videocapture.instances[0].released is True
    cam.close()


def test_opencv_camera_raises_after_two_failed_reads(stub_videocapture, monkeypatch):
    def always_fail(self):
        self.read_calls += 1
        return False, None
    monkeypatch.setattr(_StubCapture, "read", always_fail)

    cam = OpenCVCamera(source="http://x/video", resolution=(640, 480))
    with pytest.raises(CameraError):
        cam.capture()
    cam.close()


def test_opencv_camera_close_releases_handle(stub_videocapture):
    cam = OpenCVCamera(source="http://x/video", resolution=(640, 480))
    cam.capture()
    cam.close()
    assert stub_videocapture.instances[0].released is True
