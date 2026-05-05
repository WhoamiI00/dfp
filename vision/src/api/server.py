"""FastAPI app entry point. Wires routes, paths, and camera."""
import shutil
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from vision.src.api.routes import router, set_state, Paths
from vision.src.api.camera import OpenCVCamera, SwitchableCamera
from vision.src.api.config_loader import load_settings, load_shelves, ConfigError
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
    p.movement_plans = STATE_DIR / "movement_plans.json"
    return p


def _seed_default_shelves_if_needed(paths: Paths) -> None:
    """If shelves.json is missing or has fewer than 6 shelves, copy the
    canonical 2-column x 3-floor layout into place.

    Only fires when paths.shelves is inside the real CONFIG_DIR — tests
    point paths.shelves at a tmp dir and have their own fixtures, so we
    skip them. We never overwrite a layout that already has 6 shelves.
    """
    try:
        paths.shelves.resolve().relative_to(CONFIG_DIR.resolve())
    except (ValueError, OSError):
        return  # tmp dir / different filesystem -> not the real config

    template = CONFIG_DIR / "shelves.production.json"
    if not template.exists():
        return  # nothing to seed from; user is on their own
    needs_seed = False
    if not paths.shelves.exists():
        needs_seed = True
    else:
        try:
            existing = load_shelves(paths.shelves)
            if len(existing) < 6:
                needs_seed = True
        except Exception:
            # Malformed file -> reseed rather than crash on startup.
            needs_seed = True
    if needs_seed:
        paths.shelves.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(template, paths.shelves)


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
    _seed_default_shelves_if_needed(paths)

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
