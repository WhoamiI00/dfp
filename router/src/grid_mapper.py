"""
Grid mapping module.
Converts the warped top-down image into an N x M grid of cells.
"""

import cv2
import numpy as np


class GridMapper:
    """
    Maps a top-down image to an N x M grid and provides access to individual cells.
    """
    
    def __init__(self, image, n_rows, n_cols):
        """
        Initialize the grid mapper.
        
        Args:
            image: Top-down warped image
            n_rows: Number of rows in the grid
            n_cols: Number of columns in the grid
        """
        self.image = image
        self.n_rows = n_rows
        self.n_cols = n_cols
        
        self.height, self.width = image.shape[:2]
        
        # Calculate cell dimensions
        self.cell_height = self.height // n_rows
        self.cell_width = self.width // n_cols
        
        print(f"Grid initialized: {n_rows}x{n_cols} grid")
        print(f"Image size: {self.width}x{self.height}")
        print(f"Cell size: {self.cell_width}x{self.cell_height}")
    
    
    def get_cell(self, row, col):
        """
        Extract a specific cell from the grid.
        
        Args:
            row: Row index (0 to n_rows-1)
            col: Column index (0 to n_cols-1)
        
        Returns:
            numpy.ndarray: Image patch for the specified cell or None if invalid
        """
        if row < 0 or row >= self.n_rows or col < 0 or col >= self.n_cols:
            print(f"Warning: Invalid cell coordinates ({row}, {col})")
            return None
        
        # Calculate pixel coordinates
        y1 = row * self.cell_height
        y2 = (row + 1) * self.cell_height
        x1 = col * self.cell_width
        x2 = (col + 1) * self.cell_width
        
        # Extract cell
        cell_image = self.image[y1:y2, x1:x2]
        
        return cell_image
    
    
    def get_all_cells(self):
        """
        Extract all cells from the grid.
        
        Returns:
            list: 2D list of cell images [row][col]
        """
        cells = []
        
        for i in range(self.n_rows):
            row_cells = []
            for j in range(self.n_cols):
                cell = self.get_cell(i, j)
                row_cells.append(cell)
            cells.append(row_cells)
        
        return cells
    
    
    def get_cell_center(self, row, col):
        """
        Get the pixel coordinates of the center of a cell.
        
        Args:
            row: Row index
            col: Column index
        
        Returns:
            tuple: (x, y) pixel coordinates of cell center
        """
        y = int((row + 0.5) * self.cell_height)
        x = int((col + 0.5) * self.cell_width)
        
        return (x, y)
    
    
    def pixel_to_grid(self, x, y):
        """
        Convert pixel coordinates to grid cell coordinates.
        
        Args:
            x: Pixel x-coordinate
            y: Pixel y-coordinate
        
        Returns:
            tuple: (row, col) grid coordinates
        """
        col = int(x // self.cell_width)
        row = int(y // self.cell_height)
        
        # Clamp to valid range
        row = max(0, min(row, self.n_rows - 1))
        col = max(0, min(col, self.n_cols - 1))
        
        return (row, col)
    
    
    def grid_to_pixel(self, row, col):
        """
        Convert grid cell coordinates to pixel coordinates (center of cell).
        
        Args:
            row: Row index
            col: Column index
        
        Returns:
            tuple: (x, y) pixel coordinates
        """
        return self.get_cell_center(row, col)
    
    
    def draw_grid(self, color=(0, 255, 0), thickness=1):
        """
        Draw grid lines on the image.
        
        Args:
            color: Color of grid lines (B, G, R)
            thickness: Thickness of lines
        
        Returns:
            numpy.ndarray: Image with grid lines
        """
        result = self.image.copy()
        
        # Draw horizontal lines
        for i in range(1, self.n_rows):
            y = i * self.cell_height
            cv2.line(result, (0, y), (self.width, y), color, thickness)
        
        # Draw vertical lines
        for j in range(1, self.n_cols):
            x = j * self.cell_width
            cv2.line(result, (x, 0), (x, self.height), color, thickness)
        
        return result
    
    
    def visualize_grid_with_indices(self):
        """
        Visualize the grid with cell indices for debugging.
        
        Returns:
            numpy.ndarray: Image with grid and cell indices
        """
        result = self.draw_grid()
        
        # Add cell indices
        for i in range(self.n_rows):
            for j in range(self.n_cols):
                x, y = self.get_cell_center(i, j)
                text = f"({i},{j})"
                
                # Calculate text size for background
                (text_w, text_h), baseline = cv2.getTextSize(
                    text, cv2.FONT_HERSHEY_SIMPLEX, 0.3, 1
                )
                
                # Draw background rectangle
                cv2.rectangle(
                    result,
                    (x - text_w // 2 - 2, y - text_h // 2 - 2),
                    (x + text_w // 2 + 2, y + text_h // 2 + 2),
                    (255, 255, 255),
                    -1
                )
                
                # Draw text
                cv2.putText(
                    result, text,
                    (x - text_w // 2, y + text_h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1
                )
        
        return result


def create_grid_mapper(image, n_rows, n_cols):
    """
    Factory function to create a GridMapper instance.
    
    Args:
        image: Top-down warped image
        n_rows: Number of rows
        n_cols: Number of columns
    
    Returns:
        GridMapper: Initialized grid mapper
    """
    return GridMapper(image, n_rows, n_cols)
