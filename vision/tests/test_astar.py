"""A* search tests."""
import numpy as np
import pytest
from vision.src.planning.astar import a_star
from vision.src.planning.errors import NoPathError


def test_astar_direct_line_empty_grid():
    grid = np.zeros((10, 10), dtype=np.int8)
    path = a_star(grid, (0, 0), (0, 9))
    assert path[0] == (0, 0)
    assert path[-1] == (0, 9)
    # Straight line should produce 10 cells.
    assert len(path) == 10


def test_astar_diagonal():
    grid = np.zeros((10, 10), dtype=np.int8)
    path = a_star(grid, (0, 0), (5, 5))
    assert path[0] == (0, 0)
    assert path[-1] == (5, 5)
    assert len(path) == 6


def test_astar_routes_around_obstacle():
    grid = np.zeros((10, 10), dtype=np.int8)
    grid[0:8, 5] = 1  # vertical wall with a gap at rows 8-9
    path = a_star(grid, (0, 0), (0, 9))
    assert path[0] == (0, 0)
    assert path[-1] == (0, 9)
    assert all(grid[r, c] == 0 for r, c in path)


def test_astar_unreachable_raises():
    grid = np.zeros((10, 10), dtype=np.int8)
    grid[:, 5] = 1  # full vertical wall
    with pytest.raises(NoPathError):
        a_star(grid, (0, 0), (0, 9))


def test_astar_start_is_goal():
    grid = np.zeros((10, 10), dtype=np.int8)
    path = a_star(grid, (3, 3), (3, 3))
    assert path == [(3, 3)]
