"""Generate a printable PNG of an ArUco DICT_4X4_50 tag.

Use this to print the robot's tag (ID 4) at exactly the size configured in
settings.yaml (`robot.markers.tag_size_m`). Print the resulting PNG at 100 %
scale on white paper, glue flat on top of the robot.

Usage:
    python -m vision.scripts.generate_tag                    # robot tag from settings
    python -m vision.scripts.generate_tag --id 4 --size-m 0.05
    python -m vision.scripts.generate_tag --id 0 --size-m 0.10 --out corner0.png

The generated image's physical size at 100 % print scale equals the
requested `--size-m` (assumes 96 DPI; many OS print dialogs default to this
or let you pick). For dead-accurate sizing, generate at higher pixel
density and scale in your print dialog.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import cv2
import numpy as np
from vision.src.calibration.extrinsic import ARUCO_DICT
from vision.src.api.config_loader import load_settings


_DEFAULT_DPI = 96


def generate(tag_id: int, size_m: float, out_path: Path, dpi: int = _DEFAULT_DPI,
             quiet_zone_ratio: float = 0.15) -> None:
    """Render `tag_id` to `out_path` at `size_m` metres on a `dpi`-DPI page.

    Adds a white quiet zone around the tag (default 15 % of tag size) so the
    detector has a clean border to find — printing edge-to-edge with no
    margin makes detection unreliable.
    """
    metres_per_inch = 0.0254
    tag_px = max(1, int(round(size_m / metres_per_inch * dpi)))
    quiet_px = max(8, int(round(tag_px * quiet_zone_ratio)))

    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    tag = cv2.aruco.generateImageMarker(aruco_dict, tag_id, tag_px)

    canvas_px = tag_px + 2 * quiet_px
    canvas = 255 * np.ones((canvas_px, canvas_px), dtype="uint8")
    canvas[quiet_px:quiet_px + tag_px, quiet_px:quiet_px + tag_px] = tag

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), canvas)
    print(
        f"Wrote {out_path} — tag {tag_px}px + {quiet_px}px quiet zone, "
        f"= {size_m * 100:.1f} cm at {dpi} DPI."
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--id", type=int, default=None, help="ArUco tag ID. Default: robot tag from settings.")
    p.add_argument("--size-m", type=float, default=None, help="Physical tag size in metres. Default: from settings.")
    p.add_argument("--out", type=Path, default=None, help="Output PNG path.")
    p.add_argument("--dpi", type=int, default=_DEFAULT_DPI, help="Print DPI (default 96).")
    args = p.parse_args()

    if args.id is None or args.size_m is None:
        config_dir = Path(__file__).resolve().parents[1] / "config"
        settings = load_settings(config_dir / "settings.yaml")
        if args.id is None:
            args.id = settings.robot.markers.tag_id
        if args.size_m is None:
            args.size_m = settings.robot.markers.tag_size_m

    if args.out is None:
        args.out = Path(__file__).resolve().parents[1] / f"tag_{args.id}_{int(args.size_m * 1000)}mm.png"

    generate(args.id, args.size_m, args.out, dpi=args.dpi)


if __name__ == "__main__":
    main()
