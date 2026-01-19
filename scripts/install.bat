@echo off
REM Claude Calendar Scheduler - Installation Script
REM For Windows Command Prompt

echo.
echo ============================================
echo   Claude Calendar Scheduler - Installer
echo ============================================
echo.

REM Check Python
echo Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.9 or later.
    exit /b 1
)

python -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"
if errorlevel 1 (
    echo Error: Python 3.9 or later required.
    exit /b 1
)

for /f "tokens=*" %%i in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

REM Check if we're in the right directory
if not exist "setup.py" if not exist "pyproject.toml" (
    echo Error: Please run this script from the project root directory.
    exit /b 1
)

REM Create virtual environment
echo.
echo Setting up virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Created virtual environment
) else (
    echo Virtual environment already exists
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Upgrading pip...
pip install --upgrade pip --quiet 2>nul

REM Install dependencies
echo.
echo Installing dependencies...
if exist "requirements.txt" (
    pip install -r requirements.txt --quiet 2>nul
)

REM Install package
echo.
echo Installing claude-meet...
pip install -e . --quiet 2>nul

REM Verify installation
echo.
echo Verifying installation...
claude-meet --version >nul 2>&1
if errorlevel 1 (
    echo Installation may have failed. Try running manually:
    echo   pip install -e .
    exit /b 1
)
echo claude-meet installed successfully!

REM Create config directory
echo.
echo Creating config directory...
if not exist "%USERPROFILE%\.claude-meet" mkdir "%USERPROFILE%\.claude-meet"
echo Config directory: %USERPROFILE%\.claude-meet

REM Summary
echo.
echo ============================================
echo   Installation Complete!
echo ============================================
echo.
echo Next steps:
echo.
echo   1. Activate the virtual environment:
echo      venv\Scripts\activate.bat
echo.
echo   2. Run the setup wizard:
echo      claude-meet init
echo.
echo   3. Start scheduling:
echo      claude-meet chat
echo.
echo For help: claude-meet --help
echo.
