#!/bin/bash
#
# Claude Calendar Scheduler - Installation Script
# For macOS and Linux
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Claude Calendar Scheduler - Installer${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}Error: Python not found. Please install Python 3.9 or later.${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo -e "${RED}Error: Python 3.9 or later required. Found Python $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}Found Python $PYTHON_VERSION${NC}"

# Check if we're in the right directory
if [ ! -f "setup.py" ] && [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory.${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
echo ""
echo -e "${YELLOW}Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}Created virtual environment${NC}"
else
    echo -e "${GREEN}Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo ""
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo ""
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip --quiet

# Install dependencies
echo ""
echo -e "${YELLOW}Installing dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
fi

# Install package in development mode
echo ""
echo -e "${YELLOW}Installing claude-meet...${NC}"
pip install -e . --quiet

# Verify installation
echo ""
echo -e "${YELLOW}Verifying installation...${NC}"
if command -v claude-meet &> /dev/null; then
    VERSION=$(claude-meet --version 2>&1 || echo "installed")
    echo -e "${GREEN}claude-meet installed successfully!${NC}"
else
    echo -e "${RED}Installation may have failed. Try running manually:${NC}"
    echo "  pip install -e ."
    exit 1
fi

# Create config directory
echo ""
echo -e "${YELLOW}Creating config directory...${NC}"
mkdir -p ~/.claude-meet
echo -e "${GREEN}Config directory: ~/.claude-meet${NC}"

# Summary
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo -e "Next steps:"
echo ""
echo -e "  1. ${YELLOW}Activate the virtual environment:${NC}"
echo -e "     source venv/bin/activate"
echo ""
echo -e "  2. ${YELLOW}Run the setup wizard:${NC}"
echo -e "     claude-meet init"
echo ""
echo -e "  3. ${YELLOW}Start scheduling:${NC}"
echo -e "     claude-meet chat"
echo ""
echo -e "For help: claude-meet --help"
echo ""
