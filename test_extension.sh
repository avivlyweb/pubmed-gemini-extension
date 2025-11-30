#!/bin/bash
# Test script for PubMed Gemini Extension

echo "🧪 Testing PubMed Gemini Extension"
echo "=================================="

# Test 1: Check if extension is installed
echo "1. Checking extension installation..."
gemini extensions list | grep pubmed-gemini && echo "✅ Extension installed" || echo "❌ Extension not found"

# Test 2: Test the search command
echo ""
echo "2. Testing /pubmed:search command..."
echo "Command: /pubmed:search does exercise help chronic back pain"
echo "Note: This would normally run the command, but requires interactive Gemini CLI session"

# Test 3: Test the synthesis command
echo ""
echo "3. Testing /pubmed:synthesis command..."
echo "Command: /pubmed:synthesis telemedicine for diabetes"
echo "Note: This would normally run the command, but requires interactive Gemini CLI session"

# Test 4: Test the analyze command
echo ""
echo "4. Testing /pubmed:analyze command..."
echo "Command: /pubmed:analyze 34580864"
echo "Note: This would normally run the command, but requires interactive Gemini CLI session"

echo ""
echo "🎯 To test the extension:"
echo "1. Open Gemini CLI in a new terminal"
echo "2. Try: /pubmed:search does exercise help chronic back pain"
echo "3. Try: /pubmed:synthesis acupuncture for migraines"
echo "4. Try: /pubmed:analyze 34580864"

echo ""
echo "📚 Available tools in Gemini CLI:"
echo "- enhanced_pubmed_search: Advanced PubMed search with PICO analysis"
echo "- analyze_article_trustworthiness: Quality assessment of individual articles"
echo "- generate_research_summary: PhD-level research synthesis"
