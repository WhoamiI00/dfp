"""Draw shelves, robot pose, and path on an image."""
import math
import numpy as np
import cv2
from vision.src.models import (
    Settings, Shelf, RobotPose, Waypoint, DriveWaypoint, Intrinsics, Extrinsics,
)


def _project_world_to_pixel(
    world_xyz: np.ndarray,
    intrinsics: Intrinsics,
    extrinsics: Extrinsics,
) -> tuple[int, int] | None:
    R, _ = cv2.Rodrigues(extrinsics.rvec)
    cam = R @ world_xyz + extrinsics.tvec
    if cam[2] <= 0:
        return None
    K = intrinsics.camera_matrix
    u = K[0, 0] * (cam[0] / cam[2]) + K[0, 2]
    v = K[1, 1] * (cam[1] / cam[2]) + K[1, 2]
    return int(round(u)), int(round(v))


def draw_overlay(
    frame: np.ndarray,
    shelves: list[Shelf],
    robot_pose: RobotPose | None,
    waypoints: list[Waypoint],
    intrinsics: Intrinsics,
    extrinsics: Extrinsics,
    travel_height_m: float,
) -> np.ndarray:
    """Return a copy of `frame` with shelves, robot, and path drawn on it."""
    out = frame.copy()

    # --- Draw shelves as rectangles projected to pixel space.
    for shelf in shelves:
        corners_local = np.array([
            [-shelf.width_m / 2, -shelf.length_m / 2],
            [shelf.width_m / 2, -shelf.length_m / 2],
            [shelf.width_m / 2, shelf.length_m / 2],
            [-shelf.width_m / 2, shelf.length_m / 2],
        ])
        c = math.cos(math.radians(shelf.rotation_deg))
        s = math.sin(math.radians(shelf.rotation_deg))
        R2 = np.array([[c, -s], [s, c]])
        corners_world = (R2 @ corners_local.T).T + np.array([shelf.x_m, shelf.y_m])

        pixel_corners = []
        for (x, y) in corners_world:
            px = _project_world_to_pixel(np.array([x, y, 0.0]), intrinsics, extrinsics)
            if px is not None:
                pixel_corners.append(px)
        if len(pixel_corners) == 4:
            pts = np.array(pixel_corners, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(out, [pts], True, (255, 200, 0), 2)
            label_px = _project_world_to_pixel(
                np.array([shelf.x_m, shelf.y_m, 0.0]), intrinsics, extrinsics
            )
            if label_px:
                cv2.putText(out, shelf.id, label_px, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)

    # --- Draw robot pose.
    if robot_pose is not None:
        px = _project_world_to_pixel(
            np.array([robot_pose.x_m, robot_pose.y_m, travel_height_m]),
            intrinsics, extrinsics,
        )
        if px is not None:
            cv2.circle(out, px, 8, (0, 255, 255), -1)
            # Heading arrow
            tip_x = robot_pose.x_m + 0.2 * math.cos(math.radians(robot_pose.heading_deg))
            tip_y = robot_pose.y_m + 0.2 * math.sin(math.radians(robot_pose.heading_deg))
            tip_px = _project_world_to_pixel(
                np.array([tip_x, tip_y, travel_height_m]), intrinsics, extrinsics
            )
            if tip_px:
                cv2.arrowedLine(out, px, tip_px, (0, 255, 255), 2, tipLength=0.3)

    # --- Draw drive path segments.
    for wp in waypoints:
        if isinstance(wp, DriveWaypoint):
            from_px = _project_world_to_pixel(
                np.array([wp.from_pose.x_m, wp.from_pose.y_m, travel_height_m]),
                intrinsics, extrinsics,
            )
            to_px = _project_world_to_pixel(
                np.array([wp.to_pose.x_m, wp.to_pose.y_m, travel_height_m]),
                intrinsics, extrinsics,
            )
            if from_px and to_px:
                cv2.line(out, from_px, to_px, (0, 255, 0), 3)

    return out
