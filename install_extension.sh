#!/bin/bash
# PubMed Gemini Extension - Local Installation Script
# Run this after cloning the repository manually

set -e

echo "PubMed Gemini Extension - Local Installer"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "gemini-extension.json" ]; then
    echo "Error: gemini-extension.json not found!"
    echo "Please run this script from the pubmed-gemini-extension directory"
    exit 1
fi

echo "Current directory: $(pwd)"
echo "Extension: $(grep '"name"' gemini-extension.json | cut -d'"' -f4)"
echo ""

# Install Python dependencies
echo "[1/4] Installing Python dependencies..."
if [ -f "pubmed-mcp/requirements.txt" ]; then
    pip3 install -r pubmed-mcp/requirements.txt
    if [ $? -ne 0 ]; then
        echo "Warning: Failed to install Python dependencies."
        echo "Please install manually: pip3 install httpx"
    else
        echo "Python dependencies installed successfully!"
    fi
else
    pip3 install httpx
fi
echo ""

# Install Node.js dependencies
echo "[2/4] Installing Node.js dependencies..."
if [ -f "pubmed-gemini/package.json" ]; then
    cd pubmed-gemini && npm install && cd ..
    echo "Node.js dependencies installed!"
fi
echo ""

# Link extension
echo "[3/4] Linking extension to Gemini CLI..."
echo "This may ask for confirmation. Type 'Y' and press Enter."
echo ""
gemini extensions link .
echo ""

# Verify
echo "[4/4] Verifying installation..."
if gemini extensions list 2>/dev/null | grep -q "pubmed-gemini"; then
    echo ""
    echo "=========================================="
    echo "Installation Complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "  1. Restart your Gemini CLI (close and reopen)"
    echo "  2. Try: /pubmed:search does exercise help back pain"
    echo "  3. Try: /pubmed:synthesis telemedicine for diabetes"
    echo "  4. Try: /pubmed:analyze 34580864"
    echo ""
    echo "Available commands:"
    echo "  /pubmed:search <query>     - Enhanced PubMed search"
    echo "  /pubmed:synthesis <topic>  - PhD-level research synthesis"
    echo "  /pubmed:analyze <pmid>     - Article quality assessment"
    echo ""
else
    echo ""
    echo "Warning: Could not verify installation."
    echo "Please restart Gemini CLI and try: gemini extensions list"
fi
