"""Replace fake/hallucinated ArUco patterns in a test image with real ones.

Image generators (Gemini, etc.) produce visually plausible but bit-invalid
ArUco markers — cv2.aruco rejects them. This script finds the white tag
squares the model drew, then warps real DICT_4X4_50 markers onto them so the
full vision pipeline (extrinsic calibration, robot detection) actually runs
on the synthetic scene.

Assumes a top-down-ish view with:
  * 4 corner ArUco backgrounds (largest white squares)  -> IDs 0,1,2,3
    (assigned by image position: top-left, top-right, bottom-right, bottom-left)
  * 1 robot tag on the chassis (smaller white square inside the workspace) -> ID 4

Usage:
    python -m vision.scripts.composite_real_aruco INPUT.png OUTPUT.png [--debug]
"""
from __future__ import annotations
import argparse
from pathlib import Path
import cv2
import numpy as np

from vision.src.calibration.extrinsic import ARUCO_DICT


CORNER_IDS = [0, 1, 2, 3]  # TL, TR, BR, BL
ROBOT_ID = 4


def _find_white_tag_squares(bgr: np.ndarray, min_area_frac: float = 0.0008,
                            max_area_frac: float = 0.05) -> list[np.ndarray]:
    """Return contours of plausible ArUco-tag white squares, biggest first.

    A 'white tag square' is the white paper backing the model drew around the
    black ArUco pattern. We threshold for very-bright regions, then keep
    contours whose area falls in [min_area_frac, max_area_frac] of the image
    and are roughly square (4-corner approx, aspect ~1).
    """
    h, w = bgr.shape[:2]
    img_area = h * w
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    # Fixed high threshold: tag papers are near-white (>230), floor is mid-grey
    # (~170-200). Otsu often picks the wrong split because the floor takes more
    # area than the papers, biasing the histogram.
    _, mask = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY)
    # Close small gaps — the black ArUco bits cut deep into the white square,
    # and the closing has to span them. Kernel size scales with image size so
    # this works on both 600px previews and 2752px originals.
    k = max(15, int(min(h, w) * 0.02))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[tuple[float, np.ndarray]] = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area_frac * img_area or area > max_area_frac * img_area:
            continue
        # Use min-area rect as the quad — approxPolyDP often returns 5-8 pts
        # when the closing didn't fully fill the ArUco bit-cuts. min-area rect
        # is more robust and still gives a tight square fit when the contour
        # really is square-ish.
        rect = cv2.minAreaRect(c)
        (_, _), (rw, rh), _ = rect
        if rw < 1 or rh < 1:
            continue
        aspect = max(rw, rh) / min(rw, rh)
        if aspect > 1.4:
            continue
        rect_area = rw * rh
        if rect_area > 0 and area / rect_area < 0.55:
            # Contour fills less than 55% of its bounding rect — not square-ish.
            continue
        box = cv2.boxPoints(rect).astype(np.float32)
        candidates.append((rect_area, box))

    candidates.sort(key=lambda t: -t[0])
    return [c for _, c in candidates]


def _order_corners(quad: np.ndarray) -> np.ndarray:
    """Return the 4 corners in (TL, TR, BR, BL) order."""
    pts = quad.reshape(4, 2)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).ravel()
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def _classify_squares(squares: list[np.ndarray], img_shape: tuple[int, int]
                      ) -> tuple[dict[int, np.ndarray], np.ndarray]:
    """Pick 4 corner squares + 1 robot square from candidates.

    Heuristic: among the top candidates, the 4 corner tags sit nearest the image
    corners. The robot tag is the largest remaining square (or the next-best
    candidate near the image centre).
    """
    if len(squares) < 5:
        raise RuntimeError(
            f"Expected >=5 white tag squares, found {len(squares)}. "
            "Try lowering min_area_frac or check the input image."
        )

    h, w = img_shape
    image_corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)

    centroids = np.array([sq.mean(axis=0) for sq in squares])

    # For each image corner, pick the nearest unique square as that ArUco ID.
    used: set[int] = set()
    corner_assignment: dict[int, np.ndarray] = {}
    for tag_id, ic in zip(CORNER_IDS, image_corners):
        dists = np.linalg.norm(centroids - ic, axis=1)
        # Mask out already-used squares.
        for u in used:
            dists[u] = np.inf
        best = int(np.argmin(dists))
        used.add(best)
        corner_assignment[tag_id] = _order_corners(squares[best])

    # Robot tag: largest remaining square (squares list is area-sorted desc).
    robot_quad = None
    for i, sq in enumerate(squares):
        if i in used:
            continue
        robot_quad = _order_corners(sq)
        break
    if robot_quad is None:
        raise RuntimeError("Found 4 corner squares but no remaining square for the robot tag.")

    return corner_assignment, robot_quad


def _generate_marker(tag_id: int, size_px: int = 400, quiet_ratio: float = 0.12
                     ) -> np.ndarray:
    """Return a BGR image of the ArUco tag with a white quiet zone."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    tag = cv2.aruco.generateImageMarker(aruco_dict, tag_id, size_px)
    quiet = max(8, int(round(size_px * quiet_ratio)))
    canvas_px = size_px + 2 * quiet
    canvas = 255 * np.ones((canvas_px, canvas_px), dtype="uint8")
    canvas[quiet:quiet + size_px, quiet:quiet + size_px] = tag
    return cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)


def _warp_onto(dest: np.ndarray, src: np.ndarray, dest_quad: np.ndarray) -> None:
    """Warp src image onto dest at the 4-point dest_quad (in TL,TR,BR,BL order)."""
    sh, sw = src.shape[:2]
    src_quad = np.array([[0, 0], [sw - 1, 0], [sw - 1, sh - 1], [0, sh - 1]],
                        dtype=np.float32)
    H = cv2.getPerspectiveTransform(src_quad, dest_quad)
    warped = cv2.warpPerspective(src, H, (dest.shape[1], dest.shape[0]),
                                 flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT)
    # Mask = where warped is non-zero (covers the destination quad).
    mask = np.zeros(dest.shape[:2], dtype=np.uint8)
    cv2.fillConvexPoly(mask, dest_quad.astype(np.int32), 255)
    # Copy warped pixels into dest where mask is set.
    dest[mask > 0] = warped[mask > 0]


def composite(input_path: Path, output_path: Path, debug: bool = False) -> None:
    img = cv2.imread(str(input_path))
    if img is None:
        raise SystemExit(f"Failed to read image: {input_path}")

    squares = _find_white_tag_squares(img)
    if debug:
        dbg = img.copy()
        for i, sq in enumerate(squares[:10]):
            cv2.polylines(dbg, [sq.astype(np.int32)], True, (0, 255, 0), 4)
            cx, cy = sq.mean(axis=0).astype(int)
            cv2.putText(dbg, str(i), (cx, cy), cv2.FONT_HERSHEY_SIMPLEX,
                        2, (0, 0, 255), 3)
        dbg_path = output_path.with_name(output_path.stem + "_debug.png")
        cv2.imwrite(str(dbg_path), dbg)
        print(f"Wrote debug overlay: {dbg_path} (top {min(10, len(squares))} candidates)")

    corner_quads, robot_quad = _classify_squares(squares, img.shape[:2])

    out = img.copy()
    for tag_id, quad in corner_quads.items():
        marker = _generate_marker(tag_id, size_px=500)
        _warp_onto(out, marker, quad)
    robot_marker = _generate_marker(ROBOT_ID, size_px=500)
    _warp_onto(out, robot_marker, robot_quad)

    cv2.imwrite(str(output_path), out)
    print(f"Wrote {output_path}")
    print(f"  Corner IDs {CORNER_IDS} placed at TL/TR/BR/BL")
    print(f"  Robot ID {ROBOT_ID} placed on remaining square")

    # Sanity-check: re-detect with cv2.aruco to confirm the patterns are valid.
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    detector = cv2.aruco.ArucoDetector(aruco_dict, cv2.aruco.DetectorParameters())
    corners, ids, _ = detector.detectMarkers(out)
    found = sorted([int(i) for i in ids.ravel()]) if ids is not None else []
    print(f"  Re-detection found IDs: {found}")
    expected = sorted(CORNER_IDS + [ROBOT_ID])
    if found != expected:
        print(f"  WARNING: expected {expected}, got {found}. The compositor may have "
              "misclassified squares — try --debug to inspect.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path, help="Path to input PNG/JPEG.")
    p.add_argument("output", type=Path, help="Where to write the composited image.")
    p.add_argument("--debug", action="store_true",
                   help="Also write *_debug.png with detected square candidates.")
    args = p.parse_args()
    composite(args.input, args.output, debug=args.debug)


if __name__ == "__main__":
    main()
