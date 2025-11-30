# Test and Example Scripts

This directory will contain test images for the inventory robot routing system.

## Expected Contents

Place your test images here with the following characteristics:

### Image Requirements

1. **Overhead view** of inventory area
2. **Visible corners** for perspective correction
3. **Robot** with colored marker (red/blue/green/yellow)
4. **Objects/blocks** (cards, boxes, etc.)
5. **Clear floor** background

### Recommended Test Images

- `test_5x5.jpg` - Simple 5×5 grid
- `test_10x10.jpg` - Larger 10×10 grid
- `test_obstacles.jpg` - Grid with multiple blocks
- `test_aruco.jpg` - Grid with ArUco markers at corners

### Example Setup

```
Floor/Surface (uniform color)
├── Grid drawn (optional, helps visualization)
├── 4 corner markers (for homography)
├── Bottle/object with red cap (robot)
└── Playing cards or blocks (obstacles)
```

### Capture Tips

1. Mount camera directly above inventory area
2. Ensure even lighting (no harsh shadows)
3. Keep camera parallel to ground (minimize distortion)
4. Include all 4 corners in frame
5. Use high resolution (1280×720 or higher)

## Usage

After placing images here, run:

```bash
cd ../src
python main.py --image ../data/sample_images/YOUR_IMAGE.jpg --rows 10 --cols 10 --goal 4 5
```
