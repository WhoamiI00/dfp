# Overhead Vision-Based Inventory Robot Routing

> Complete Python implementation of an overhead camera system for autonomous robot routing in inventory grids using computer vision and A* path planning.

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)](https://opencv.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Test the system
cd src
python test_system.py

# 3. Run an example (no hardware needed)
python examples.py 2

# 4. Run with your image
python main.py --image ../data/sample_images/test.jpg --rows 10 --cols 10 --goal 4 5
```

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| **[QUICKSTART.md](QUICKSTART.md)** | Get started in 5 minutes |
| **[README_PROJECT.md](README_PROJECT.md)** | Complete documentation |
| **[INSTRUCTIONS.md](INSTRUCTIONS.md)** | Theory and concepts |
| **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** | Implementation details |
| **[FILE_TREE.md](FILE_TREE.md)** | Project structure |

## ✨ Features

- ✅ **Perspective Correction** - Homography-based top-down view
- ✅ **Grid Mapping** - Configurable N×M inventory grid
- ✅ **Robot Detection** - HSV color-based marker detection
- ✅ **Object Detection** - Classical CV edge/contour detection
- ✅ **Path Planning** - A* with Manhattan heuristic + BFS
- ✅ **Visualization** - Real-time path display
- ✅ **Flexible Input** - Camera feed or static images
- ✅ **No Deep Learning** - Pure classical computer vision

## 🏗️ Architecture

```
Input (Camera/Image)
    ↓
Corner Detection → Homography → Top-Down View
    ↓
Grid Mapping (N×M cells)
    ↓
Detection (Robot + Blocks)
    ↓
Occupancy Grid (0=free, 1=block, 2=robot)
    ↓
A* Path Planning
    ↓
Visualization + Commands
```

## 📁 Project Structure

```
router/
├── src/               # Source code (10 modules)
│   ├── main.py       # Entry point with CLI
│   ├── planner.py    # A* path planning
│   ├── detector.py   # Object detection
│   └── ...
├── data/             # Test images
├── requirements.txt  # Dependencies
└── *.md             # Documentation
```

## 🎯 Usage Examples

### Basic Image Processing
```bash
python main.py --image test.jpg --rows 10 --cols 10 --goal 4 5
```

### Live Camera
```bash
python main.py --camera 0 --rows 5 --cols 5 --goal 2 3
```

### Blue Robot Marker
```bash
python main.py --image test.jpg --rows 10 --cols 10 --goal 7 8 --robot-color blue
```

### Save Output
```bash
python main.py --image test.jpg --rows 10 --cols 10 --goal 4 5 --output result.jpg
```

## 🧪 Testing

```bash
# Validate installation
.\check_install.ps1     # Windows PowerShell

# Run system tests
cd src
python test_system.py

# Interactive examples
python examples.py
```

## 🛠️ Technology Stack

- **Language:** Python 3.7+
- **Computer Vision:** OpenCV 4.x
- **Numerical Computing:** NumPy
- **Algorithms:** A*, BFS, Manhattan heuristic
- **Detection:** HSV thresholding, Canny edges, contours

## 📦 Installation

### Requirements
- Python 3.7 or higher
- pip (Python package manager)

### Setup
```bash
# Clone/download the repository
cd router

# Install dependencies
pip install -r requirements.txt

# Verify installation
.\check_install.ps1  # Windows
# OR
cd src && python test_system.py
```

## 🎓 Key Concepts

### Computer Vision
- Homography transformation
- HSV color space
- Canny edge detection
- Contour analysis

### Algorithms
- A* pathfinding
- Manhattan distance heuristic
- Breadth-First Search (BFS)

### Robotics
- Occupancy grid mapping
- Collision-free path planning
- 4-connected grid navigation

## 📊 Performance

- **Grid Size:** Tested up to 20×20 cells
- **Detection:** Real-time on static images
- **Path Planning:** <1s for typical grids
- **Camera:** 30 FPS capable (depends on resolution)

## 🔧 Customization

All parameters are configurable:
- Grid dimensions (--rows, --cols)
- Robot marker color (--robot-color)
- Detection thresholds (in code)
- Corner detection method (--corners)
- Path algorithm (--algorithm)

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Robot not detected | Check --robot-color matches marker |
| No path found | Verify goal is not blocked |
| Corner detection fails | Use --corners manual |
| Poor detection | Improve lighting, use solid background |

See [README_PROJECT.md](README_PROJECT.md#troubleshooting) for details.

## 🎯 Use Cases

- Warehouse inventory management
- Automated storage and retrieval
- Robot navigation research
- Computer vision education
- Path planning demonstrations

## 🚧 Future Extensions

- [ ] Multi-robot coordination
- [ ] Dynamic obstacle avoidance
- [ ] YOLO-based detection
- [ ] ROS2 integration
- [ ] 3D visualization
- [ ] Real-time re-planning

## 📚 Learning Resources

This project demonstrates:
- **Computer Vision:** Perspective transformation, color detection, edge detection
- **Algorithms:** A*, BFS, graph search, heuristics
- **Robotics:** Occupancy grids, path planning, collision avoidance
- **Python:** Clean architecture, modular design, CLI interfaces

## 🤝 Contributing

This is an educational project. Feel free to:
- Experiment with different detection methods
- Implement additional path planning algorithms
- Add visualization features
- Integrate with hardware robots

## 📄 License

MIT License - Free for educational and commercial use.

## 👤 Author

Developed as a complete implementation of overhead vision-based inventory robot routing system.

## 🌟 Highlights

- **Production-Ready:** ~2,240 lines of clean, documented code
- **Modular Design:** 10 independent modules with clear responsibilities
- **Well-Documented:** 6 comprehensive documentation files
- **Fully Tested:** Validation scripts included
- **Educational:** Perfect for learning CV and path planning
- **Extensible:** Easy to add features and improvements

## 📞 Support

- **Quick Start:** See [QUICKSTART.md](QUICKSTART.md)
- **Full Docs:** See [README_PROJECT.md](README_PROJECT.md)
- **Theory:** See [INSTRUCTIONS.md](INSTRUCTIONS.md)
- **Examples:** Run `python examples.py`

---

**Ready to route robots? Get started with [QUICKSTART.md](QUICKSTART.md)! 🤖**
