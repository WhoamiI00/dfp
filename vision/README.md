# vision — Robot detection and path planning

Phase 1 of the DFP reimplementation. Detects a robot's pose from a corner-mounted camera snapshot and plans pick-and-place paths for a non-holonomic differential-drive robot. See [the design spec](../docs/superpowers/specs/2026-04-10-vision-module-design.md) for details.

## Install

```bash
cd vision
pip install -r requirements.txt
```

## Run

```bash
python -m vision.scripts.run_server
```

Server starts on `http://localhost:8100`. Open the Next.js dev server (`cd ../web-app && npm run dev`) and visit `http://localhost:3000/vision`.

## Calibrate

1. **Intrinsic** (one-time): print a 9x6 chessboard, upload ~15 photos via the Calibration tab.
2. **Extrinsic** (per-setup): print 4 ArUco markers (DICT_4X4_50, IDs 0-3), place at workspace corners, click "Run extrinsic calibration".

## Test

```bash
pytest vision/tests -v
```
