"""Start the FastAPI server."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import uvicorn
from vision.src.api.camera import FakeCamera
from vision.src.api.server import create_app


def main():
    camera = None
    still_path = os.environ.get("VISION_STILL_IMAGE")
    if still_path:
        camera = FakeCamera.from_file(Path(still_path))
        print(f"[vision] Using still-image camera: {still_path}")
    app = create_app(camera=camera)
    uvicorn.run(app, host="127.0.0.1", port=8100)


if __name__ == "__main__":
    main()
