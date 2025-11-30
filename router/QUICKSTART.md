# Quick Start Guide

## Installation

```bash
# Navigate to project directory
cd c:\Users\ankit\Pictures\dfp\router

# Install dependencies
pip install -r requirements.txt
```

## Running Your First Test

### Option 1: With a Test Image

1. **Prepare test setup:**
   - Draw or print a 5×5 or 10×10 grid
   - Place a bottle with a red cap (robot)
   - Place some cards or small boxes (obstacles)
   - Take a photo from directly above

2. **Save image:**
   ```
   Save as: data/sample_images/test.jpg
   ```

3. **Run the system:**
   ```bash
   cd src
   python main.py --image ../data/sample_images/test.jpg --rows 5 --cols 5 --goal 2 3
   ```

4. **When prompted:**
   - Click the 4 corners of your grid area (top-left, top-right, bottom-right, bottom-left)
   - Press any key to see results

### Option 2: Programmatic Example

Run the synthetic grid example (no camera/image needed):

```bash
cd src
python examples.py 2
```

This creates a virtual grid and shows path planning.

### Option 3: Live Camera

```bash
cd src
python main.py --camera 0 --rows 5 --cols 5 --goal 2 3
```

## Common Commands

### Basic Usage
```bash
# 10×10 grid, goal at (4,5)
python main.py --image test.jpg --rows 10 --cols 10 --goal 4 5
```

### Different Robot Color
```bash
# Blue robot marker
python main.py --image test.jpg --rows 10 --cols 10 --goal 4 5 --robot-color blue
```

### Save Output Image
```bash
# Save visualization
python main.py --image test.jpg --rows 5 --cols 5 --goal 2 3 --output result.jpg
```

### Use BFS Instead of A*
```bash
python main.py --image test.jpg --rows 10 --cols 10 --goal 7 8 --algorithm bfs
```

## Troubleshooting

### "Robot not detected"
- **Solution 1:** Check `--robot-color` matches your marker
- **Solution 2:** Ensure good lighting
- **Solution 3:** Make robot marker more prominent

### "No path found"
- **Solution 1:** Check if goal cell is blocked
- **Solution 2:** Verify obstacles don't completely block path
- **Solution 3:** Try different goal position

### "Cannot read image"
- **Solution:** Check file path is correct and image exists
- **Example:** Use forward slashes or double backslashes in paths

### Corner detection issues
- **Solution:** Use manual corner selection: `--corners manual`
- Click corners in order: top-left, top-right, bottom-right, bottom-left

## Project Files

```
src/main.py              - Main entry point (start here!)
src/examples.py          - Example usage scripts
src/camera_stream.py     - Camera/image input
src/homography.py        - Perspective correction
src/grid_mapper.py       - Grid cell management
src/detector.py          - Object detection
src/occupancy_grid.py    - Grid representation
src/planner.py           - Path planning (A*)
src/utils.py             - Helper functions
```

## Testing Without Hardware

You can test the system without a camera or physical setup:

```bash
cd src
python examples.py
# Select option 2 (Programmatic Grid)
```

This demonstrates the path planning on a synthetic grid.

## Next Steps

1. ✅ Run `examples.py` to see different use cases
2. ✅ Create your own test setup with grid + robot + obstacles
3. ✅ Capture an overhead photo
4. ✅ Run `main.py` with your image
5. ✅ Experiment with different grid sizes and robot colors

## Help

```bash
# Show all command-line options
python main.py --help
```

## Full README

See `README_PROJECT.md` for complete documentation.
See `INSTRUCTIONS.md` for theory and concepts.
