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

## Known limitations

Phase 1 prototype notes:

- **HSV ranges are untuned.** The red/green marker thresholds in `src/detection/hsv_ranges.py` are starting values only. Tune them once for your specific lighting before relying on detection.
- **Robot must be in frame for `/api/plan`.** If the robot markers are not detected, the plan endpoint returns HTTP 422 `{error: "robot_not_detected"}`. Capture the robot somewhere visible first.
- **Snapshot workflow only.** Each capture/detect/plan cycle is triggered manually from the web UI. Continuous video tracking is out of scope for phase 1.
- **Grab and place are stubs.** The waypoint sequence includes `grab` and `place` actions, but the robot controller that consumes them is still in development. The web UI's Execute button is intentionally disabled.
- **No frontend tests yet.** The `/vision` route is smoke-tested by clicking through; Playwright or similar can be added later.
