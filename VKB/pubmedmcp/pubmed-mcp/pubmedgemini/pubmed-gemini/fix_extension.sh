#!/bin/bash
# Fix PubMed Gemini Extension Script

echo "🔧 Fixing PubMed Gemini Extension..."
echo "===================================="

# Check if we're in the right directory
if [ ! -f "gemini-extension.json" ]; then
    echo "❌ Error: gemini-extension.json not found!"
    echo "Please run this script from the pubmed-gemini directory"
    exit 1
fi

echo "📍 Current directory: $(pwd)"
echo ""

# Unlink the old extension
echo "1. Unlinking old extension..."
gemini extensions unlink pubmed-gemini

if [ $? -eq 0 ]; then
    echo "✅ Successfully unlinked"
else
    echo "⚠️  Unlink may have failed (extension might not exist)"
fi

echo ""

# Link the new extension
echo "2. Linking updated extension..."
gemini extensions link .

if [ $? -eq 0 ]; then
    echo "✅ Successfully linked"
else
    echo "❌ Linking failed"
    exit 1
fi

echo ""

# Verify
echo "3. Verifying installation..."
gemini extensions list | grep pubmed

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Extension fixed successfully!"
    echo ""
    echo "🧪 TEST IT NOW:"
    echo "1. Open a NEW Gemini CLI terminal: gemini"
    echo "2. Try: /pubmed:search does exercise help back pain"
    echo "3. You should see PICO analysis and trust scores (not Google Search fallback)"
    echo ""
    echo "📚 Available commands:"
    echo "• /pubmed:search <query> - Enhanced PubMed search"
    echo "• /pubmed:synthesis <topic> - PhD-level synthesis"
    echo "• /pubmed:analyze <pmid> - Article quality assessment"
else
    echo ""
    echo "❌ Verification failed - extension may not be properly linked"
fi
