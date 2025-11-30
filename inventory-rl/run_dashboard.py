"""
Simple launcher for the Streamlit dashboard.

Run this script to start the interactive web interface:
    python run_dashboard.py
"""

import subprocess
import sys
import os

def main():
    """Launch the Streamlit dashboard."""
    print("=" * 60)
    print("Starting Inventory RL Dashboard...")
    print("=" * 60)
    
    # Check if streamlit is installed
    try:
        import streamlit
    except ImportError:
        print("❌ Streamlit is not installed!")
        print("\nInstall it with:")
        print("    pip install streamlit")
        sys.exit(1)
    
    # Get the path to streamlit_app.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, "streamlit_app.py")
    
    if not os.path.exists(app_path):
        print(f"❌ streamlit_app.py not found at {app_path}")
        sys.exit(1)
    
    print("\n🚀 Launching dashboard...")
    print("📍 Dashboard will open at: http://localhost:8501")
    print("\n💡 Tip: Use Ctrl+C to stop the server\n")
    print("=" * 60 + "\n")
    
    # Launch streamlit
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("Dashboard stopped.")
        print("=" * 60)

if __name__ == "__main__":
    main()
