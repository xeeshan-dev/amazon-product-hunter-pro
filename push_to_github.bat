@echo off
echo ========================================
echo Amazon Hunter Pro - GitHub Push Script
echo ========================================
echo.

REM Check if git is configured
git config user.name >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not configured!
    echo.
    echo Please run these commands first:
    echo   git config --global user.name "Your Name"
    echo   git config --global user.email "your.email@example.com"
    echo.
    pause
    exit /b 1
)

echo [1/5] Checking git status...
git status

echo.
echo [2/5] Adding all files...
git add .

echo.
echo [3/5] Creating commit...
git commit -m "feat: Enhanced UI with filters, export, and winner detection - Added download functionality (CSV and JSON export) - Added interactive filters (margin, sales range, seller filters) - Added winning product detection with visual badges - Added profit calculator modal - Production-ready infrastructure"

echo.
echo [4/5] Checking for remote...
git remote -v

echo.
echo ========================================
echo NEXT STEPS:
echo ========================================
echo.
echo 1. Create a new repository on GitHub:
echo    https://github.com/new
echo.
echo 2. Copy your repository URL
echo.
echo 3. Run these commands:
echo    git remote add origin YOUR_REPO_URL
echo    git branch -M main
echo    git push -u origin main
echo.
echo ========================================
pause
