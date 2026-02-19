#!/bin/bash
# Nagomi Clinical Forensic Installation Script

echo "🏯 Nagomi Clinical Forensic Installer"
echo "===================================="
echo ""

# Check if we're in the right directory
if [ ! -f "gemini-extension.json" ]; then
    echo "❌ Error: gemini-extension.json not found!"
    echo "Please run this script from the pubmed-gemini directory"
    exit 1
fi

echo "📍 Current directory: $(pwd)"
echo "📄 Extension config found: $(cat gemini-extension.json | grep '"name"' | cut -d'"' -f4)"
echo ""

echo "🔗 Linking Nagomi Forensic Engine to Gemini CLI..."
echo "This will ask for confirmation. Type 'Y' and press Enter."
echo ""

# Run the link command
gemini extensions link .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Extension linked successfully!"
    echo ""
    echo "🚀 Next steps:"
    echo "1. Restart your Gemini CLI (close and reopen)"
    echo "2. Try: /nagomi:synthesis the effects of running outside on brain function"
    echo "3. Try: /nagomi:verify 10.1001/jama.2023.12345"
    echo "4. Try: /nagomi:analyze 34580864"
    echo ""
    echo "📚 Available commands:"
    echo "• /nagomi:synthesis <topic>  - PhD-level evidence synthesis"
    echo "• /nagomi:verify <identifier> - Forensic citation audit"
    echo "• /nagomi:analyze <pmid>     - Methodological appraisal"
    echo "• /nagomi:export <pmid>      - Bibliographic export"
    echo ""
    echo "🧪 Test the installation:"
    echo "gemini extensions list | grep nagomi"
    echo ""
    echo "🎉 Engineered with precision for the global scientific vanguard!"
else
    echo ""
    echo "❌ Extension linking failed. Please check the error messages above."
    exit 1
fi
