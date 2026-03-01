#!/bin/bash
# Test script for Nagomi Clinical Forensic

echo "🧪 Testing Nagomi Clinical Forensic"
echo "=================================="

# Test 1: Check if extension is installed
echo "1. Checking extension installation..."
gemini extensions list | grep pubmed-gemini && echo "✅ Extension installed" || echo "❌ Extension not found"

# Test 2: Test the search command
echo ""
echo "2. Testing /nagomi:search command..."
echo "Command: /nagomi:search does exercise help chronic back pain"
echo "Note: This would normally run the command, but requires interactive Gemini CLI session"

# Test 3: Test the synthesis command
echo ""
echo "3. Testing /nagomi:synthesis command..."
echo "Command: /nagomi:synthesis telemedicine for diabetes"
echo "Note: This would normally run the command, but requires interactive Gemini CLI session"

# Test 4: Test the analyze command
echo ""
echo "4. Testing /nagomi:analyze command..."
echo "Command: /nagomi:analyze 34580864"
echo "Note: This would normally run the command, but requires interactive Gemini CLI session"

echo ""
echo "🎯 To test the extension:"
echo "1. Open Gemini CLI in a new terminal"
echo "2. Try: /nagomi:search does exercise help chronic back pain"
echo "3. Try: /nagomi:synthesis acupuncture for migraines"
echo "4. Try: /nagomi:analyze 34580864"

echo ""
echo "📚 Available tools in Gemini CLI:"
echo "- enhanced_pubmed_search: Advanced PubMed search with PICO analysis"
echo "- analyze_article_trustworthiness: Quality assessment of individual articles"
echo "- generate_research_summary: PhD-level research synthesis"
