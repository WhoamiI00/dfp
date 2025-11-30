"""
Main entry point for the overhead vision-based inventory robot routing system.

This script orchestrates the complete pipeline:
    1. Load image or capture from camera
    2. Detect corners and apply homography
    3. Convert to top-down view
    4. Create grid mapper
    5. Detect robot and blocks
    6. Build occupancy grid
    7. Run A* path planning
    8. Visualize and display results

Usage:
    # Single image mode
    python main.py --image sample.jpg --rows 10 --cols 10 --goal 4 5
    
    # Camera mode
    python main.py --camera 0 --rows 10 --cols 10 --goal 4 5
    
    # Manual corner selection
    python main.py --image sample.jpg --rows 5 --cols 5 --goal 2 3 --corners manual
"""

import argparse
import sys
import cv2
import numpy as np

from camera_stream import CameraStream
from homography import get_top_down_view
from grid_mapper import GridMapper
from detector import CellClassifier
from occupancy_grid import build_occupancy_grid
from planner import find_path, path_to_commands
from utils import draw_grid_on_image, draw_path_on_grid, annotate_grid_cells, resize_for_display


def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Overhead Vision-Based Inventory Robot Routing System'
    )
    
    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--image', type=str, help='Path to input image')
    input_group.add_argument('--camera', type=int, help='Camera index (default: 0)')
    
    # Grid parameters
    parser.add_argument('--rows', type=int, required=True, help='Number of grid rows')
    parser.add_argument('--cols', type=int, required=True, help='Number of grid columns')
    
    # Goal position
    parser.add_argument('--goal', type=int, nargs=2, required=True,
                        metavar=('ROW', 'COL'),
                        help='Goal cell coordinates (row col)')
    
    # Corner detection method
    parser.add_argument('--corners', type=str, default='manual',
                        choices=['manual', 'aruco', 'contour'],
                        help='Corner detection method (default: manual)')
    
    # Robot detection parameters
    parser.add_argument('--robot-color', type=str, default='red',
                        choices=['red', 'blue', 'green', 'yellow'],
                        help='Color of robot marker (default: red)')
    
    # Output parameters
    parser.add_argument('--output', type=str, help='Path to save output image')
    parser.add_argument('--warp-size', type=int, default=800,
                        help='Size of warped top-down view (default: 800)')
    
    # Algorithm choice
    parser.add_argument('--algorithm', type=str, default='astar',
                        choices=['astar', 'bfs'],
                        help='Path planning algorithm (default: astar)')
    
    # Display options
    parser.add_argument('--no-display', action='store_true',
                        help='Do not display visualization windows')
    
    return parser.parse_args()


def main():
    """
    Main execution function.
    """
    # Parse arguments
    args = parse_arguments()
    
    print("=" * 60)
    print("Overhead Vision-Based Inventory Robot Routing System")
    print("=" * 60)
    
    # Step 1: Load image or open camera
    print("\n[1/8] Loading input source...")
    try:
        if args.image:
            camera_stream = CameraStream(args.image)
        else:
            camera_stream = CameraStream(args.camera if args.camera is not None else 0)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Read frame
    success, frame = camera_stream.read_frame()
    if not success or frame is None:
        print("Error: Could not read frame")
        camera_stream.release()
        sys.exit(1)
    
    print(f"Input loaded: {frame.shape[1]}x{frame.shape[0]}")
    
    # Step 2: Detect corners and compute homography
    print("\n[2/8] Detecting corners and computing homography...")
    top_down, homography = get_top_down_view(
        frame,
        width=args.warp_size,
        height=args.warp_size,
        auto_detect=args.corners
    )
    
    if top_down is None:
        print("Error: Failed to create top-down view")
        camera_stream.release()
        sys.exit(1)
    
    print("Top-down view created successfully")
    
    # Step 3: Create grid mapper
    print(f"\n[3/8] Creating {args.rows}x{args.cols} grid mapper...")
    grid_mapper = GridMapper(top_down, args.rows, args.cols)
    
    # Step 4: Initialize detector
    print(f"\n[4/8] Initializing detector (robot color: {args.robot_color})...")
    classifier = CellClassifier(robot_color=args.robot_color)
    
    # Step 5: Build occupancy grid
    print("\n[5/8] Building occupancy grid...")
    occupancy_grid = build_occupancy_grid(grid_mapper, classifier)
    occupancy_grid.print_grid()
    
    # Step 6: Get robot position
    print("\n[6/8] Locating robot...")
    robot_pos = occupancy_grid.get_robot_position()
    
    if robot_pos is None:
        print("Error: Robot not detected in the grid")
        print("Tip: Check robot marker color or adjust detection thresholds")
        camera_stream.release()
        sys.exit(1)
    
    print(f"Robot found at position: {robot_pos}")
    
    # Step 7: Plan path to goal
    goal_pos = tuple(args.goal)
    print(f"\n[7/8] Planning path from {robot_pos} to {goal_pos}...")
    
    path = find_path(robot_pos, goal_pos, occupancy_grid, algorithm=args.algorithm)
    
    if path is None:
        print("\nNo path found! Possible reasons:")
        print("  - Goal position is blocked")
        print("  - No collision-free path exists")
        print("  - Goal is unreachable due to obstacles")
    else:
        print(f"\nPath found successfully!")
        print(f"Path: {path}")
        print(f"Steps: {len(path) - 1}")
        
        # Convert to movement commands
        commands = path_to_commands(path)
        print(f"Commands: {' -> '.join(commands)}")
    
    # Step 8: Visualize results
    print("\n[8/8] Generating visualization...")
    
    # Create visualization with grid
    vis_image = grid_mapper.draw_grid(color=(0, 255, 0), thickness=2)
    
    # Annotate cells
    vis_image = annotate_grid_cells(vis_image, occupancy_grid.grid, args.rows, args.cols)
    
    # Draw path if found
    if path is not None:
        vis_image = draw_path_on_grid(vis_image, path, args.rows, args.cols,
                                      color=(255, 0, 255), thickness=3)
    
    # Add text overlay
    cv2.putText(vis_image, f"Robot: {robot_pos}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.putText(vis_image, f"Goal: {goal_pos}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    if path is not None:
        cv2.putText(vis_image, f"Path length: {len(path) - 1} steps", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
    else:
        cv2.putText(vis_image, "No path found!", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # Save output if requested
    if args.output:
        cv2.imwrite(args.output, vis_image)
        print(f"Output saved to: {args.output}")
    
    # Display results
    if not args.no_display:
        # Resize for display
        display_image = resize_for_display(vis_image, max_width=1000, max_height=800)
        
        cv2.imshow("Inventory Robot Routing - Result", display_image)
        
        # Also show occupancy grid visualization
        grid_vis = occupancy_grid.visualize(cell_size=50)
        grid_vis_resized = resize_for_display(grid_vis, max_width=600, max_height=600)
        cv2.imshow("Occupancy Grid", grid_vis_resized)
        
        print("\nPress any key to exit...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    # Cleanup
    camera_stream.release()
    
    print("\n" + "=" * 60)
    print("Processing complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        cv2.destroyAllWindows()
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        cv2.destroyAllWindows()
        sys.exit(1)
