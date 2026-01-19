#
# Claude Calendar Scheduler - Installation Script
# For Windows PowerShell
#

$ErrorActionPreference = "Stop"

function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Claude Calendar Scheduler - Installer" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow

$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} else {
    Write-Host "Error: Python not found. Please install Python 3.9 or later." -ForegroundColor Red
    exit 1
}

$pythonVersion = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pythonMajor = & $pythonCmd -c "import sys; print(sys.version_info.major)"
$pythonMinor = & $pythonCmd -c "import sys; print(sys.version_info.minor)"

if ([int]$pythonMajor -lt 3 -or ([int]$pythonMajor -eq 3 -and [int]$pythonMinor -lt 9)) {
    Write-Host "Error: Python 3.9 or later required. Found Python $pythonVersion" -ForegroundColor Red
    exit 1
}

Write-Host "Found Python $pythonVersion" -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "setup.py") -and -not (Test-Path "pyproject.toml")) {
    Write-Host "Error: Please run this script from the project root directory." -ForegroundColor Red
    exit 1
}

# Create virtual environment if it doesn't exist
Write-Host ""
Write-Host "Setting up virtual environment..." -ForegroundColor Yellow

if (-not (Test-Path "venv")) {
    & $pythonCmd -m venv venv
    Write-Host "Created virtual environment" -ForegroundColor Green
} else {
    Write-Host "Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host ""
Write-Host "Upgrading pip..." -ForegroundColor Yellow
pip install --upgrade pip --quiet 2>$null

# Install dependencies
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow
if (Test-Path "requirements.txt") {
    pip install -r requirements.txt --quiet 2>$null
}

# Install package in development mode
Write-Host ""
Write-Host "Installing claude-meet..." -ForegroundColor Yellow
pip install -e . --quiet 2>$null

# Verify installation
Write-Host ""
Write-Host "Verifying installation..." -ForegroundColor Yellow

try {
    $version = claude-meet --version 2>&1
    Write-Host "claude-meet installed successfully!" -ForegroundColor Green
} catch {
    Write-Host "Installation may have failed. Try running manually:" -ForegroundColor Red
    Write-Host "  pip install -e ." -ForegroundColor Yellow
    exit 1
}

# Create config directory
Write-Host ""
Write-Host "Creating config directory..." -ForegroundColor Yellow
$configDir = Join-Path $env:USERPROFILE ".claude-meet"
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}
Write-Host "Config directory: $configDir" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host ""
Write-Host "  1. " -NoNewline
Write-Host "Activate the virtual environment:" -ForegroundColor Yellow
Write-Host "     .\venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "  2. " -NoNewline
Write-Host "Run the setup wizard:" -ForegroundColor Yellow
Write-Host "     claude-meet init"
Write-Host ""
Write-Host "  3. " -NoNewline
Write-Host "Start scheduling:" -ForegroundColor Yellow
Write-Host "     claude-meet chat"
Write-Host ""
Write-Host "For help: claude-meet --help"
Write-Host ""
