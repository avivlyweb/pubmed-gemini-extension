# 🦸‍♂️ PubMed Gemini Extension

**Transform Gemini CLI into a Medical Research Superhero!** 🔬🤖📚

[![Gemini CLI Extension](https://img.shields.io/badge/Gemini_CLI-Extension-blue)](https://gcli.dev)
[![Medical Research](https://img.shields.io/badge/Medical-Research-red)](https://pubmed.ncbi.nlm.nih.gov)
[![PhD Level](https://img.shields.io/badge/Analysis-PhD_Level-purple)](https://pubmed.ncbi.nlm.nih.gov)
[![GitHub Repo](https://img.shields.io/badge/GitHub-avivlyweb%2Fpubmed--gemini--extension-black)](https://github.com/avivlyweb/pubmed-gemini-extension)

---

## 🚀 **What is This?**

Turn your Gemini CLI into a **professional medical research assistant** powered by:

- **🧬 35+ Million Medical Articles** from PubMed
- **⭐ Trust Scores & Evidence Grades** (A/B/C/D)
- **🏥 PICO Analysis Framework** (Patient, Intervention, Comparison, Outcome)
- **🧠 AI-Powered Research Synthesis** with ClinicalBERT
- **📊 Quality Assessment** using advanced algorithms

**Perfect for researchers, doctors, students, and anyone exploring medical science!**

---

## 🎯 **Key Features**

### **🔍 Advanced PubMed Search**
- Clinical question optimization
- PICO framework extraction
- Evidence-based filtering
- Trustworthiness scoring

### **📊 Article Quality Analysis**
- Methodological rigor assessment
- Risk of bias evaluation
- Study design hierarchy
- Clinical relevance scoring

### **🧠 Research Synthesis**
- Systematic review automation
- Evidence strength evaluation
- Clinical recommendation generation
- Research gap identification

### **💻 Multiple Access Methods**
- **Gemini CLI Commands**: `/pubmed:search`, `/pubmed:analyze`, `/pubmed:synthesis`
- **Direct Python API**: Full programmatic access
- **CLI Tool**: Terminal-based interface with hacker mode

---

## 📦 **Installation**

### **Quick Install (Recommended)**

```bash
# Install directly from GitHub
gemini extensions install https://github.com/avivlyweb/pubmed-gemini-extension

# Or install from a specific branch/tag
gemini extensions install https://github.com/avivlyweb/pubmed-gemini-extension --ref=main
```

### **Requirements**
- **Gemini CLI** installed ([download here](https://gcli.dev))
- **Node.js** 18+ ([download here](https://nodejs.org))
- **Python 3.8+** ([download here](https://python.org))
- **Internet connection** for PubMed API access

### **Automatic Setup**
The extension will automatically:
- ✅ Download required Python dependencies
- ✅ Setup virtual environment
- ✅ Configure MCP server connection
- ✅ Install custom commands

---

## 🎮 **Usage**

### **Search Medical Research**
```bash
# Open Gemini CLI
gemini

# Search for medical evidence
/pubmed:search does exercise help chronic back pain
/pubmed:search what treatments work for migraines
/pubmed:search is vitamin D good for bone health
```

### **Analyze Specific Articles**
```bash
# Analyze article quality
/pubmed:analyze 34580864
/pubmed:analyze 37894562
```

### **Generate Research Summaries**
```bash
# Create comprehensive analysis
/pubmed:synthesis telemedicine for diabetes management
/pubmed:synthesis exercise for mental health
```

### **Example Conversation**
```
You: /pubmed:search does yoga help anxiety

Gemini: Based on the PubMed search results, here's what I found:

🔬 **Search Results** (10 articles found)

1. **Yoga for Anxiety** - Trust Score: 85 ⭐
   - **PICO Analysis**: Population (adults with anxiety), Intervention (yoga therapy), Comparison (usual care), Outcome (anxiety reduction)
   - **Evidence Grade**: B (Good evidence)
   - **Key Findings**: 8-week yoga program reduced anxiety symptoms by 25%

2. **Mindfulness Yoga Study** - Trust Score: 78 ⭐
   - **PICO Analysis**: Population (young adults), Intervention (mindfulness-based yoga), Comparison (meditation alone), Outcome (stress reduction)
   - **Evidence Grade**: B (Good evidence)

🧠 **Research Synthesis**: Yoga appears effective for anxiety reduction with moderate to strong evidence...
```

---

## 🏗️ **Architecture**

### **Multi-Component System**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Gemini CLI    │────│  Node.js Wrapper │────│ Python MCP Server│
│                 │    │                  │    │                 │
│ /pubmed:search  │    │ pubmed-wrapper.js│    │ pubmed_mcp.py   │
│ /pubmed:analyze │    │                  │    │                 │
│ /pubmed:synthesis│    │                  │    │ ClinicalBERT   │
└─────────────────┘    └──────────────────┘    │ PICO Analysis  │
                                               │ Quality Assess │
                                               └─────────────────┘
```

### **AI Models & Algorithms**
- **ClinicalBERT**: Specialized language model for medical text
- **PICO Extractor**: Automatic clinical question structuring
- **Quality Assessor**: Evidence-based study evaluation
- **Synthesis Engine**: AI-powered research summarization

---

## 📊 **Evidence Quality System**

### **Trust Scores (0-100)**
- **80-100**: ⭐ Excellent research
- **50-79**: ⚠️ Good research
- **0-49**: ❌ Limited evidence

### **Evidence Grades**
- **A**: Excellent evidence (systematic reviews, meta-analyses)
- **B**: Good evidence (randomized controlled trials)
- **C**: Fair evidence (cohort studies, case-control)
- **D**: Limited evidence (case reports, expert opinion)

### **Study Design Hierarchy**
1. Systematic reviews & meta-analyses
2. Randomized controlled trials (RCTs)
3. Cohort studies
4. Case-control studies
5. Case series/reports
6. Expert opinion

---

## 🔧 **Advanced Configuration**

### **Custom Settings**
Edit your extension settings in `~/.gemini/extensions/pubmed-gemini/.env`:

```bash
# Optional: Increase search result limits
MAX_SEARCH_RESULTS=20

# Optional: Enable debug logging
DEBUG_MODE=true
```

### **Manual Installation**
If automatic setup fails:

```bash
# 1. Install Python dependencies
pip3 install httpx rich mcp

# 2. Install Node.js dependencies
cd ~/.gemini/extensions/pubmed-gemini
npm install

# 3. Build the extension
npm run build

# 4. Link for development
gemini extensions link .
```

---

## 🐛 **Troubleshooting**

### **Extension Not Loading**
```bash
# Check if extension is installed
gemini extensions list

# Reinstall if needed
gemini extensions install https://github.com/avivlyweb/pubmed-gemini-extension
```

### **Commands Not Working**
```bash
# Restart Gemini CLI
# Try: gemini --restart

# Check Node.js and Python versions
node --version  # Should be 18+
python3 --version  # Should be 3.8+
```

### **Search Errors**
- Ensure internet connection
- Check PubMed API availability
- Try simpler search terms

### **Performance Issues**
- Reduce `max_results` parameter
- Use specific clinical terms
- Limit concurrent searches

---

## 🤝 **Contributing**

We welcome contributions! This is an open-source project for advancing medical research accessibility.

### **Ways to Contribute**
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/avivlyweb/pubmed-gemini-extension/issues)
- 💡 **Feature Requests**: Suggest new medical research features
- 📖 **Documentation**: Improve guides and examples
- 🔧 **Code**: Submit pull requests for enhancements

### **Development Setup**
```bash
# Clone the repository
git clone https://github.com/avivlyweb/pubmed-gemini-extension.git
cd pubmed-gemini-extension

# Install dependencies
npm install
npm run build

# Link for development
gemini extensions link .
```

---

## 📜 **License**

**MIT License** - Free for educational, research, and non-commercial use.

See [LICENSE](LICENSE) for full terms.

---

## 🙏 **Credits & Acknowledgments**

### **Open Source Libraries**
- **Gemini CLI**: For the amazing extension platform
- **ClinicalBERT**: For medical language understanding
- **PubMed API**: For access to medical literature
- **MCP SDK**: For model-tool integration

### **Research Standards**
- **PICO Framework**: For clinical question structuring
- **GRADE Approach**: For evidence quality assessment
- **Cochrane Methods**: For systematic review standards

---

## 📞 **Support**

### **Documentation**
- 📖 [Complete Installation Guide](GEMINI_EXTENSION_MANUAL.md)
- 🎯 [Quick Reference](QUICK_REFERENCE.md)
- 🧪 [Test Script](TEST_MEDICAL_RESEARCH.sh)

### **Community**
- 💬 **Discussions**: [GitHub Discussions](https://github.com/avivlyweb/pubmed-gemini-extension/discussions)
- 🐛 **Issues**: [GitHub Issues](https://github.com/avivlyweb/pubmed-gemini-extension/issues)
- 📧 **Email**: For sensitive research questions

### **Educational Use**
This tool is designed for **learning and research purposes**. For medical decisions, always consult qualified healthcare professionals.

---

## 🎊 **Impact**

**This extension democratizes access to medical research by:**

- 🔓 **Removing paywalls** from medical knowledge
- 🎓 **Supporting education** in healthcare fields
- 🔬 **Accelerating research** through AI assistance
- 🌍 **Promoting evidence-based** medical practice
- 🤝 **Bridging gaps** between research and clinical care

**Together, we're making medical science more accessible to everyone!** 🌟

---

*Made with ❤️ for the global medical research community* 🦸‍♂️🦸‍♀️

**#MedicalResearch #EvidenceBasedMedicine #OpenScience #AI**