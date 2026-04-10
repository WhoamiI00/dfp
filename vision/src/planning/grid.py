"""Occupancy grid construction."""
import math
from collections import deque
import numpy as np
from vision.src.models import Settings, Shelf
from vision.src.planning.errors import ApproachPointBlockedError


def world_to_cell(xy_m: tuple[float, float], settings: Settings) -> tuple[int, int]:
    """World (x, y) in meters -> (row, col). Raises ValueError if out of bounds.

    Points exactly on the far boundary are clamped to the last cell so that
    detection noise at the workspace edge does not error out.
    """
    x, y = xy_m
    ws = settings.workspace
    if not (0 <= x <= ws.width_m and 0 <= y <= ws.height_m):
        raise ValueError(f"Point ({x}, {y}) outside workspace")
    cols = int(round(ws.width_m / ws.cell_size_m))
    rows = int(round(ws.height_m / ws.cell_size_m))
    col = min(int(x / ws.cell_size_m), cols - 1)
    row = min(int(y / ws.cell_size_m), rows - 1)
    return row, col


def cell_to_world(rc: tuple[int, int], settings: Settings) -> tuple[float, float]:
    """(row, col) -> world (x, y) at cell center."""
    row, col = rc
    s = settings.workspace.cell_size_m
    return col * s + s / 2, row * s + s / 2


def snap_to_free_cell(
    grid: np.ndarray,
    cell: tuple[int, int],
    max_radius_cells: int = 8,
) -> tuple[int, int] | None:
    """Return the nearest unoccupied cell to `cell` via 8-connected BFS.

    If `cell` itself is free (or out of bounds but near a free cell), returns
    it unchanged. Returns None if no free cell exists within `max_radius_cells`
    steps. Used to recover a valid planning anchor when the detected robot
    pose happens to fall inside an inflated obstacle zone — a common failure
    mode when extrinsic calibration is approximate or the robot is physically
    close to a shelf edge.
    """
    rows, cols = grid.shape
    r0, c0 = cell
    in_bounds = 0 <= r0 < rows and 0 <= c0 < cols
    if in_bounds and grid[r0, c0] == 0:
        return cell

    visited: set[tuple[int, int]] = {(r0, c0)}
    q: deque[tuple[int, int, int]] = deque([(r0, c0, 0)])
    neighbours = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1),
    ]
    while q:
        r, c, d = q.popleft()
        if d > max_radius_cells:
            continue
        if 0 <= r < rows and 0 <= c < cols and grid[r, c] == 0:
            return (r, c)
        for dr, dc in neighbours:
            nr, nc = r + dr, c + dc
            if (nr, nc) in visited:
                continue
            visited.add((nr, nc))
            q.append((nr, nc, d + 1))
    return None


def _rasterize_shelf(shelf: Shelf, grid: np.ndarray, settings: Settings) -> None:
    """Mark grid cells whose center lies inside the (rotated) shelf rectangle."""
    s = settings.workspace.cell_size_m
    cos = math.cos(math.radians(shelf.rotation_deg))
    sin = math.sin(math.radians(shelf.rotation_deg))
    half_w = shelf.width_m / 2
    half_l = shelf.length_m / 2

    rows, cols = grid.shape
    for row in range(rows):
        for col in range(cols):
            cx = col * s + s / 2
            cy = row * s + s / 2
            dx = cx - shelf.x_m
            dy = cy - shelf.y_m
            # Rotate into shelf local frame.
            local_x = cos * dx + sin * dy
            local_y = -sin * dx + cos * dy
            if -half_w <= local_x <= half_w and -half_l <= local_y <= half_l:
                grid[row, col] = 1


def _inflate(grid: np.ndarray, radius_cells: int) -> np.ndarray:
    """Grow obstacles by `radius_cells` using a square kernel."""
    if radius_cells <= 0:
        return grid
    rows, cols = grid.shape
    out = grid.copy()
    for row in range(rows):
        for col in range(cols):
            if grid[row, col] == 1:
                r0 = max(0, row - radius_cells)
                r1 = min(rows, row + radius_cells + 1)
                c0 = max(0, col - radius_cells)
                c1 = min(cols, col + radius_cells + 1)
                out[r0:r1, c0:c1] = 1
    return out


def build_occupancy_grid(shelves: list[Shelf], settings: Settings) -> np.ndarray:
    """Build an int8 occupancy grid from the shelf list.

    Grid cells are 0 for free, 1 for obstacle. Obstacles are shelves rasterized
    into the grid and then inflated by planner.obstacle_inflation_m, rounded
    up to the nearest whole cell so small safety margins never silently round
    to zero.
    """
    ws = settings.workspace
    rows = int(round(ws.height_m / ws.cell_size_m))
    cols = int(round(ws.width_m / ws.cell_size_m))
    grid = np.zeros((rows, cols), dtype=np.int8)

    for shelf in shelves:
        _rasterize_shelf(shelf, grid, settings)

    radius_cells = math.ceil(settings.planner.obstacle_inflation_m / ws.cell_size_m)
    inflated = _inflate(grid, radius_cells)

    for shelf in shelves:
        try:
            row, col = world_to_cell((shelf.approach_point.x_m, shelf.approach_point.y_m), settings)
        except ValueError:
            raise ApproachPointBlockedError(shelf.id)
        if inflated[row, col] == 1:
            raise ApproachPointBlockedError(shelf.id)

    return inflated
