# Overhead Vision–Based Inventory Robot Routing

Complete implementation of an overhead vision system for robot routing in inventory grids.

## Project Overview

This system uses a ceiling-mounted camera to detect a robot and objects in an inventory grid, then computes collision-free paths using A* path planning.

## Features

- ✅ Top-down perspective correction using homography
- ✅ N×M grid mapping with configurable dimensions
- ✅ Classical CV-based robot detection (colored marker)
- ✅ Block/object detection using edge detection and contours
- ✅ Occupancy grid representation
- ✅ A* path planning with Manhattan heuristic
- ✅ BFS alternative path planning
- ✅ Visualization and path display
- ✅ Support for both static images and live camera feed

## Installation

### Requirements

- Python 3.7+
- OpenCV
- NumPy

### Setup

```bash
# Clone or download the repository
cd router

# Install dependencies
pip install -r requirements.txt
```

## Project Structure

```
router/
├── README.md
├── INSTRUCTIONS.md
├── requirements.txt
├── src/
│   ├── main.py              # Entry point
│   ├── camera_stream.py     # Camera/image input handling
│   ├── homography.py        # Perspective correction
│   ├── grid_mapper.py       # Grid cell mapping
│   ├── detector.py          # Robot and block detection
│   ├── occupancy_grid.py    # Occupancy grid representation
│   ├── planner.py           # A* path planning
│   └── utils.py             # Helper functions
└── data/
    └── sample_images/       # Test images (place your images here)
```

## Usage

### Basic Usage with Image

```bash
cd src
python main.py --image ../data/sample_images/test.jpg --rows 10 --cols 10 --goal 4 5
```

### Using Camera Feed

```bash
python main.py --camera 0 --rows 5 --cols 5 --goal 2 3
```

### Command-Line Arguments

| Argument | Required | Description | Default |
|----------|----------|-------------|---------|
| `--image PATH` | Yes* | Path to input image | - |
| `--camera INDEX` | Yes* | Camera index (0, 1, etc.) | - |
| `--rows N` | Yes | Number of grid rows | - |
| `--cols M` | Yes | Number of grid columns | - |
| `--goal ROW COL` | Yes | Target cell coordinates | - |
| `--corners METHOD` | No | Corner detection: manual/aruco/contour | manual |
| `--robot-color COLOR` | No | Robot marker color: red/blue/green/yellow | red |
| `--algorithm ALG` | No | Path planner: astar/bfs | astar |
| `--warp-size SIZE` | No | Warped image size in pixels | 800 |
| `--output PATH` | No | Save output image | - |
| `--no-display` | No | Don't show windows | False |

\* Either `--image` or `--camera` must be provided

### Examples

#### Example 1: 5×5 Grid with Red Robot

```bash
python main.py --image test.jpg --rows 5 --cols 5 --goal 2 3 --robot-color red
```

#### Example 2: 10×10 Grid with Blue Robot, Save Output

```bash
python main.py --image inventory.jpg --rows 10 --cols 10 --goal 7 8 --robot-color blue --output result.jpg
```

#### Example 3: Live Camera with BFS Algorithm

```bash
python main.py --camera 0 --rows 8 --cols 8 --goal 5 5 --algorithm bfs
```

#### Example 4: ArUco Marker Detection

```bash
python main.py --image scene.jpg --rows 10 --cols 10 --goal 9 9 --corners aruco
```

## How It Works

### Pipeline Overview

1. **Input Acquisition** → Load image or capture from camera
2. **Corner Detection** → Identify 4 corners of inventory area (manual/ArUco/contour)
3. **Homography** → Compute perspective transformation matrix
4. **Perspective Warp** → Create rectified top-down view
5. **Grid Mapping** → Divide image into N×M cells
6. **Robot Detection** → Find robot using colored marker (HSV thresholding)
7. **Block Detection** → Detect objects using edge detection and contours
8. **Occupancy Grid** → Build 2D matrix (0=free, 1=block, 2=robot)
9. **Path Planning** → Run A* to find collision-free path
10. **Visualization** → Display grid, path, and annotations

### Coordinate System

- Grid uses **image convention**: (0,0) is top-left
- `i` = row index (increases downward)
- `j` = column index (increases rightward)

### Detection Methods

#### Robot Detection
- Uses **HSV color thresholding** to detect colored marker
- Configurable color: red, blue, green, yellow
- Threshold: minimum 5% of cell must be target color

#### Block Detection
- **Method 1**: Edge detection (Canny) + contour area analysis
- **Method 2**: Color variance analysis
- Combined approach for robustness

### Path Planning

#### A* Algorithm
- **Heuristic**: Manhattan distance
- **Cost**: 1 per step (uniform grid)
- **Neighbors**: 4-connected (up, down, left, right)

#### BFS Algorithm
- Guaranteed shortest path in unweighted grid
- Alternative when A* is not needed

## Module Descriptions

### `camera_stream.py`
Handles input from camera or image file. Provides unified interface with `CameraStream` class.

### `homography.py`
Performs perspective correction:
- Manual corner selection (mouse clicks)
- ArUco marker detection
- Contour-based rectangle detection
- Homography computation and warping

### `grid_mapper.py`
Maps warped image to N×M grid:
- Cell extraction and indexing
- Coordinate conversion (pixel ↔ grid)
- Grid visualization

### `detector.py`
Classifies grid cells:
- `RobotDetector`: HSV color-based detection
- `BlockDetector`: Edge and contour-based detection
- `CellClassifier`: Combines both detectors

### `occupancy_grid.py`
Represents inventory state:
- 2D matrix with cell types (0/1/2)
- Robot position tracking
- Grid visualization and statistics

### `planner.py`
Path planning algorithms:
- A* with Manhattan heuristic
- BFS alternative
- Path reconstruction
- Command generation (UP/DOWN/LEFT/RIGHT)

### `utils.py`
Helper functions:
- Drawing grid lines and paths
- Cell annotations
- Image resizing for display

## Testing Strategy

### For Initial Testing

Use simple props:
- **Robot**: Bottle with colored cap (red marker)
- **Blocks**: Playing cards or small boxes
- **Grid**: 5×5 or 10×10 drawn on floor/paper

### Test Cases

1. **Empty Grid**: Robot only, clear path
2. **Single Obstacle**: One block between robot and goal
3. **Multiple Obstacles**: Complex maze
4. **No Path**: Goal completely blocked
5. **Robot at Goal**: Start equals goal

## Troubleshooting

### Robot Not Detected
- Check `--robot-color` matches actual marker color
- Ensure good lighting conditions
- Adjust HSV ranges in `detector.py` if needed

### Path Not Found
- Verify goal cell is not blocked
- Check if obstacles completely block path
- Review occupancy grid output

### Corner Detection Failed
- Use `--corners manual` for manual selection
- Ensure 4 corners are visible and high-contrast
- For ArUco, use markers with IDs 0, 1, 2, 3

### Poor Detection Quality
- Improve lighting (avoid shadows)
- Use solid-color floor/background
- Increase image resolution with `--warp-size`

## Possible Extensions

- [ ] Multi-robot coordination
- [ ] Dynamic obstacle avoidance
- [ ] YOLO-based object detection
- [ ] ROS2 integration for real robots
- [ ] Velocity/acceleration planning
- [ ] 3D visualization

## Key Concepts (for Review)

### Computer Vision
- **Homography**: 3×3 projective transformation matrix
- **HSV Color Space**: Better for color detection than RGB
- **Canny Edge Detection**: Gradient-based edge detector
- **Contour Analysis**: Shape detection from edges

### Algorithms
- **A* Search**: Best-first search with heuristic
- **Manhattan Distance**: |Δx| + |Δy| (admissible heuristic)
- **BFS**: Breadth-first search for unweighted graphs

### Robotics
- **Occupancy Grid**: Discrete 2D map representation
- **Path Planning**: Finding collision-free trajectories
- **4-Connected Grid**: Cardinal direction movement only

## License

MIT License - Feel free to use for educational purposes.

## Author

Developed for overhead vision-based inventory robot routing project.

---

**Questions?** Check `INSTRUCTIONS.md` for detailed theory and cross-questions.
