"""FastAPI app entry point. Wires routes, paths, and camera."""
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from vision.src.api.routes import router, set_state, Paths
from vision.src.api.camera import OpenCVCamera, SwitchableCamera
from vision.src.api.config_loader import load_settings, ConfigError
from vision.src.inventory.orders import OrderQueue


VISION_ROOT = Path(__file__).resolve().parents[2]  # vision/
CONFIG_DIR = VISION_ROOT / "config"


STATE_DIR = VISION_ROOT / "state"


def build_paths() -> Paths:
    p = Paths()
    p.settings = CONFIG_DIR / "settings.yaml"
    p.shelves = CONFIG_DIR / "shelves.json"
    p.intrinsics = CONFIG_DIR / "camera_intrinsics.yaml"
    p.extrinsics = CONFIG_DIR / "camera_extrinsics.yaml"
    p.custom_hsv = CONFIG_DIR / "custom_hsv.yaml"
    # Runtime state (sqlite, etc.) lives outside config/ since it's
    # written to and shouldn't be checked into git.
    p.orders_db = STATE_DIR / "orders.db"
    return p


def create_app(camera=None) -> FastAPI:
    app = FastAPI(title="DFP Vision API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    paths = build_paths()

    if camera is None:
        settings = load_settings(paths.settings)
        camera = OpenCVCamera(
            source=settings.camera.source,
            resolution=tuple(settings.camera.resolution),
        )

    if not isinstance(camera, SwitchableCamera):
        camera = SwitchableCamera(camera)

    orders = OrderQueue(paths.orders_db)
    set_state(paths, camera, orders=orders)
    app.include_router(router)

    # Translate ConfigError to a 500 with the same shape the rest of the API
    # uses for error envelopes. Without this, malformed settings.yaml would
    # bubble up as FastAPI's generic "Internal Server Error" with no detail.
    @app.exception_handler(ConfigError)
    async def _config_error_handler(_request: Request, exc: ConfigError) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": {"error": "config_error", "message": str(exc)}},
        )

    return app


app = None  # Created by run_server.py


def get_app():
    global app
    if app is None:
        app = create_app()
    return app
