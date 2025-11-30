# Installation Verification Script for Windows PowerShell
# Run this to check if everything is set up correctly

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Inventory Robot Routing - Installation Check" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ $pythonVersion" -ForegroundColor Green
    $pythonOk = $true
} catch {
    Write-Host "  ✗ Python not found!" -ForegroundColor Red
    Write-Host "    Please install Python 3.7+ from python.org" -ForegroundColor Red
    $pythonOk = $false
}

# Check pip
Write-Host ""
Write-Host "[2/4] Checking pip..." -ForegroundColor Yellow
try {
    $pipVersion = pip --version 2>&1
    Write-Host "  ✓ $pipVersion" -ForegroundColor Green
    $pipOk = $true
} catch {
    Write-Host "  ✗ pip not found!" -ForegroundColor Red
    $pipOk = $false
}

# Check if in correct directory
Write-Host ""
Write-Host "[3/4] Checking project structure..." -ForegroundColor Yellow
$currentDir = Get-Location
$requiredFiles = @("requirements.txt", "src\main.py", "QUICKSTART.md")
$allExist = $true

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ Found: $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Missing: $file" -ForegroundColor Red
        $allExist = $false
    }
}

if (-not $allExist) {
    Write-Host ""
    Write-Host "  Please run this script from the project root directory:" -ForegroundColor Red
    Write-Host "  cd c:\Users\ankit\Pictures\dfp\router" -ForegroundColor Yellow
    exit 1
}

# Install dependencies
Write-Host ""
Write-Host "[4/4] Checking dependencies..." -ForegroundColor Yellow

if ($pipOk) {
    Write-Host "  Installing from requirements.txt..." -ForegroundColor Cyan
    pip install -r requirements.txt --quiet
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Installation had issues, but may still work" -ForegroundColor Yellow
    }
}

# Run system test
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Running system tests..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

cd src
python test_system.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  ✓ INSTALLATION SUCCESSFUL!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Read QUICKSTART.md for usage instructions" -ForegroundColor White
    Write-Host "  2. Run examples: python examples.py" -ForegroundColor White
    Write-Host "  3. Or get help: python main.py --help" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "  ✗ Some tests failed" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please check the error messages above." -ForegroundColor Yellow
    Write-Host "Try: pip install opencv-python numpy" -ForegroundColor Yellow
    Write-Host ""
}

cd ..
