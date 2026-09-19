@echo off
REM Optional helper: sets up and starts the Community Hunger Mapping System on Windows.
REM Double-click this file, or run it from Command Prompt.
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install Python 3.9 or newer from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

if not exist venv\Scripts\activate.bat (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Could not create the virtual environment.
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat
echo Installing requirements...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Could not install requirements. Check your internet connection.
    pause
    exit /b 1
)

python init_db.py
echo.
echo Starting the server. Open http://127.0.0.1:5000 in your browser.
echo Press Ctrl+C in this window to stop the server.
python app.py
pause
