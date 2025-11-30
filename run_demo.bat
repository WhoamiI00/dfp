@echo off
echo ========================================
echo  AI INVENTORY MANAGEMENT SYSTEM DEMO
echo ========================================
echo.
echo Starting the AI-powered inventory management system...
echo.
echo This will:
echo 1. Load the trained AI model
echo 2. Launch the interactive dashboard
echo.
echo Press Ctrl+C to stop at any time.
echo.
pause

cd /d "%~dp0"

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo ========================================
echo  LAUNCHING DASHBOARD...
echo ========================================
echo.
echo The dashboard will open in your browser at:
echo http://localhost:8501
echo.

streamlit run dashboard.py

pause
