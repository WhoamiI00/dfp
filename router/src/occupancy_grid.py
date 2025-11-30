"""
Occupancy grid module.
Builds and manages the occupancy grid representation of the inventory.
"""

import numpy as np
import cv2


class OccupancyGrid:
    """
    Represents the inventory as an occupancy grid.
    
    Grid values:
        0 = FREE (empty cell)
        1 = BLOCK (occupied by object)
        2 = ROBOT (robot position)
        3 = GOAL (goal/destination position)
    """
    
    # Cell type constants
    FREE = 0
    BLOCK = 1
    ROBOT = 2
    GOAL = 3
    
    def __init__(self, n_rows, n_cols):
        """
        Initialize an empty occupancy grid.
        
        Args:
            n_rows: Number of rows
            n_cols: Number of columns
        """
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.grid = np.zeros((n_rows, n_cols), dtype=int)
        self.robot_position = None
        self.goal_position = None
    
    
    def set_cell(self, row, col, value):
        """
        Set the value of a specific cell.
        
        Args:
            row: Row index
            col: Column index
            value: Cell value (FREE, BLOCK, ROBOT, or GOAL)
        """
        if 0 <= row < self.n_rows and 0 <= col < self.n_cols:
            self.grid[row, col] = value
            
            # Track robot position
            if value == self.ROBOT:
                self.robot_position = (row, col)
            # Track goal position
            elif value == self.GOAL:
                self.goal_position = (row, col)
        else:
            print(f"Warning: Invalid cell coordinates ({row}, {col})")
    
    
    def get_cell(self, row, col):
        """
        Get the value of a specific cell.
        
        Args:
            row: Row index
            col: Column index
        
        Returns:
            int: Cell value or None if invalid
        """
        if 0 <= row < self.n_rows and 0 <= col < self.n_cols:
            return self.grid[row, col]
        return None
    
    
    def is_free(self, row, col):
        """
        Check if a cell is free (not occupied).
        
        Args:
            row: Row index
            col: Column index
        
        Returns:
            bool: True if cell is free, False otherwise
        """
        if 0 <= row < self.n_rows and 0 <= col < self.n_cols:
            return self.grid[row, col] == self.FREE
        return False
    
    
    def is_valid(self, row, col):
        """
        Check if coordinates are within grid bounds.
        
        Args:
            row: Row index
            col: Column index
        
        Returns:
            bool: True if coordinates are valid
        """
        return 0 <= row < self.n_rows and 0 <= col < self.n_cols
    
    
    def get_robot_position(self):
        """
        Get the current robot position.
        
        Returns:
            tuple: (row, col) or None if robot not found
        """
        if self.robot_position is not None:
            return self.robot_position
        
        # Search for robot in grid
        robot_cells = np.where(self.grid == self.ROBOT)
        if len(robot_cells[0]) > 0:
            self.robot_position = (robot_cells[0][0], robot_cells[1][0])
            return self.robot_position
        
        return None
    
    
    def get_block_positions(self):
        """
        Get positions of all blocks in the grid.
        
        Returns:
            list: List of (row, col) tuples for block positions
        """
        block_cells = np.where(self.grid == self.BLOCK)
        return list(zip(block_cells[0], block_cells[1]))
    
    
    def count_cells(self):
        """
        Count cells of each type.
        
        Returns:
            dict: Dictionary with counts for 'free', 'block', and 'robot'
        """
        unique, counts = np.unique(self.grid, return_counts=True)
        cell_counts = dict(zip(unique, counts))
        
        return {
            'free': cell_counts.get(self.FREE, 0),
            'block': cell_counts.get(self.BLOCK, 0),
            'robot': cell_counts.get(self.ROBOT, 0)
        }
    
    
    def from_classifications(self, classifications):
        """
        Build occupancy grid from cell classifications.
        
        Args:
            classifications: 2D numpy array of cell classifications
        """
        if classifications.shape != (self.n_rows, self.n_cols):
            raise ValueError("Classifications shape does not match grid dimensions")
        
        self.grid = classifications.copy()
        self.robot_position = self.get_robot_position()
    
    
    def visualize(self, cell_size=50):
        """
        Create a visualization of the occupancy grid.
        
        Args:
            cell_size: Size of each cell in pixels
        
        Returns:
            numpy.ndarray: Image visualization of the grid
        """
        height = self.n_rows * cell_size
        width = self.n_cols * cell_size
        
        # Create blank image
        image = np.ones((height, width, 3), dtype=np.uint8) * 255
        
        for i in range(self.n_rows):
            for j in range(self.n_cols):
                y1 = i * cell_size
                y2 = (i + 1) * cell_size
                x1 = j * cell_size
                x2 = (j + 1) * cell_size
                
                # Color based on cell type
                if self.grid[i, j] == self.ROBOT:
                    color = (0, 0, 255)  # Red for robot
                elif self.grid[i, j] == self.GOAL:
                    color = (0, 255, 0)  # Green for goal
                elif self.grid[i, j] == self.BLOCK:
                    color = (128, 128, 128)  # Gray for block
                else:
                    color = (255, 255, 255)  # White for free
                
                cv2.rectangle(image, (x1, y1), (x2, y2), color, -1)
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 0), 1)
                
                # Add text labels
                text_y = y1 + cell_size // 2 + 5
                text_x = x1 + cell_size // 2 - 10
                if self.grid[i, j] == self.ROBOT:
                    cv2.putText(image, 'R', (text_x, text_y),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                elif self.grid[i, j] == self.GOAL:
                    cv2.putText(image, 'G', (text_x, text_y),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        return image
    
    
    def print_grid(self):
        """
        Print the grid to console for debugging.
        """
        print("\nOccupancy Grid:")
        print("  0 = Free, 1 = Block, 2 = Robot, 3 = Goal")
        print("-" * (self.n_cols * 2 + 1))
        for i in range(self.n_rows):
            row_str = "|"
            for j in range(self.n_cols):
                row_str += str(self.grid[i, j]) + " "
            print(row_str + "|")
        print("-" * (self.n_cols * 2 + 1))
        
        counts = self.count_cells()
        print(f"\nCell counts: Free={counts['free']}, Blocks={counts['block']}, Robot={counts['robot']}")
        
        robot_pos = self.get_robot_position()
        if robot_pos:
            print(f"Robot position: {robot_pos}")
        else:
            print("Robot not found in grid")


def build_occupancy_grid(grid_mapper, classifier):
    """
    Build an occupancy grid from a grid mapper and classifier.
    
    Args:
        grid_mapper: GridMapper instance
        classifier: CellClassifier instance
    
    Returns:
        OccupancyGrid: Built occupancy grid
    """
    print("\nBuilding occupancy grid...")
    
    # Classify all cells
    classifications = classifier.classify_all_cells(grid_mapper)
    
    # Create occupancy grid
    occupancy_grid = OccupancyGrid(grid_mapper.n_rows, grid_mapper.n_cols)
    occupancy_grid.from_classifications(classifications)
    
    print("Occupancy grid built successfully")
    
    return occupancy_grid


def create_occupancy_grid(n_rows, n_cols):
    """
    Factory function to create an empty OccupancyGrid.
    
    Args:
        n_rows: Number of rows
        n_cols: Number of columns
    
    Returns:
        OccupancyGrid: Empty occupancy grid
    """
    return OccupancyGrid(n_rows, n_cols)
