"""
Path planning module.
Implements A* algorithm for finding collision-free paths in the occupancy grid.
"""

import heapq
import numpy as np
from collections import defaultdict


def heuristic(a, b):
    """
    Manhattan distance heuristic for A*.
    
    Args:
        a: Tuple (row, col) for first position
        b: Tuple (row, col) for second position
    
    Returns:
        int: Manhattan distance between positions
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def get_neighbors(position, n_rows, n_cols):
    """
    Get valid neighboring cells (4-connected grid).
    
    Args:
        position: Current position (row, col)
        n_rows: Number of rows in grid
        n_cols: Number of columns in grid
    
    Returns:
        list: List of valid neighbor positions
    """
    row, col = position
    neighbors = []
    
    # 4-connected grid: Up, Down, Left, Right
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    
    for dr, dc in directions:
        new_row, new_col = row + dr, col + dc
        
        # Check bounds
        if 0 <= new_row < n_rows and 0 <= new_col < n_cols:
            neighbors.append((new_row, new_col))
    
    return neighbors


def reconstruct_path(came_from, current):
    """
    Reconstruct path from start to goal using came_from dictionary.
    
    Args:
        came_from: Dictionary mapping position -> previous position
        current: Goal position
    
    Returns:
        list: List of positions from start to goal
    """
    path = [current]
    
    while current in came_from:
        current = came_from[current]
        path.append(current)
    
    path.reverse()
    return path


def astar(start, goal, occupancy_grid):
    """
    A* path planning algorithm.
    
    Args:
        start: Start position (row, col)
        goal: Goal position (row, col)
        occupancy_grid: OccupancyGrid instance
    
    Returns:
        list: Path as list of (row, col) positions, or None if no path found
    """
    # Validate start and goal
    if not occupancy_grid.is_valid(start[0], start[1]):
        print(f"Error: Invalid start position {start}")
        return None
    
    if not occupancy_grid.is_valid(goal[0], goal[1]):
        print(f"Error: Invalid goal position {goal}")
        return None
    
    # Check if goal is occupied by a block
    if occupancy_grid.get_cell(goal[0], goal[1]) == occupancy_grid.BLOCK:
        print(f"Error: Goal position {goal} is blocked")
        return None
    
    # If start == goal
    if start == goal:
        return [start]
    
    # Initialize data structures
    open_set = []
    heapq.heappush(open_set, (0, start))
    
    came_from = {}
    g_score = defaultdict(lambda: float('inf'))
    g_score[start] = 0
    
    f_score = defaultdict(lambda: float('inf'))
    f_score[start] = heuristic(start, goal)
    
    visited = set()
    
    print(f"\nA* pathfinding from {start} to {goal}...")
    
    while open_set:
        _, current = heapq.heappop(open_set)
        
        # Skip if already visited
        if current in visited:
            continue
        
        visited.add(current)
        
        # Check if we reached the goal
        if current == goal:
            path = reconstruct_path(came_from, current)
            print(f"Path found! Length: {len(path)} steps")
            return path
        
        # Explore neighbors
        neighbors = get_neighbors(current, occupancy_grid.n_rows, occupancy_grid.n_cols)
        
        for neighbor in neighbors:
            # Skip occupied cells (blocks)
            if occupancy_grid.get_cell(neighbor[0], neighbor[1]) == occupancy_grid.BLOCK:
                continue
            
            # Calculate tentative g_score
            tentative_g_score = g_score[current] + 1  # Cost of 1 per step
            
            # If this path is better
            if tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                
                # Add to open set if not visited
                if neighbor not in visited:
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
    
    # No path found
    print("No path found to goal")
    return None


def bfs(start, goal, occupancy_grid):
    """
    Breadth-First Search for path planning (alternative to A*).
    
    Args:
        start: Start position (row, col)
        goal: Goal position (row, col)
        occupancy_grid: OccupancyGrid instance
    
    Returns:
        list: Path as list of (row, col) positions, or None if no path found
    """
    # Validate start and goal
    if not occupancy_grid.is_valid(start[0], start[1]):
        print(f"Error: Invalid start position {start}")
        return None
    
    if not occupancy_grid.is_valid(goal[0], goal[1]):
        print(f"Error: Invalid goal position {goal}")
        return None
    
    if start == goal:
        return [start]
    
    # BFS queue
    queue = [start]
    visited = {start}
    came_from = {}
    
    print(f"\nBFS pathfinding from {start} to {goal}...")
    
    while queue:
        current = queue.pop(0)
        
        # Check if we reached the goal
        if current == goal:
            path = reconstruct_path(came_from, current)
            print(f"Path found! Length: {len(path)} steps")
            return path
        
        # Explore neighbors
        neighbors = get_neighbors(current, occupancy_grid.n_rows, occupancy_grid.n_cols)
        
        for neighbor in neighbors:
            # Skip if visited or occupied
            if neighbor in visited:
                continue
            
            if occupancy_grid.get_cell(neighbor[0], neighbor[1]) == occupancy_grid.BLOCK:
                continue
            
            visited.add(neighbor)
            came_from[neighbor] = current
            queue.append(neighbor)
    
    # No path found
    print("No path found to goal")
    return None


def find_path(start, goal, occupancy_grid, algorithm='astar'):
    """
    Find a path from start to goal using the specified algorithm.
    
    Args:
        start: Start position (row, col)
        goal: Goal position (row, col)
        occupancy_grid: OccupancyGrid instance
        algorithm: 'astar' or 'bfs'
    
    Returns:
        list: Path as list of positions, or None if no path found
    """
    if algorithm.lower() == 'bfs':
        return bfs(start, goal, occupancy_grid)
    else:
        return astar(start, goal, occupancy_grid)


def path_to_commands(path):
    """
    Convert a path (list of grid positions) to movement commands.
    
    Args:
        path: List of (row, col) positions
    
    Returns:
        list: List of movement commands ('UP', 'DOWN', 'LEFT', 'RIGHT')
    """
    if not path or len(path) < 2:
        return []
    
    commands = []
    
    for i in range(len(path) - 1):
        current = path[i]
        next_pos = path[i + 1]
        
        dr = next_pos[0] - current[0]
        dc = next_pos[1] - current[1]
        
        if dr == -1:
            commands.append('UP')
        elif dr == 1:
            commands.append('DOWN')
        elif dc == -1:
            commands.append('LEFT')
        elif dc == 1:
            commands.append('RIGHT')
    
    return commands
