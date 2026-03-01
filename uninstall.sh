#!/bin/bash
#
# Nagomi Clinical Forensic - Uninstaller
#
# Usage: curl -fsSL https://raw.githubusercontent.com/avivlyweb/pubmed-gemini-extension/main/uninstall.sh | bash
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="$HOME/.pubmed-gemini-extension"
EXT_LINK="$HOME/.gemini/extensions/pubmed-gemini"

echo ""
echo -e "${CYAN}Nagomi Clinical Forensic - Uninstaller${NC}"
echo "======================================"
echo ""

# Check if installed
if [[ ! -d "$INSTALL_DIR" ]] && [[ ! -L "$EXT_LINK" ]]; then
    echo -e "${YELLOW}Extension does not appear to be installed.${NC}"
    exit 0
fi

# Confirm
echo "This will remove:"
echo "  - $INSTALL_DIR"
echo "  - $EXT_LINK"
echo ""
read -p "Are you sure you want to uninstall? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Uninstall cancelled.${NC}"
    exit 0
fi

# Remove symlink
if [[ -L "$EXT_LINK" ]]; then
    rm "$EXT_LINK"
    echo -e "${GREEN}[OK]${NC} Removed Gemini CLI extension link"
fi

# Remove installation directory
if [[ -d "$INSTALL_DIR" ]]; then
    rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}[OK]${NC} Removed installation directory"
fi

echo ""
echo -e "${GREEN}Uninstallation complete!${NC}"
echo ""
echo "Note: Node.js and Python were NOT removed."
echo "To remove them, use your package manager (e.g., brew uninstall node python@3.12)"
echo ""
