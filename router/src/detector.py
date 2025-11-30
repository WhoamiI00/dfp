"""
Object detection module.
Detects robot (colored marker) and blocks (objects) in grid cells.
Uses classical computer vision techniques (color thresholding, contour detection).
"""

import cv2
import numpy as np


class RobotDetector:
    """
    Detects robot based on colored marker (default: red).
    """
    
    def __init__(self, color='red', min_area_ratio=0.05):
        """
        Initialize robot detector.
        
        Args:
            color: Color of robot marker ('red', 'blue', 'green')
            min_area_ratio: Minimum ratio of colored pixels to consider as robot
        """
        self.color = color.lower()
        self.min_area_ratio = min_area_ratio
        
        # Define HSV color ranges
        self.color_ranges = {
            'red': [
                (np.array([0, 100, 100]), np.array([10, 255, 255])),
                (np.array([160, 100, 100]), np.array([179, 255, 255]))
            ],
            'blue': [
                (np.array([100, 100, 100]), np.array([130, 255, 255]))
            ],
            'green': [
                (np.array([40, 50, 50]), np.array([80, 255, 255]))
            ],
            'yellow': [
                (np.array([20, 100, 100]), np.array([30, 255, 255]))
            ],
            'orange': [
                (np.array([10, 100, 100]), np.array([25, 255, 255]))
            ],
            'purple': [
                (np.array([130, 50, 50]), np.array([160, 255, 255]))
            ],
            'pink': [
                (np.array([140, 50, 50]), np.array([170, 255, 255]))
            ],
            'cyan': [
                (np.array([80, 100, 100]), np.array([100, 255, 255]))
            ],
            'white': [
                (np.array([0, 0, 200]), np.array([180, 30, 255]))
            ],
            'black': [
                (np.array([0, 0, 0]), np.array([180, 255, 50]))
            ]
        }
        
        if self.color not in self.color_ranges:
            print(f"Warning: Unknown color '{color}', defaulting to red")
            self.color = 'red'
    
    
    def detect(self, cell_image):
        """
        Detect if the cell contains the robot marker.
        
        Args:
            cell_image: Image of the grid cell
        
        Returns:
            bool: True if robot detected, False otherwise
        """
        if cell_image is None or cell_image.size == 0:
            return False
        
        # Convert to HSV
        hsv = cv2.cvtColor(cell_image, cv2.COLOR_BGR2HSV)
        
        # Create mask for the specified color
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        
        for lower, upper in self.color_ranges[self.color]:
            mask_temp = cv2.inRange(hsv, lower, upper)
            mask = cv2.bitwise_or(mask, mask_temp)
        
        # Calculate ratio of colored pixels
        total_pixels = cell_image.shape[0] * cell_image.shape[1]
        colored_pixels = cv2.countNonZero(mask)
        ratio = colored_pixels / total_pixels
        
        # Robot detected if ratio exceeds threshold
        return ratio >= self.min_area_ratio


class BlockDetector:
    """
    Detects blocks/objects in grid cells using background subtraction and contour detection.
    """
    
    def __init__(self, background_color=None, min_contour_area=100, min_area_ratio=0.1):
        """
        Initialize block detector.
        
        Args:
            background_color: Expected background color in BGR (optional)
            min_contour_area: Minimum contour area to consider as a block
            min_area_ratio: Minimum ratio of non-background pixels to consider as block
        """
        self.background_color = background_color
        self.min_contour_area = min_contour_area
        self.min_area_ratio = min_area_ratio
    
    
    def detect(self, cell_image):
        """
        Detect if the cell contains a block/object.
        
        Args:
            cell_image: Image of the grid cell
        
        Returns:
            bool: True if block detected, False otherwise
        """
        if cell_image is None or cell_image.size == 0:
            return False
        
        # Method 1: Edge detection and contour area
        gray = cv2.cvtColor(cell_image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Edge detection
        edges = cv2.Canny(blurred, 30, 100)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Check if there are significant contours
        total_contour_area = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_contour_area:
                total_contour_area += area
        
        cell_area = cell_image.shape[0] * cell_image.shape[1]
        contour_ratio = total_contour_area / cell_area
        
        # Method 2: Color variance (blocks usually have different texture than floor)
        std_dev = np.std(gray)
        
        # Block detected if significant contours found OR high variance
        return contour_ratio >= self.min_area_ratio or std_dev > 30
    
    
    def detect_with_background(self, cell_image, background_sample):
        """
        Detect block by comparing with background sample.
        
        Args:
            cell_image: Image of the grid cell
            background_sample: Sample image of empty background/floor
        
        Returns:
            bool: True if block detected, False otherwise
        """
        if cell_image is None or background_sample is None:
            return self.detect(cell_image)
        
        # Resize background sample to match cell size
        bg_resized = cv2.resize(background_sample, (cell_image.shape[1], cell_image.shape[0]))
        
        # Compute absolute difference
        diff = cv2.absdiff(cell_image, bg_resized)
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        
        # Threshold the difference
        _, thresh = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)
        
        # Calculate ratio of different pixels
        total_pixels = thresh.shape[0] * thresh.shape[1]
        diff_pixels = cv2.countNonZero(thresh)
        ratio = diff_pixels / total_pixels
        
        return ratio >= self.min_area_ratio


class CellClassifier:
    """
    Classifies grid cells as ROBOT, BLOCK, or EMPTY.
    """
    
    # Cell type constants
    EMPTY = 0
    BLOCK = 1
    ROBOT = 2
    
    def __init__(self, robot_color='red', robot_min_ratio=0.05, block_min_ratio=0.1):
        """
        Initialize cell classifier.
        
        Args:
            robot_color: Color of robot marker
            robot_min_ratio: Minimum color ratio for robot detection
            block_min_ratio: Minimum area ratio for block detection
        """
        self.robot_detector = RobotDetector(color=robot_color, min_area_ratio=robot_min_ratio)
        self.block_detector = BlockDetector(min_area_ratio=block_min_ratio)
    
    
    def classify_cell(self, cell_image):
        """
        Classify a single grid cell.
        
        Args:
            cell_image: Image of the grid cell
        
        Returns:
            int: EMPTY (0), BLOCK (1), or ROBOT (2)
        """
        if cell_image is None or cell_image.size == 0:
            return self.EMPTY
        
        # Check for robot first (higher priority)
        if self.robot_detector.detect(cell_image):
            return self.ROBOT
        
        # Check for block
        if self.block_detector.detect(cell_image):
            return self.BLOCK
        
        # Default to empty
        return self.EMPTY
    
    
    def classify_all_cells(self, grid_mapper):
        """
        Classify all cells in a grid.
        
        Args:
            grid_mapper: GridMapper instance
        
        Returns:
            numpy.ndarray: 2D array of cell classifications
        """
        classifications = np.zeros((grid_mapper.n_rows, grid_mapper.n_cols), dtype=int)
        
        for i in range(grid_mapper.n_rows):
            for j in range(grid_mapper.n_cols):
                cell_image = grid_mapper.get_cell(i, j)
                classifications[i, j] = self.classify_cell(cell_image)
        
        return classifications


def create_detector(robot_color='red', robot_threshold=0.05, block_threshold=0.1):
    """
    Factory function to create a CellClassifier.
    
    Args:
        robot_color: Color of the robot marker
        robot_threshold: Minimum ratio for robot detection
        block_threshold: Minimum ratio for block detection
    
    Returns:
        CellClassifier: Initialized classifier
    """
    return CellClassifier(
        robot_color=robot_color,
        robot_min_ratio=robot_threshold,
        block_min_ratio=block_threshold
    )
