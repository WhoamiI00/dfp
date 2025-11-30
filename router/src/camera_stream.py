"""
Camera stream and image input handling module.
Handles both live camera feed and static image loading.
"""

import cv2
import numpy as np


class CameraStream:
    """
    Wrapper class for camera stream or image input.
    Provides a unified interface for both live camera and static images.
    """
    
    def __init__(self, source=None):
        """
        Initialize camera stream or image source.
        
        Args:
            source: Can be:
                    - None: Use default camera (index 0)
                    - int: Camera index (e.g., 0, 1)
                    - str: Path to image file
        """
        self.source = source
        self.is_camera = False
        self.is_image = False
        self.cap = None
        self.static_image = None
        
        if source is None or isinstance(source, int):
            # Camera mode
            camera_index = source if source is not None else 0
            self.cap = cv2.VideoCapture(camera_index)
            
            if not self.cap.isOpened():
                raise ValueError(f"Cannot open camera with index {camera_index}")
            
            self.is_camera = True
            print(f"Camera stream initialized (index: {camera_index})")
            
        elif isinstance(source, str):
            # Image file mode
            self.static_image = cv2.imread(source)
            
            if self.static_image is None:
                raise ValueError(f"Cannot read image file: {source}")
            
            self.is_image = True
            print(f"Static image loaded: {source}")
        
        else:
            raise ValueError("Source must be None, int (camera index), or str (image path)")
    
    
    def read_frame(self):
        """
        Read a frame from the camera or return the static image.
        
        Returns:
            tuple: (success, frame)
                   - success (bool): True if frame was read successfully
                   - frame (numpy.ndarray): The captured/loaded image
        """
        if self.is_camera:
            ret, frame = self.cap.read()
            if not ret:
                print("Warning: Failed to read frame from camera")
                return False, None
            return True, frame
        
        elif self.is_image:
            # For static images, always return a copy
            return True, self.static_image.copy()
        
        return False, None
    
    
    def release(self):
        """
        Release camera resources.
        """
        if self.cap is not None:
            self.cap.release()
            print("Camera released")
    
    
    def get_frame_size(self):
        """
        Get the size of the frame/image.
        
        Returns:
            tuple: (width, height) or None if not available
        """
        if self.is_camera and self.cap is not None:
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return (width, height)
        
        elif self.is_image and self.static_image is not None:
            h, w = self.static_image.shape[:2]
            return (w, h)
        
        return None
    
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()


def load_image(image_path):
    """
    Load an image from file path.
    
    Args:
        image_path: Path to the image file
    
    Returns:
        numpy.ndarray: Loaded image or None if failed
    """
    image = cv2.imread(image_path)
    
    if image is None:
        print(f"Error: Cannot load image from {image_path}")
        return None
    
    print(f"Image loaded successfully: {image_path}")
    print(f"Image size: {image.shape[1]}x{image.shape[0]}")
    
    return image


def capture_from_camera(camera_index=0, display=False):
    """
    Capture a single frame from the camera.
    
    Args:
        camera_index: Index of the camera (default: 0)
        display: Whether to display the frame before capturing
    
    Returns:
        numpy.ndarray: Captured frame or None if failed
    """
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"Error: Cannot open camera with index {camera_index}")
        return None
    
    print("Camera opened. Press SPACE to capture, ESC to cancel.")
    
    frame = None
    
    while True:
        ret, temp_frame = cap.read()
        
        if not ret:
            print("Error: Cannot read frame from camera")
            break
        
        if display:
            cv2.imshow("Camera - Press SPACE to capture, ESC to cancel", temp_frame)
            key = cv2.waitKey(1) & 0xFF
            
            if key == 32:  # SPACE key
                frame = temp_frame.copy()
                print("Frame captured!")
                break
            elif key == 27:  # ESC key
                print("Capture cancelled")
                break
        else:
            # Capture immediately without display
            frame = temp_frame.copy()
            break
    
    cap.release()
    if display:
        cv2.destroyAllWindows()
    
    return frame
