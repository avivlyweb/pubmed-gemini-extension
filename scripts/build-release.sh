#!/bin/bash

# Build script for PubMed Gemini Extension GitHub Releases
# Creates a self-contained archive that works with:
#   gemini extensions install github:avivlyweb/pubmed-gemini-extension
#
# Made by Aviv at Avivly (physiotherapy.ai)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RELEASE_DIR="$PROJECT_ROOT/release"
ARCHIVE_NAME="pubmed-gemini.tar.gz"

echo "Building PubMed Gemini Extension release..."
echo "Project root: $PROJECT_ROOT"

# Clean previous build
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# Copy extension files (gemini-extension.json must be at root of archive)
echo "Copying extension files..."

# Core extension files from pubmed-gemini/
cp "$PROJECT_ROOT/pubmed-gemini/gemini-extension.json" "$RELEASE_DIR/"
cp "$PROJECT_ROOT/pubmed-gemini/pubmed-wrapper.js" "$RELEASE_DIR/"
cp "$PROJECT_ROOT/pubmed-gemini/package.json" "$RELEASE_DIR/"

# GEMINI.md for context
cp "$PROJECT_ROOT/pubmed-gemini/GEMINI.md" "$RELEASE_DIR/"

# Commands directory (if exists)
if [ -d "$PROJECT_ROOT/pubmed-gemini/commands" ]; then
    cp -r "$PROJECT_ROOT/pubmed-gemini/commands" "$RELEASE_DIR/"
fi

# Node modules (required for MCP SDK)
if [ -d "$PROJECT_ROOT/pubmed-gemini/node_modules" ]; then
    echo "Copying node_modules..."
    cp -r "$PROJECT_ROOT/pubmed-gemini/node_modules" "$RELEASE_DIR/"
fi

# Python MCP server (without venv - created on first run)
echo "Copying Python MCP server..."
mkdir -p "$RELEASE_DIR/pubmed-mcp"
cp "$PROJECT_ROOT/pubmed-mcp/pubmed_mcp.py" "$RELEASE_DIR/pubmed-mcp/"
cp "$PROJECT_ROOT/pubmed-mcp/requirements.txt" "$RELEASE_DIR/pubmed-mcp/"

# Copy test files (optional, for verification)
if [ -f "$PROJECT_ROOT/pubmed-mcp/test_query.py" ]; then
    cp "$PROJECT_ROOT/pubmed-mcp/test_query.py" "$RELEASE_DIR/pubmed-mcp/"
fi

# Create the archive (only include files that exist)
echo "Creating archive..."
cd "$RELEASE_DIR"

# Build list of files to include
FILES_TO_INCLUDE="gemini-extension.json pubmed-wrapper.js package.json GEMINI.md pubmed-mcp"

# Add optional directories if they exist
[ -d "commands" ] && FILES_TO_INCLUDE="$FILES_TO_INCLUDE commands"
[ -d "node_modules" ] && FILES_TO_INCLUDE="$FILES_TO_INCLUDE node_modules"

tar -czvf "$ARCHIVE_NAME" $FILES_TO_INCLUDE

echo ""
echo "Release archive created: $RELEASE_DIR/$ARCHIVE_NAME"
echo ""

# Show archive contents
echo "Archive contents:"
tar -tzvf "$ARCHIVE_NAME" | head -20
echo "..."

# Show archive size
ARCHIVE_SIZE=$(ls -lh "$ARCHIVE_NAME" | awk '{print $5}')
echo ""
echo "Archive size: $ARCHIVE_SIZE"
echo ""
echo "Done! Upload this file to GitHub Releases."
