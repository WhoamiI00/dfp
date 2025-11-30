"""
Example usage script demonstrating the inventory robot routing system.

This script shows how to use the system programmatically (without CLI).
"""

import sys
import cv2
import numpy as np

# Import modules
from camera_stream import CameraStream, load_image
from homography import get_top_down_view, detect_corners_manual
from grid_mapper import GridMapper
from detector import CellClassifier
from occupancy_grid import build_occupancy_grid
from planner import find_path, path_to_commands
from utils import draw_path_on_grid, annotate_grid_cells


def example_1_basic_pipeline():
    """
    Example 1: Basic pipeline with image file.
    """
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Pipeline with Image File")
    print("="*60)
    
    # Configuration
    IMAGE_PATH = "../data/sample_images/test.jpg"
    N_ROWS = 10
    N_COLS = 10
    GOAL = (4, 5)
    ROBOT_COLOR = 'red'
    
    # Step 1: Load image
    print("\n1. Loading image...")
    image = load_image(IMAGE_PATH)
    if image is None:
        print("Error: Could not load image")
        return
    
    # Step 2: Get top-down view (manual corner selection)
    print("\n2. Creating top-down view...")
    top_down, H = get_top_down_view(image, width=800, height=800, auto_detect='manual')
    if top_down is None:
        print("Error: Failed to create top-down view")
        return
    
    # Step 3: Create grid mapper
    print(f"\n3. Creating {N_ROWS}x{N_COLS} grid...")
    grid_mapper = GridMapper(top_down, N_ROWS, N_COLS)
    
    # Step 4: Classify cells
    print(f"\n4. Detecting robot (color: {ROBOT_COLOR}) and blocks...")
    classifier = CellClassifier(robot_color=ROBOT_COLOR)
    
    # Step 5: Build occupancy grid
    print("\n5. Building occupancy grid...")
    occupancy_grid = build_occupancy_grid(grid_mapper, classifier)
    occupancy_grid.print_grid()
    
    # Step 6: Find robot
    robot_pos = occupancy_grid.get_robot_position()
    if robot_pos is None:
        print("\nError: Robot not found!")
        return
    
    print(f"\n6. Robot located at: {robot_pos}")
    
    # Step 7: Plan path
    print(f"\n7. Planning path to goal {GOAL}...")
    path = find_path(robot_pos, GOAL, occupancy_grid, algorithm='astar')
    
    if path:
        print(f"\nPath found: {path}")
        print(f"Length: {len(path) - 1} steps")
        commands = path_to_commands(path)
        print(f"Commands: {' → '.join(commands)}")
    else:
        print("\nNo path found!")
    
    # Step 8: Visualize
    print("\n8. Visualizing results...")
    vis_image = grid_mapper.draw_grid()
    vis_image = annotate_grid_cells(vis_image, occupancy_grid.grid, N_ROWS, N_COLS)
    if path:
        vis_image = draw_path_on_grid(vis_image, path, N_ROWS, N_COLS)
    
    cv2.imshow("Result - Example 1", vis_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def example_2_programmatic_grid():
    """
    Example 2: Create a synthetic occupancy grid and plan path.
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: Programmatic Grid Creation")
    print("="*60)
    
    from occupancy_grid import OccupancyGrid
    
    # Create a 10x10 grid
    grid = OccupancyGrid(10, 10)
    
    # Place robot at (0, 0)
    grid.set_cell(0, 0, grid.ROBOT)
    
    # Place some blocks
    obstacles = [(2, 1), (2, 2), (2, 3), (5, 5), (5, 6), (7, 3), (7, 4)]
    for r, c in obstacles:
        grid.set_cell(r, c, grid.BLOCK)
    
    print("\nSynthetic grid created:")
    grid.print_grid()
    
    # Plan path
    start = (0, 0)
    goal = (9, 9)
    
    print(f"\nPlanning path from {start} to {goal}...")
    path = find_path(start, goal, grid, algorithm='astar')
    
    if path:
        print(f"\nPath: {path}")
        print(f"Length: {len(path) - 1} steps")
        
        # Visualize
        vis = grid.visualize(cell_size=60)
        
        # Draw path on visualization
        for i in range(len(path) - 1):
            r1, c1 = path[i]
            r2, c2 = path[i + 1]
            pt1 = (int((c1 + 0.5) * 60), int((r1 + 0.5) * 60))
            pt2 = (int((c2 + 0.5) * 60), int((r2 + 0.5) * 60))
            cv2.line(vis, pt1, pt2, (255, 0, 255), 3)
        
        cv2.imshow("Result - Example 2", vis)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def example_3_camera_stream():
    """
    Example 3: Using live camera feed.
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: Live Camera Stream")
    print("="*60)
    
    try:
        # Open camera
        print("\nOpening camera...")
        stream = CameraStream(0)
        
        print("Camera opened successfully!")
        print("Press SPACE to capture frame, ESC to exit")
        
        frame = None
        while True:
            success, temp_frame = stream.read_frame()
            if not success:
                break
            
            cv2.imshow("Camera Feed - Press SPACE to capture", temp_frame)
            key = cv2.waitKey(1) & 0xFF
            
            if key == 32:  # SPACE
                frame = temp_frame
                print("\nFrame captured!")
                break
            elif key == 27:  # ESC
                print("\nCancelled")
                break
        
        stream.release()
        cv2.destroyAllWindows()
        
        if frame is not None:
            print("\nProcessing captured frame...")
            # Continue with pipeline (similar to example 1)
            # ... add processing here if needed
        
    except ValueError as e:
        print(f"Error: {e}")


def example_4_detection_parameters():
    """
    Example 4: Customizing detection parameters.
    """
    print("\n" + "="*60)
    print("EXAMPLE 4: Custom Detection Parameters")
    print("="*60)
    
    from detector import RobotDetector, BlockDetector, CellClassifier
    
    # Create custom robot detector (blue marker, higher threshold)
    robot_detector = RobotDetector(color='blue', min_area_ratio=0.08)
    
    # Create custom block detector (stricter criteria)
    block_detector = BlockDetector(min_contour_area=150, min_area_ratio=0.15)
    
    # Create custom classifier
    classifier = CellClassifier(
        robot_color='blue',
        robot_min_ratio=0.08,
        block_min_ratio=0.15
    )
    
    print("\nCustom classifier created:")
    print(f"  Robot color: blue")
    print(f"  Robot threshold: 8%")
    print(f"  Block threshold: 15%")
    print("\nUse this classifier in build_occupancy_grid()")


def example_5_grid_visualization():
    """
    Example 5: Various grid visualization techniques.
    """
    print("\n" + "="*60)
    print("EXAMPLE 5: Grid Visualization Techniques")
    print("="*60)
    
    from occupancy_grid import OccupancyGrid
    
    # Create sample grid
    grid = OccupancyGrid(8, 8)
    grid.set_cell(1, 1, grid.ROBOT)
    grid.set_cell(3, 3, grid.BLOCK)
    grid.set_cell(3, 4, grid.BLOCK)
    grid.set_cell(5, 2, grid.BLOCK)
    
    print("\n1. Console visualization:")
    grid.print_grid()
    
    print("\n2. Image visualization:")
    vis = grid.visualize(cell_size=80)
    cv2.imshow("Grid Visualization", vis)
    
    print("\n3. Statistics:")
    counts = grid.count_cells()
    print(f"  Free cells: {counts['free']}")
    print(f"  Blocks: {counts['block']}")
    print(f"  Robot: {counts['robot']}")
    
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def run_all_examples():
    """
    Run all examples interactively.
    """
    examples = [
        ("Basic Pipeline", example_1_basic_pipeline),
        ("Programmatic Grid", example_2_programmatic_grid),
        ("Camera Stream", example_3_camera_stream),
        ("Custom Detection", example_4_detection_parameters),
        ("Grid Visualization", example_5_grid_visualization),
    ]
    
    print("\n" + "="*60)
    print("INVENTORY ROBOT ROUTING - EXAMPLES")
    print("="*60)
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    print(f"  {len(examples) + 1}. Run all")
    print("  0. Exit")
    
    choice = input("\nSelect example (0-6): ").strip()
    
    try:
        choice = int(choice)
        if choice == 0:
            print("Exiting...")
            return
        elif choice == len(examples) + 1:
            for name, func in examples:
                print(f"\n\nRunning: {name}")
                input("Press ENTER to continue...")
                func()
        elif 1 <= choice <= len(examples):
            examples[choice - 1][1]()
        else:
            print("Invalid choice")
    except ValueError:
        print("Invalid input")
    except KeyboardInterrupt:
        print("\n\nInterrupted")


if __name__ == "__main__":
    try:
        # Check if specific example requested
        if len(sys.argv) > 1:
            example_num = int(sys.argv[1])
            examples = [
                example_1_basic_pipeline,
                example_2_programmatic_grid,
                example_3_camera_stream,
                example_4_detection_parameters,
                example_5_grid_visualization,
            ]
            if 1 <= example_num <= len(examples):
                examples[example_num - 1]()
            else:
                print(f"Invalid example number. Choose 1-{len(examples)}")
        else:
            run_all_examples()
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
