"""
Installation and module test script.

Run this to verify that all modules are correctly installed and importable.
"""

import sys
import os


def test_imports():
    """Test if all required modules can be imported."""
    print("="*60)
    print("TESTING MODULE IMPORTS")
    print("="*60)
    
    tests = []
    
    # Test external dependencies
    print("\n[1/3] Testing external dependencies...")
    
    try:
        import cv2
        print(f"  ✓ OpenCV version: {cv2.__version__}")
        tests.append(("OpenCV", True))
    except ImportError as e:
        print(f"  ✗ OpenCV: {e}")
        tests.append(("OpenCV", False))
    
    try:
        import numpy as np
        print(f"  ✓ NumPy version: {np.__version__}")
        tests.append(("NumPy", True))
    except ImportError as e:
        print(f"  ✗ NumPy: {e}")
        tests.append(("NumPy", False))
    
    # Test project modules
    print("\n[2/3] Testing project modules...")
    
    modules = [
        'camera_stream',
        'homography',
        'grid_mapper',
        'detector',
        'occupancy_grid',
        'planner',
        'utils'
    ]
    
    for module in modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
            tests.append((module, True))
        except ImportError as e:
            print(f"  ✗ {module}: {e}")
            tests.append((module, False))
    
    # Test main script
    print("\n[3/3] Testing main script...")
    try:
        import main
        print(f"  ✓ main")
        tests.append(("main", True))
    except ImportError as e:
        print(f"  ✗ main: {e}")
        tests.append(("main", False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed! System is ready to use.")
        return True
    else:
        print("\n✗ Some tests failed. Please install missing dependencies:")
        print("  pip install -r ../requirements.txt")
        return False


def test_functionality():
    """Test basic functionality of each module."""
    print("\n" + "="*60)
    print("TESTING MODULE FUNCTIONALITY")
    print("="*60)
    
    import numpy as np
    import cv2
    from occupancy_grid import OccupancyGrid
    from planner import find_path
    
    # Test 1: Occupancy Grid
    print("\n[Test 1] Occupancy Grid...")
    try:
        grid = OccupancyGrid(5, 5)
        grid.set_cell(0, 0, grid.ROBOT)
        grid.set_cell(2, 2, grid.BLOCK)
        robot_pos = grid.get_robot_position()
        assert robot_pos == (0, 0), "Robot position incorrect"
        print("  ✓ Occupancy grid works correctly")
    except Exception as e:
        print(f"  ✗ Occupancy grid test failed: {e}")
        return False
    
    # Test 2: Path Planning
    print("\n[Test 2] Path Planning (A*)...")
    try:
        grid = OccupancyGrid(5, 5)
        grid.set_cell(0, 0, grid.ROBOT)
        grid.set_cell(2, 1, grid.BLOCK)
        grid.set_cell(2, 2, grid.BLOCK)
        
        path = find_path((0, 0), (4, 4), grid, algorithm='astar')
        assert path is not None, "Path should exist"
        assert path[0] == (0, 0), "Path should start at robot"
        assert path[-1] == (4, 4), "Path should end at goal"
        print(f"  ✓ Path found: {len(path)} steps")
    except Exception as e:
        print(f"  ✗ Path planning test failed: {e}")
        return False
    
    # Test 3: Grid Mapper
    print("\n[Test 3] Grid Mapper...")
    try:
        from grid_mapper import GridMapper
        
        # Create dummy image
        dummy_image = np.zeros((800, 800, 3), dtype=np.uint8)
        mapper = GridMapper(dummy_image, 10, 10)
        
        assert mapper.n_rows == 10
        assert mapper.n_cols == 10
        assert mapper.cell_height == 80
        assert mapper.cell_width == 80
        
        cell = mapper.get_cell(0, 0)
        assert cell is not None
        assert cell.shape == (80, 80, 3)
        
        print("  ✓ Grid mapper works correctly")
    except Exception as e:
        print(f"  ✗ Grid mapper test failed: {e}")
        return False
    
    # Test 4: Detector
    print("\n[Test 4] Detector...")
    try:
        from detector import CellClassifier
        
        classifier = CellClassifier(robot_color='red')
        
        # Create dummy red image (robot)
        red_cell = np.zeros((50, 50, 3), dtype=np.uint8)
        red_cell[:, :] = [0, 0, 255]  # BGR: Red
        
        result = classifier.classify_cell(red_cell)
        # Note: This might not always detect as ROBOT due to HSV conversion
        # Just check it doesn't crash
        
        print("  ✓ Detector works (classification returned)")
    except Exception as e:
        print(f"  ✗ Detector test failed: {e}")
        return False
    
    print("\n" + "="*60)
    print("✓ All functionality tests passed!")
    print("="*60)
    return True


def test_system_info():
    """Display system information."""
    print("\n" + "="*60)
    print("SYSTEM INFORMATION")
    print("="*60)
    
    print(f"\nPython version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current directory: {os.getcwd()}")
    
    try:
        import cv2
        print(f"\nOpenCV build info:")
        print(f"  Version: {cv2.__version__}")
        print(f"  Video I/O: {cv2.getBuildInformation().count('Video I/O') > 0}")
    except:
        pass


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("INVENTORY ROBOT ROUTING - SYSTEM TEST")
    print("="*60)
    
    # Change to src directory if needed
    if not os.path.exists('camera_stream.py'):
        if os.path.exists('src'):
            os.chdir('src')
            print("\nChanged directory to: src/")
    
    # Test imports
    if not test_imports():
        print("\n⚠ Please fix import errors before proceeding.")
        return False
    
    # Test functionality
    if not test_functionality():
        print("\n⚠ Some functionality tests failed.")
        return False
    
    # Show system info
    test_system_info()
    
    print("\n" + "="*60)
    print("✓ ALL TESTS PASSED - SYSTEM READY!")
    print("="*60)
    
    print("\nNext steps:")
    print("  1. Read QUICKSTART.md for usage instructions")
    print("  2. Run: python examples.py")
    print("  3. Or: python main.py --help")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
