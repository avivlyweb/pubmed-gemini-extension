#!/bin/bash
# PubMed Gemini Extension Installation Script

echo "🧬 PubMed Gemini Extension Installer"
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

echo "🔗 Linking extension to Gemini CLI..."
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
    echo "2. Try: /pubmed:search does exercise help back pain"
    echo "3. Try: /pubmed:synthesis telemedicine for diabetes"
    echo "4. Try: /pubmed:analyze 34580864"
    echo ""
    echo "📚 Available commands:"
    echo "• /pubmed:search <query>     - Enhanced PubMed search"
    echo "• /pubmed:synthesis <topic>  - PhD-level research synthesis"
    echo "• /pubmed:analyze <pmid>     - Article quality assessment"
    echo ""
    echo "🧪 Test the installation:"
    echo "gemini extensions list | grep pubmed"
    echo ""
    echo "🎉 Happy researching with AI-powered PubMed analysis!"
else
    echo ""
    echo "❌ Extension linking failed. Please check the error messages above."
    exit 1
fi
