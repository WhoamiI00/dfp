"""Generate a single A4-sized PNG with multiple ArUco tags laid out for printing.

Why a separate script: `generate_tag.py` produces one tag at its physical size
with a tight quiet zone — convenient but printer-dependent (the printer may
auto-scale to fit the page, breaking the calibration). This script produces a
PNG already sized to A4 so the printer leaves it alone — print at 100 %
("Actual size" / "Do not scale") and the tags come out at exactly the
configured millimetre size.

Default layout: robot tag (ID 4, 50 mm) plus three shelf tags (IDs 5-7, 40 mm
each), each labelled with its ID, all on one A4 page. Cut along the borders
after printing.

Usage:
    python -m vision.scripts.generate_tag_sheet                # default layout
    python -m vision.scripts.generate_tag_sheet --out sheet.png
    python -m vision.scripts.generate_tag_sheet --tags 4:50,5:40,6:40,7:40

The --tags syntax is "id:size_mm" pairs separated by commas.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from pathlib import Path
import cv2
import numpy as np
from vision.src.calibration.extrinsic import ARUCO_DICT


# A4 dimensions and assumed print DPI. 300 DPI is the standard for clean
# black-and-white print output; lower DPI risks fuzzy tag edges that hurt
# corner detection. The PNG file size at 300 DPI is ~1 MB — fine.
_A4_WIDTH_MM = 210
_A4_HEIGHT_MM = 297
_DPI = 300

# Quiet zone around each tag (white border ArUco needs to find the tag's
# outer edge). 8 mm is generous — survives a careless cut.
_QUIET_ZONE_MM = 8

# Label font: drawn below each tag so you can tell IDs apart after cutting.
_LABEL_HEIGHT_MM = 6
_FONT = cv2.FONT_HERSHEY_SIMPLEX
_FONT_SCALE = 0.7
_FONT_THICKNESS = 2


@dataclass
class TagSpec:
    tag_id: int
    size_mm: float
    label: str   # printed under the tag, e.g. "ID 4 (robot, 50mm)"


def _mm_to_px(mm: float) -> int:
    return int(round(mm / 25.4 * _DPI))


def _render_tag_block(spec: TagSpec) -> np.ndarray:
    """One tag + quiet zone + label, on a white block.

    The block's outer dimensions account for tag + 2*quiet zone + label area.
    """
    tag_px = _mm_to_px(spec.size_mm)
    quiet_px = _mm_to_px(_QUIET_ZONE_MM)
    label_px = _mm_to_px(_LABEL_HEIGHT_MM)

    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    tag = cv2.aruco.generateImageMarker(aruco_dict, spec.tag_id, tag_px)

    block_w = tag_px + 2 * quiet_px
    block_h = tag_px + 2 * quiet_px + label_px
    block = np.full((block_h, block_w), 255, dtype=np.uint8)

    # Place tag with quiet zone.
    block[quiet_px:quiet_px + tag_px, quiet_px:quiet_px + tag_px] = tag

    # Centred label below the tag.
    (text_w, text_h), _ = cv2.getTextSize(spec.label, _FONT, _FONT_SCALE, _FONT_THICKNESS)
    text_x = max(0, (block_w - text_w) // 2)
    text_y = tag_px + 2 * quiet_px + (label_px + text_h) // 2
    cv2.putText(block, spec.label, (text_x, text_y), _FONT, _FONT_SCALE, 0, _FONT_THICKNESS, cv2.LINE_AA)

    # Faint cut border so it's obvious where to scissor.
    cv2.rectangle(block, (0, 0), (block_w - 1, block_h - 1), 200, thickness=1)
    return block


def _layout_blocks_on_a4(blocks: list[np.ndarray]) -> np.ndarray:
    """Lay tag blocks out top-to-bottom, left-to-right on an A4 canvas with
    a small page margin. Wraps to a new row when a block doesn't fit on the
    current row's right side. Raises if a single block is bigger than A4.
    """
    page_w = _mm_to_px(_A4_WIDTH_MM)
    page_h = _mm_to_px(_A4_HEIGHT_MM)
    margin = _mm_to_px(10)
    gap = _mm_to_px(5)

    canvas = np.full((page_h, page_w), 255, dtype=np.uint8)

    cur_x = margin
    cur_y = margin
    row_h = 0
    for b in blocks:
        bh, bw = b.shape
        if bh > page_h - 2 * margin or bw > page_w - 2 * margin:
            raise ValueError(
                f"Tag block {bw}x{bh}px doesn't fit in A4 with margins; "
                "reduce tag size."
            )
        # Wrap to next row if this block won't fit on the right.
        if cur_x + bw > page_w - margin:
            cur_x = margin
            cur_y += row_h + gap
            row_h = 0
        if cur_y + bh > page_h - margin:
            raise ValueError(
                "Tags don't fit on one A4 page. Reduce sizes or split into "
                "multiple pages (not yet supported)."
            )
        canvas[cur_y:cur_y + bh, cur_x:cur_x + bw] = b
        cur_x += bw + gap
        row_h = max(row_h, bh)
    return canvas


def _parse_tag_arg(s: str) -> list[TagSpec]:
    """Parse "4:50,5:40,6:40,7:40" into TagSpec list."""
    specs = []
    for token in s.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" not in token:
            raise argparse.ArgumentTypeError(
                f"Bad --tags entry {token!r}; expected 'id:size_mm'"
            )
        id_str, size_str = token.split(":", 1)
        tag_id = int(id_str)
        size_mm = float(size_str)
        specs.append(TagSpec(
            tag_id=tag_id,
            size_mm=size_mm,
            label=f"ID {tag_id} ({int(size_mm)}mm)",
        ))
    if not specs:
        raise argparse.ArgumentTypeError("--tags must list at least one tag")
    return specs


_DEFAULT_TAGS = [
    TagSpec(tag_id=4, size_mm=50, label="ID 4 - ROBOT (50mm)"),
    TagSpec(tag_id=5, size_mm=40, label="ID 5 - shelf (40mm)"),
    TagSpec(tag_id=6, size_mm=40, label="ID 6 - shelf (40mm)"),
    TagSpec(tag_id=7, size_mm=40, label="ID 7 - shelf (40mm)"),
]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--tags", type=_parse_tag_arg, default=None,
        help='Comma-separated "id:size_mm" pairs. Default: 4:50,5:40,6:40,7:40',
    )
    p.add_argument(
        "--out", type=Path, default=None,
        help="Output PNG path. Default: vision/tag_sheet_a4.png",
    )
    args = p.parse_args()

    specs = args.tags if args.tags is not None else _DEFAULT_TAGS
    out_path = args.out or (Path(__file__).resolve().parents[1] / "tag_sheet_a4.png")

    blocks = [_render_tag_block(s) for s in specs]
    sheet = _layout_blocks_on_a4(blocks)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), sheet)

    print(f"Wrote {out_path}")
    print(f"  Page size: {_A4_WIDTH_MM} x {_A4_HEIGHT_MM} mm at {_DPI} DPI ({sheet.shape[1]}x{sheet.shape[0]} px)")
    print(f"  Tags ({len(specs)}):")
    for s in specs:
        print(f"    - ID {s.tag_id}, {s.size_mm:.0f} mm  ({s.label})")
    print()
    print("Print at 100 % scale ('Actual size' / 'Do not scale').")
    print("After printing, measure a black tag edge with a ruler — should match the configured mm size.")


if __name__ == "__main__":
    main()
