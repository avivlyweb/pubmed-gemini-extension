#!/bin/bash
# Nagomi Clinical Forensic Verification Script

echo "🔍 Nagomi Clinical Forensic Verification"
echo "======================================"
echo ""

# Check 1: Extension in list
echo "1. Checking if extension is installed..."
if gemini extensions list | grep -q "pubmed-gemini"; then
    echo "✅ Extension found in Gemini CLI"
else
    echo "❌ Extension NOT found. Run install_extension.sh first"
    exit 1
fi

# Check 2: Files exist
echo ""
echo "2. Checking extension files..."
if [ -f "pubmed-gemini/gemini-extension.json" ] && [ -f "pubmed-gemini/GEMINI.md" ]; then
    echo "✅ Extension files present"
else
    echo "❌ Extension files missing"
    exit 1
fi

# Check 3: MCP server path
echo ""
echo "3. Checking MCP server connection..."
MCP_PATH=$(cat pubmed-gemini/gemini-extension.json | grep -o '"args":\s*\[[^]]*\]' | grep -o '"[^"]*pubmed_mcp\.py[^"]*"')
if [ -n "$MCP_PATH" ]; then
    echo "✅ MCP server path configured: $MCP_PATH"
else
    echo "❌ MCP server path not found in config"
fi

# Check 4: Custom commands
echo ""
echo "4. Checking custom commands..."
if [ -d "pubmed-gemini/commands/pubmed" ] && [ "$(ls pubmed-gemini/commands/pubmed/*.toml 2>/dev/null | wc -l)" -gt 0 ]; then
    echo "✅ Custom commands found: $(ls pubmed-gemini/commands/pubmed/*.toml | wc -l) command(s)"
else
    echo "❌ Custom commands missing"
fi

echo ""
echo "🎯 TEST YOUR INSTALLATION:"
echo "1. Open a NEW terminal window"
echo "2. Start Gemini CLI: gemini"
echo "3. Try: /nagomi:search does exercise help back pain"
echo "4. Try: /nagomi:synthesis acupuncture for migraines"
echo "5. Try: /nagomi:analyze 34580864"

echo ""
echo "📊 If you see PubMed analysis results, the installation is successful! 🎉"

echo ""
echo "🔧 TROUBLESHOOTING:"
echo "- If commands don't work: Restart Gemini CLI completely"
echo "- If MCP errors: Check that ../pubmed_mcp.py exists"
echo "- If no response: Wait 10-15 seconds for analysis to complete"
