@echo off
REM Navigate to the script's directory
cd /d "%~dp0.."

echo Setting up GitHub-to-EXE...
echo Current directory: %cd%

REM Create virtual environment
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment. Is Python installed?
    pause
    exit /b 1
)

call venv\Scripts\activate

REM Install dependencies
if not exist "backend\requirements.txt" (
    echo ERROR: backend\requirements.txt not found!
    echo Please make sure you're running this from your project root.
    pause
    exit /b 1
)

pip install -r backend\requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Setup complete!
echo To run manually later:
echo   call venv\Scripts\activate
echo   python -m backend.app
echo.
echo Starting server now...
timeout /t 2 /nobreak >nul
python -m backend.app