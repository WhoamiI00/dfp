"""Stream a plan from the vision API to the Mega over HC-05 Bluetooth.

Usage:
    # 1. Smoke-test the link only:
    python -m vision.scripts.run_plan_on_robot --port COM6 --ping

    # 2. Send literal char commands:
    python -m vision.scripts.run_plan_on_robot --port COM6 --cmds "FFLFG"

    # 3. Fetch a real plan from the running vision server and execute it:
    python -m vision.scripts.run_plan_on_robot --port COM6 --task pick_place --source shelf_A --destination shelf_B

    # 4. See what would be sent without touching Bluetooth:
    python -m vision.scripts.run_plan_on_robot --port COM6 --dry-run --task pick_place --source shelf_A --destination shelf_B

Single-char protocol (matches firmware/plan_executor/plan_executor.ino):
    F   forward one cell        ->  OK
    B   backward one cell       ->  OK
    L   turn left  90°          ->  OK
    R   turn right 90°          ->  OK
    G   grab  (placeholder 2 s) ->  OK
    P   place (placeholder 2 s) ->  OK
    S   emergency stop          ->  OK
    ?   ping                    ->  PONG

Why single-char with cell-step semantics: the robot can't do precise angles
or arbitrary distances — only 90° spins and one-cell forward steps. The
planner is configured 4-connected (vision/src/planning/task.py) so every
TURN waypoint is exactly ±90° or 180° and every DRIVE distance is an integer
multiple of cell_size_m. We translate each waypoint into the corresponding
sequence of single chars on the PC and pace them with OK acks.
"""
import argparse
import sys
import time

import serial
import requests


VISION_API = "http://127.0.0.1:8100/api"
CELL_SIZE_M = 0.25  # must match vision/config/settings.yaml workspace.cell_size_m


def normalize_deg(d: float) -> float:
    """Wrap an angle to (-180, 180]."""
    return ((d + 180.0) % 360.0) - 180.0


def open_link(port: str, baud: int = 9600) -> serial.Serial:
    print(f"opening {port} @ {baud}…")
    bt = serial.Serial(port, baud, timeout=10)
    time.sleep(2)  # HC-05 link warmup
    bt.reset_input_buffer()
    return bt


def send_char(bt: serial.Serial, c: str) -> str:
    bt.write(c.encode())
    reply = bt.readline().decode(errors="replace").strip()
    print(f"  > {c}    < {reply}")
    return reply


def waypoint_to_chars(wp: dict) -> str:
    """Translate one planner waypoint into zero or more single-char commands.

    With 4-connected A* every TURN delta is one of {0, ±90, 180} and every
    DRIVE distance is an integer multiple of CELL_SIZE_M, so the conversion
    is exact.
    """
    t = wp.get("type")

    if t == "turn":
        target = wp["target_heading_deg"]
        current = (wp.get("from_pose") or {}).get("heading_deg", 0.0)
        delta = normalize_deg(target - current)
        steps_90 = round(abs(delta) / 90.0)
        if steps_90 == 0:
            return ""
        return ("L" if delta > 0 else "R") * steps_90  # +CCW = left

    if t == "drive":
        cells = round(wp["distance_m"] / CELL_SIZE_M)
        return "F" * max(cells, 0)

    if t == "grab":
        return "G"
    if t == "place":
        return "P"

    return ""  # arrive / unknown


def plan_to_chars(waypoints: list[dict]) -> str:
    return "".join(waypoint_to_chars(w) for w in waypoints)


def upload_test_image(path: str) -> None:
    """Push a still image into the running server's SwitchableCamera so
    detection runs against it instead of the live camera. Idempotent."""
    with open(path, "rb") as fh:
        r = requests.post(
            f"{VISION_API}/camera/image",
            files={"file": (path, fh, "image/png")},
            timeout=10,
        )
    if not r.ok:
        print(f"!! /camera/image returned {r.status_code}: {r.text}", file=sys.stderr)
        sys.exit(2)
    print(f"camera now using test image: {path}")


def fetch_plan(task: str, source: str | None, destination: str) -> list[dict]:
    body: dict = {"task": task, "destination_shelf_id": destination}
    if source:
        body["source_shelf_id"] = source
    r = requests.post(f"{VISION_API}/plan", json=body, timeout=10)
    if not r.ok:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        print(f"!! /plan returned {r.status_code}: {detail}", file=sys.stderr)
        sys.exit(2)
    return r.json()["waypoints"]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True, help="HC-05 outgoing COM port (e.g. COM6)")
    p.add_argument("--baud", type=int, default=9600)
    p.add_argument("--ping", action="store_true", help="just send ? and exit")
    p.add_argument("--cmds", help='literal char string to send, e.g. "FFLFG"')
    p.add_argument("--task", choices=["navigate", "pick_place"])
    p.add_argument("--source", help="source shelf id (pick_place only)")
    p.add_argument("--destination", help="destination shelf id")
    p.add_argument("--image", help="path to a still image to use as the camera frame "
                                   "(uploaded to /api/camera/image before planning)")
    p.add_argument("--dry-run", action="store_true",
                   help="print the chars that would be sent without opening the port")
    args = p.parse_args()

    # Resolve the char sequence before opening the port.
    sequence: str = ""
    if args.ping:
        sequence = "?"
    elif args.cmds:
        sequence = "".join(args.cmds.split())  # strip whitespace
    elif args.task and args.destination:
        if args.image:
            upload_test_image(args.image)
        waypoints = fetch_plan(args.task, args.source, args.destination)
        sequence = plan_to_chars(waypoints)
        print(f"plan has {len(waypoints)} waypoints -> {len(sequence)} chars: {sequence}")
    else:
        p.error("supply one of: --ping | --cmds | (--task and --destination)")

    if args.dry_run:
        print(f"would send: {sequence}")
        return 0

    bt = open_link(args.port, args.baud)
    try:
        for c in sequence:
            reply = send_char(bt, c)
            if not (reply == "OK" or reply == "PONG"):
                print(f"!! unexpected reply, aborting: {reply!r}")
                return 1
        print("done.")
    finally:
        bt.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
