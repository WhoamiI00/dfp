"""
Utility functions for the overhead vision-based inventory robot routing system.
Provides common helper functions used across the project.
"""

import cv2
import numpy as np


def draw_grid_on_image(image, n_rows, n_cols, color=(0, 255, 0), thickness=1):
    """
    Draw grid lines on an image.
    
    Args:
        image: Input image (numpy array)
        n_rows: Number of rows in the grid
        n_cols: Number of columns in the grid
        color: Color of the grid lines (B, G, R)
        thickness: Thickness of the grid lines
    
    Returns:
        Image with grid lines drawn
    """
    h, w = image.shape[:2]
    cell_h = h // n_rows
    cell_w = w // n_cols
    
    result = image.copy()
    
    # Draw horizontal lines
    for i in range(1, n_rows):
        y = i * cell_h
        cv2.line(result, (0, y), (w, y), color, thickness)
    
    # Draw vertical lines
    for j in range(1, n_cols):
        x = j * cell_w
        cv2.line(result, (x, 0), (x, h), color, thickness)
    
    return result


def draw_path_on_grid(image, path, n_rows, n_cols, color=(255, 0, 255), thickness=3):
    """
    Draw the path on the grid image.
    
    Args:
        image: Input image (numpy array)
        path: List of (row, col) tuples representing the path
        n_rows: Number of rows in the grid
        n_cols: Number of columns in the grid
        color: Color of the path line (B, G, R)
        thickness: Thickness of the path line
    
    Returns:
        Image with path drawn
    """
    if not path or len(path) < 2:
        return image
    
    h, w = image.shape[:2]
    cell_h = h // n_rows
    cell_w = w // n_cols
    
    result = image.copy()
    
    # Draw lines between consecutive cells in the path
    for i in range(len(path) - 1):
        r1, c1 = path[i]
        r2, c2 = path[i + 1]
        
        # Get center of each cell
        y1 = int((r1 + 0.5) * cell_h)
        x1 = int((c1 + 0.5) * cell_w)
        y2 = int((r2 + 0.5) * cell_h)
        x2 = int((c2 + 0.5) * cell_w)
        
        cv2.line(result, (x1, y1), (x2, y2), color, thickness)
        cv2.circle(result, (x1, y1), 5, (0, 255, 0), -1)
    
    # Draw final point
    r_final, c_final = path[-1]
    y_final = int((r_final + 0.5) * cell_h)
    x_final = int((c_final + 0.5) * cell_w)
    cv2.circle(result, (x_final, y_final), 5, (0, 0, 255), -1)
    
    return result


def annotate_grid_cells(image, grid, n_rows, n_cols):
    """
    Annotate grid cells with their status (Robot, Block, Empty).
    
    Args:
        image: Input image (numpy array)
        grid: Occupancy grid (numpy array)
        n_rows: Number of rows in the grid
        n_cols: Number of columns in the grid
    
    Returns:
        Image with annotations
    """
    h, w = image.shape[:2]
    cell_h = h // n_rows
    cell_w = w // n_cols
    
    result = image.copy()
    
    for i in range(n_rows):
        for j in range(n_cols):
            y_center = int((i + 0.5) * cell_h)
            x_center = int((j + 0.5) * cell_w)
            
            if grid[i, j] == 2:  # Robot
                cv2.putText(result, 'R', (x_center - 10, y_center + 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            elif grid[i, j] == 1:  # Block
                cv2.putText(result, 'B', (x_center - 10, y_center + 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
    
    return result


def resize_for_display(image, max_width=800, max_height=600):
    """
    Resize image to fit within display constraints while maintaining aspect ratio.
    
    Args:
        image: Input image
        max_width: Maximum width for display
        max_height: Maximum height for display
    
    Returns:
        Resized image
    """
    h, w = image.shape[:2]
    
    # Calculate scaling factor
    scale_w = max_width / w
    scale_h = max_height / h
    scale = min(scale_w, scale_h, 1.0)  # Don't upscale
    
    if scale < 1.0:
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    return image


def validate_coordinates(coords, max_rows, max_cols):
    """
    Validate that coordinates are within grid bounds.
    
    Args:
        coords: Tuple of (row, col)
        max_rows: Maximum number of rows
        max_cols: Maximum number of columns
    
    Returns:
        True if coordinates are valid, False otherwise
    """
    row, col = coords
    return 0 <= row < max_rows and 0 <= col < max_cols
