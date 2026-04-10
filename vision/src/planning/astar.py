"""A* pathfinding on a 2D occupancy grid (8-connected)."""
import heapq
import math
import numpy as np
from vision.src.planning.errors import NoPathError


_NEIGHBORS = [
    (-1, -1, math.sqrt(2)),
    (-1, 0, 1.0),
    (-1, 1, math.sqrt(2)),
    (0, -1, 1.0),
    (0, 1, 1.0),
    (1, -1, math.sqrt(2)),
    (1, 0, 1.0),
    (1, 1, math.sqrt(2)),
]


def _heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def a_star(
    grid: np.ndarray,
    start: tuple[int, int],
    goal: tuple[int, int],
) -> list[tuple[int, int]]:
    """Return the shortest 8-connected path from `start` to `goal` as a list
    of (row, col) cells. Raises NoPathError if unreachable.
    """
    rows, cols = grid.shape
    if start == goal:
        return [start]
    if grid[start] == 1:
        raise NoPathError(f"Start cell {start} is blocked")
    if grid[goal] == 1:
        raise NoPathError(f"Goal cell {goal} is blocked")

    open_heap: list[tuple[float, tuple[int, int]]] = [(_heuristic(start, goal), start)]
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {start: 0.0}
    closed: set[tuple[int, int]] = set()

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        if current == goal:
            # Reconstruct.
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path
        closed.add(current)

        for dr, dc, cost in _NEIGHBORS:
            nr, nc = current[0] + dr, current[1] + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            if grid[nr, nc] == 1:
                continue
            neighbor = (nr, nc)
            tentative = g_score[current] + cost
            if tentative < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = tentative
                came_from[neighbor] = current
                f = tentative + _heuristic(neighbor, goal)
                heapq.heappush(open_heap, (f, neighbor))

    raise NoPathError(f"No path from {start} to {goal}")
