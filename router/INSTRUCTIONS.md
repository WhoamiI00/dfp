Here’s a detailed **README.md** you can drop straight into your repo and adapt as you build.
I’ve written it so it doubles as a revision sheet for concepts + cross-questions.

---

````markdown
# Overhead Vision–Based Inventory Robot Routing

## 1. Project Overview

This project implements a **top-down vision system** that watches an inventory grid using a ceiling-mounted camera.  
From the live camera feed, the system:

1. Detects:
   - A **robot** (with a colored marker on top, e.g. red).
   - **Objects/blocks** in the inventory (e.g. product boxes).
2. Maps detections to **grid cells** in an `N x M` inventory (e.g. 10x10).
3. Builds an **occupancy grid** (which cells are empty / filled / robot).
4. Computes a **collision-free path** for the robot from its current cell to a target cell using a path-planning algorithm (e.g. A*).

For early testing, I use:
- Playing **cards** as blocks (objects).
- A **bottle** with a colored marker as the robot.
- A **5x5** or **10x10** grid drawn on the floor (or implied by spacing).

---

## 2. High-Level Architecture

**Input → Vision → Grid → Path Planning → Robot Commands**

1. **Camera Input**
   - Ceiling-mounted camera continuously captures frames.
2. **Preprocessing & Perspective Correction**
   - Detect 4 reference points (e.g., ArUco markers or manually defined corners).
   - Apply a homography transform to get a **top-down, undistorted view** of the inventory.
3. **Grid Mapping**
   - Warp the image into a fixed resolution and divide it into `N x M` cells.
4. **Object & Robot Detection**
   - For each cell, classify it as:
     - `Robot`
     - `Block`
     - `Empty`
5. **Occupancy Grid**
   - Represent the inventory as a 2D matrix:
     - `0 = free cell`
     - `1 = occupied (block)`
     - `2 = robot`
6. **Path Planning (e.g., A*)**
   - Given:
     - Start = robot cell (e.g., `(0, 0)`)
     - Goal = target object cell (e.g., `(4, 5)`)
   - Compute a path that does not cross occupied cells.
7. **Output**
   - Display the path on the image and/or
   - Convert path cells to movement commands (for a real robot later).

---

## 3. Tech Stack and Why

### 3.1 Programming Language

- **Python 3**
  - Easy prototyping and rich ecosystem for Computer Vision and AI.
  - Plenty of libraries and tutorials.

### 3.2 Core Libraries

- **OpenCV (opencv-python)**
  - Read camera stream, process images.
  - Detect colors, contours, markers.
  - Perform perspective correction (homography / warpPerspective).

- **NumPy**
  - Efficient operations on 2D arrays for the occupancy grid.
  - Useful for coordinate transformations and image slicing.

### 3.3 Optional / Advanced Libraries

- **Ultralytics YOLOv8 (Object Detection)**
  - For robust detection of robots and blocks in more complex scenes.
  - Not mandatory for the initial version with simple color-based detection.

- **(Later) ROS2 / MQTT / Serial**
  - For sending path commands or velocity commands to a physical robot.
  - Outside the scope of the first prototype.

---

## 4. Coordinate System and Grid Design

- The inventory is modeled as a **2D grid**: `N x M` (e.g., `10 x 10`).
- We define indices:

  - `i` → row index
  - `j` → column index

- Convention used (pick one and be consistent):

  - **Image/Grid convention** (common in CS):
    - `(0,0)` is **top-left**.
    - `i` increases downwards, `j` increases rightwards.
  - For a robot in a math/physics context, sometimes `(0,0)` is **bottom-left**, but since we work with images, top-left is more natural.

### Mapping Image → Grid

- Assume the warped image (`top_view`) has size `H x W` pixels.
- For a grid of `N` rows and `M` columns:

  - `cell_h = H // N`
  - `cell_w = W // M`

- Cell `(i, j)` in pixel coordinates:

  ```python
  y1 = i * cell_h
  y2 = (i + 1) * cell_h
  x1 = j * cell_w
  x2 = (j + 1) * cell_w

  cell_img = top_view[y1:y2, x1:x2]
````

---

## 5. Computer Vision Pipeline

### 5.1 Camera Calibration & Homography

**Why?**
To convert the original camera view (with perspective distortion) to a **rectified top-down view** where the grid is uniform.

**Steps:**

1. Place 4 high-contrast markers (or ArUco tags) on the four corners of the physical inventory area.

2. In each frame:

   * Detect these corners in the image → `pts_src`.

3. Define the desired destination coordinates → `pts_dst`, e.g.:

   ```python
   pts_dst = np.float32([
       [0, 0],
       [W, 0],
       [W, H],
       [0, H]
   ])
   ```

4. Compute the homography and warp:

   ```python
   H_mat, _ = cv2.findHomography(pts_src, pts_dst)
   top_view = cv2.warpPerspective(frame, H_mat, (W, H))
   ```

Now `top_view` is a clean rectangle representing the inventory.

**Possible Cross Questions:**

* What is **homography**?

  * A 3x3 projective transformation that maps points from one plane to another. Used to correct perspective.
* Why do we need **camera calibration**?

  * To remove distortions and map image coordinates to real-world coordinates accurately.

---

### 5.2 Robot Detection (Colored Marker)

For the initial prototype, the robot has a **distinct colored marker** on top (e.g., red).

1. Convert to HSV color space:

   ```python
   hsv = cv2.cvtColor(cell_img, cv2.COLOR_BGR2HSV)
   ```

2. Define HSV color ranges for red (two ranges due to wrap-around):

   ```python
   lower_red1 = np.array([0, 100, 100])
   upper_red1 = np.array([10, 255, 255])
   lower_red2 = np.array([160, 100, 100])
   upper_red2 = np.array([179, 255, 255])
   ```

3. Threshold and combine masks:

   ```python
   mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
   mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
   mask = mask1 | mask2
   ```

4. If the ratio of red pixels to total pixels exceeds a threshold → the cell contains the **robot**.

**Concepts:**

* RGB vs HSV.
* Thresholding.
* Binary masks.

---

### 5.3 Block / Object Detection

For each cell that is **not** robot:

**Simplified approach for uniform floor:**

1. Learn or fix a rough color range for **floor/background**.
2. Count pixels that are **not** floor.
3. If there is a significant area of non-floor pixels → mark as **occupied (block)**.
4. Else → **empty**.

Alternatively, use:

* **Edge/contour detection** (Canny + contour area).
* Treat large contours as blocks.

**Future improvement: YOLO**

* Train a YOLO model with two classes: `robot`, `block`.
* For each detection, map bounding box center to grid cell.

**Possible Cross Questions:**

* What is the difference between **classical computer vision** (color thresholding) and **deep learning**–based detection (YOLO)?
* Pros/cons of each in this project?

---

## 6. Occupancy Grid

After detection:

* Create an `N x M` matrix:

  ```python
  FREE = 0
  BLOCK = 1
  ROBOT = 2

  grid = np.zeros((N, M), dtype=int)
  ```

* While scanning cells:

  * If robot found → `grid[i][j] = ROBOT` and store its coordinates.
  * Else if block found → `grid[i][j] = BLOCK`.
  * Else → `grid[i][j] = FREE`.

**Concept:**
This is basically an **occupancy grid map**, commonly used in robotics for navigation.

---

## 7. Path Planning (A* on Grid)

**Goal:**
Given:

* `start = (rs, cs)` → robot’s current cell.
* `goal = (rt, ct)` → target object cell (e.g., `(4, 5)`).

Compute a path that avoids occupied cells.

### 7.1 Allowed Moves

* **4-connected grid** (Manhattan):

  * Up: `(i-1, j)`
  * Down: `(i+1, j)`
  * Left: `(i, j-1)`
  * Right: `(i, j+1)`

(You can extend to 8 directions if needed.)

### 7.2 BFS vs A*

* **BFS**:

  * Finds the shortest path in unweighted grids.
  * Simpler to implement.
* **A***:

  * Uses a **heuristic** (e.g., Manhattan distance) to guide the search.
  * Faster for large grids.

### 7.3 A* Outline

1. Define the heuristic:

   ```python
   def heuristic(a, b):
       # a = (i1, j1), b = (i2, j2)
       return abs(a[0] - b[0]) + abs(a[1] - b[1])  # Manhattan distance
   ```

2. Use a priority queue (min-heap) where priority = `cost_so_far + heuristic`.

3. Skip cells where `grid[i][j] == BLOCK`.

4. Stop when you reach `goal`; reconstruct path using a `came_from` dictionary.

**Possible Cross Questions:**

* Why is A* better than Dijkstra or BFS for this case?
* What makes a heuristic **admissible**?

  * It never overestimates the true cost to reach the goal.

---

## 8. Project Structure

A possible folder structure:

```text
inventory-robot-routing/
├── README.md
├── requirements.txt
├── data/
│   ├── sample_images/
│   └── calibration/
├── src/
│   ├── main.py               # Entry point
│   ├── camera_stream.py      # Capture frames
│   ├── homography.py         # Corner detection + warpPerspective
│   ├── grid_mapper.py        # Image ↔ grid conversion
│   ├── detector.py           # Robot + block detection
│   ├── occupancy_grid.py     # Build the N x M grid
│   ├── planner.py            # A* / BFS implementation
│   └── utils.py              # Helper functions
└── docs/
    └── design_notes.md
```

---

## 9. Installation & Setup

### 9.1 Dependencies

Create a `requirements.txt` like:

```text
opencv-python
numpy
# Optional:
ultralytics
```

Install:

```bash
pip install -r requirements.txt
```

### 9.2 Running

For a **single image test**:

```bash
python src/main.py --image data/sample_images/test1.jpg --rows 10 --cols 10 --goal 4 5
```

For a **live camera test** (webcam index 0):

```bash
python src/main.py --camera 0 --rows 10 --cols 10 --goal 4 5
```

*(Adjust arguments according to how you implement the CLI.)*

---

## 10. Assumptions & Limitations

* Exactly **one robot** in the scene.
* At most **one block per cell**.
* Grid lines or spacing between cells are clear enough to segment.
* Floor color is reasonably uniform (for simple background subtraction).
* Camera is fixed; scene changes only due to robot and object movements.

Future work:

* Multiple robots and conflict-free multi-agent path planning.
* Full YOLO-based detection for robust performance in complex backgrounds.
* Integration with a real robot via ROS2 or Arduino.
* Dynamic obstacles and re-planning in real time.

---

## 11. Possible Viva / Cross-Questions

1. **Why do we use a top-down camera instead of sensors on the robot only?**
2. **How does homography help in converting the image to a grid?**
3. **Difference between RGB and HSV color spaces; why HSV is often preferred for color detection?**
4. **What is an occupancy grid? How is it represented in your code?**
5. **Explain the A* algorithm and its heuristic.**
6. **What happens if there is no path? How does your code handle it?**
7. **How would you extend this to multiple robots or moving obstacles?**
8. **What are the advantages and disadvantages of classical CV vs deep learning–based object detection in this project?**
9. **How does resolution (image size) affect accuracy and speed?**
10. **If the camera is slightly shifted or rotated, what part of your pipeline compensates for it?**

---

## 12. Quick Summary of the Flow

1. Capture frame from overhead camera.
2. Detect four corners of the inventory area.
3. Compute homography and warp to a rectified top-down image.
4. Slice the image into `N x M` grid cells.
5. For each cell:

   * Detect robot via color threshold.
   * Detect block via background subtraction/contours.
6. Build occupancy grid (0 = free, 1 = block, 2 = robot).
7. Run A* from robot cell to target cell (e.g., (4,5)).
8. Visualize or send the path as commands.

---

*This README doubles as both implementation guide and theory reference.
As you implement, you can update sections with actual command-line arguments, screenshots, and code snippets from your project.*

```

If you tell me your final language/OS (e.g., “Python on Windows with VS Code”), I can tweak the “Installation & Running” section to be hyper-specific to your setup.
```
