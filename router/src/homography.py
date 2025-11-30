"""
Homography and perspective correction module.
Handles corner detection and perspective transformation to create a top-down view.
"""

import cv2
import numpy as np


def detect_corners_manual(image, display=True):
    """
    Manually select 4 corners of the inventory area by clicking on the image.
    
    Args:
        image: Input image
        display: Whether to display the image and wait for clicks
    
    Returns:
        numpy.ndarray: Array of 4 corner points in order [top-left, top-right, bottom-right, bottom-left]
                       or None if selection was cancelled
    """
    points = []
    
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(points) < 4:
                points.append([x, y])
                cv2.circle(temp_image, (x, y), 5, (0, 255, 0), -1)
                cv2.putText(temp_image, str(len(points)), (x + 10, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.imshow("Select 4 Corners", temp_image)
    
    temp_image = image.copy()
    
    print("\nClick on the 4 corners of the inventory area:")
    print("  1. Top-Left")
    print("  2. Top-Right")
    print("  3. Bottom-Right")
    print("  4. Bottom-Left")
    print("Press ESC to cancel")
    
    cv2.imshow("Select 4 Corners", temp_image)
    cv2.setMouseCallback("Select 4 Corners", mouse_callback)
    
    while len(points) < 4:
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            print("Corner selection cancelled")
            cv2.destroyAllWindows()
            return None
    
    cv2.destroyAllWindows()
    
    return np.float32(points)


def detect_corners_aruco(image, marker_size=100):
    """
    Detect ArUco markers at the 4 corners of the inventory area.
    
    Args:
        image: Input image
        marker_size: Expected size of ArUco markers in pixels (approximate)
    
    Returns:
        numpy.ndarray: Array of 4 corner points or None if detection failed
    """
    try:
        # Initialize ArUco detector
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        aruco_params = cv2.aruco.DetectorParameters()
        detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
        
        # Detect markers
        corners, ids, rejected = detector.detectMarkers(image)
        
        if ids is None or len(ids) < 4:
            print(f"Error: Found only {len(ids) if ids is not None else 0} markers, need 4")
            return None
        
        # Extract corner points (center of each marker)
        # Assumes markers with IDs 0, 1, 2, 3 correspond to corners
        corner_points = {}
        for i, marker_id in enumerate(ids):
            marker_id = marker_id[0]
            if marker_id < 4:
                # Get center of the marker
                corner = corners[i][0]
                center_x = int(np.mean(corner[:, 0]))
                center_y = int(np.mean(corner[:, 1]))
                corner_points[marker_id] = [center_x, center_y]
        
        if len(corner_points) < 4:
            print("Error: Could not find markers with IDs 0, 1, 2, 3")
            return None
        
        # Order: top-left (0), top-right (1), bottom-right (2), bottom-left (3)
        pts = np.float32([corner_points[i] for i in range(4)])
        
        print("ArUco markers detected successfully")
        return pts
        
    except Exception as e:
        print(f"ArUco detection failed: {e}")
        return None


def detect_corners_contour(image, min_area=10000):
    """
    Detect the inventory area by finding the largest rectangular contour.
    
    Args:
        image: Input image
        min_area: Minimum area threshold for valid contours
    
    Returns:
        numpy.ndarray: Array of 4 corner points or None if detection failed
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Find the largest rectangular contour
    best_contour = None
    max_area = 0
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
        
        # Approximate the contour to a polygon
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        
        if len(approx) == 4 and area > max_area:
            max_area = area
            best_contour = approx
    
    if best_contour is None:
        print("Error: Could not find a rectangular contour")
        return None
    
    # Extract the 4 corners
    pts = best_contour.reshape(4, 2).astype(np.float32)
    
    # Order points: top-left, top-right, bottom-right, bottom-left
    pts = order_points(pts)
    
    print("Corners detected from contour")
    return pts


def order_points(pts):
    """
    Order points in the sequence: top-left, top-right, bottom-right, bottom-left.
    
    Args:
        pts: Array of 4 points
    
    Returns:
        numpy.ndarray: Ordered array of points
    """
    # Initialize ordered points
    rect = np.zeros((4, 2), dtype=np.float32)
    
    # Sum of coordinates: top-left will have smallest sum, bottom-right will have largest
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # Top-left
    rect[2] = pts[np.argmax(s)]  # Bottom-right
    
    # Difference of coordinates: top-right will have smallest diff, bottom-left will have largest
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # Top-right
    rect[3] = pts[np.argmax(diff)]  # Bottom-left
    
    return rect


def compute_homography(src_points, dst_width=800, dst_height=800):
    """
    Compute homography matrix to transform source points to a rectangular top-down view.
    
    Args:
        src_points: Source corner points (4 points in the original image)
        dst_width: Width of the destination image
        dst_height: Height of the destination image
    
    Returns:
        tuple: (homography_matrix, dst_points)
    """
    # Ensure source points are ordered
    src_points = order_points(src_points)
    
    # Define destination points (rectangle)
    dst_points = np.float32([
        [0, 0],                          # Top-left
        [dst_width - 1, 0],              # Top-right
        [dst_width - 1, dst_height - 1], # Bottom-right
        [0, dst_height - 1]              # Bottom-left
    ])
    
    # Compute homography
    H, status = cv2.findHomography(src_points, dst_points)
    
    if H is None:
        raise ValueError("Failed to compute homography matrix")
    
    print(f"Homography computed for {dst_width}x{dst_height} output")
    
    return H, dst_points


def warp_perspective(image, homography_matrix, width, height):
    """
    Apply perspective transformation to get top-down view.
    
    Args:
        image: Input image
        homography_matrix: Homography matrix from compute_homography
        width: Width of output image
        height: Height of output image
    
    Returns:
        numpy.ndarray: Warped top-down view
    """
    warped = cv2.warpPerspective(image, homography_matrix, (width, height))
    
    print(f"Perspective warped to {width}x{height}")
    
    return warped


def get_top_down_view(image, corners=None, width=800, height=800, auto_detect='manual'):
    """
    Complete pipeline to get top-down view from an image.
    
    Args:
        image: Input image
        corners: Pre-defined corner points (optional)
        width: Output width
        height: Output height
        auto_detect: Method for corner detection ('manual', 'aruco', 'contour')
    
    Returns:
        tuple: (top_down_image, homography_matrix) or (None, None) if failed
    """
    # Detect corners if not provided
    if corners is None:
        if auto_detect == 'aruco':
            corners = detect_corners_aruco(image)
        elif auto_detect == 'contour':
            corners = detect_corners_contour(image)
        else:  # manual
            corners = detect_corners_manual(image)
        
        if corners is None:
            print("Error: Failed to detect corners")
            return None, None
    
    # Compute homography
    try:
        H, _ = compute_homography(corners, width, height)
    except ValueError as e:
        print(f"Error: {e}")
        return None, None
    
    # Warp perspective
    top_down = warp_perspective(image, H, width, height)
    
    return top_down, H
