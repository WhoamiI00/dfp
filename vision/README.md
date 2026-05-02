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

## Camera setup

The `camera.source` field in `config/settings.yaml` accepts several forms:

| Form | Use case |
| --- | --- |
| `0`, `1`, `2`, ... | Local USB webcam by device index. Try `1` if `0` is your laptop's built-in cam. |
| `"http://HOST:8080/video"` | Android **IP Webcam** MJPEG stream. |
| `"rtsp://..."` | Generic RTSP camera. |

### Phone as camera (Android, no driver install)

1. Install **IP Webcam** by Pavel Khlebovich from the Play Store.
2. Open the app, scroll to bottom, tap **Start server**.
3. The app shows two URLs (e.g. `http://192.168.137.19:8080`). Use the one that's on the same network as your PC.
4. Set in `config/settings.yaml`:
   ```yaml
   camera:
     source: "http://192.168.137.19:8080/video"   # note the /video suffix
     resolution: [1280, 720]
   ```
5. Restart `run_server` so it picks up the new source.

**Phone-on-laptop-hotspot setup**: when your phone connects to the laptop's mobile hotspot, the laptop is the gateway. The phone sees the laptop directly on the hotspot subnet (`192.168.137.x` on Windows by default), so the URL just works — your college LAN doesn't need to know about the phone (it's on a different network adapter).

**Sanity-check the connection** before pointing the server at it:
```bash
curl -I http://192.168.137.19:8080/
```
Should return `HTTP/1.1 200 OK`. If it times out, the phone and laptop aren't on the same network.

The camera handle is opened once and reused across captures (network MJPEG can take 1-2 s to (re)connect, so per-frame reopens would cripple closed-loop). The internal frame buffer is drained before each read so `/detect` always sees a current frame, not one from seconds ago.

## Calibrate

1. **Intrinsic** (one-time per camera): print a 9x6 chessboard, upload ~15 photos via the Calibration tab.
2. **Extrinsic** (per-setup): print 4 ArUco markers (DICT_4X4_50, IDs 0-3), place at workspace corners, click "Run extrinsic calibration".

## Robot detection

The robot's pose is found via one of three modes, set by `robot.detector` in `config/settings.yaml`:

| Mode | Behaviour |
| --- | --- |
| `aruco` | Single ArUco tag on top of robot. Most robust; ignores lighting completely. Fails cleanly if tag is hidden. |
| `hsv` | Front and back colour stickers (the original behaviour). Tunable via the Calibration tab's colour picker. |
| `aruco_then_hsv` | **Default.** Try ArUco first, fall back to HSV. Lets you transition incrementally. |

### Setting up the ArUco robot tag

1. Generate a printable PNG of tag ID 4 at the configured size:
   ```bash
   python -m vision.scripts.generate_tag
   ```
   Output goes to `vision/tag_4_50mm.png` by default. Override with `--id` / `--size-m` / `--out`.
2. Print at 100 % scale on white paper. Verify the printed size with a ruler — the file targets the `tag_size_m` from settings (default 50 mm).
3. Glue the tag flat on top of the robot, oriented so the **top edge of the tag points the way the robot drives forward** (the heading axis).
4. Update `robot.markers.tag_size_m` if you printed a different size.
5. The HSV stickers can stay on as a fallback — `aruco_then_hsv` will use ArUco when visible and silently fall back when not.

ArUco IDs in use:
- 0–3: workspace corners (extrinsic calibration)
- 4: robot
- 5+: free for future use (e.g. shelves)

### Tuning the HSV fallback

The mask pipeline now applies CLAHE (Contrast Limited Adaptive Histogram Equalization) on the V channel before thresholding. This widens the lighting band a fixed range survives — a threshold tuned in afternoon light no longer breaks under evening LED. You don't need to do anything to enable it; it's always on. Existing custom HSV ranges keep working and become more lighting-tolerant for free.

The click-to-sample colour picker in the Calibration tab still works the same way: click the marker in the live frame, the backend returns a forgiving range that masks similar pixels.

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
