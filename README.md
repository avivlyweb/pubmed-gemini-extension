# PubMed Gemini Extension

**Search 35+ million medical research articles with AI-powered analysis - right from your terminal.**

---

## What Does This Do?

This extension lets you search PubMed (the world's largest medical research database) using simple commands. It automatically:

- Finds relevant medical research articles
- Scores each article's trustworthiness (0-100)
- Grades evidence quality (A, B, C, D)
- Summarizes findings in plain language

**No medical background required. No coding required.**

---

## Quick Install (2 Minutes)

### Step 1: Install Gemini CLI

First, you need Gemini CLI. Open your terminal and run:

```bash
npm install -g @google/gemini-cli
```

> Don't have npm? Install Node.js first from [nodejs.org](https://nodejs.org)

### Step 2: Install This Extension

**Mac or Linux** - Copy and paste this:
```bash
curl -fsSL https://raw.githubusercontent.com/avivlyweb/pubmed-gemini-extension/main/install.sh | bash
```

**Windows (PowerShell as Admin)** - Copy and paste this:
```powershell
irm https://raw.githubusercontent.com/avivlyweb/pubmed-gemini-extension/main/install.ps1 | iex
```

The installer automatically sets up everything (Node.js, Python, dependencies).

### Step 3: Start Using It

```bash
gemini
```

Then type any of these commands:

```
/pubmed:search does yoga help anxiety
/pubmed:search best exercises for COPD patients
/pubmed:search vitamin D and bone health
```

---

## Available Commands

| Command | What It Does | Example |
|---------|--------------|---------|
| `/pubmed:search` | Search for medical research | `/pubmed:search does coffee affect sleep` |
| `/pubmed:analyze` | Analyze one specific article | `/pubmed:analyze 34580864` |
| `/pubmed:synthesis` | Get a full research summary | `/pubmed:synthesis meditation for stress` |

---

## Example Output

```
You: /pubmed:search does exercise help depression

Gemini: Found 8 articles from PubMed:

1. [A] Trust: 84/100 - "Exercise as treatment for depression: A meta-analysis"
   Journal: JAMA Psychiatry | 2023 | Systematic Review
   
2. [B] Trust: 76/100 - "Walking programs for mild depression"
   Journal: BMJ | 2022 | Randomized Controlled Trial

Clinical Recommendation: Strong evidence supports exercise as an 
effective treatment for depression, particularly aerobic exercise 
3-5 times per week.
```

---

## Understanding the Results

### Trust Scores
- **80-100**: Excellent quality research
- **60-79**: Good quality research  
- **40-59**: Fair quality research
- **0-39**: Limited evidence

### Evidence Grades
- **A**: Best evidence (systematic reviews, meta-analyses)
- **B**: Good evidence (randomized trials)
- **C**: Fair evidence (observational studies)
- **D**: Limited evidence (case reports, opinions)

---

## Troubleshooting

**"Command not found"**
```bash
# Make sure Gemini CLI is installed:
npm install -g @google/gemini-cli
```

**"Extension not working"**
```bash
# Reinstall the extension:
curl -fsSL https://raw.githubusercontent.com/avivlyweb/pubmed-gemini-extension/main/install.sh | bash
```

**"No results found"**
- Try simpler search terms
- Check your internet connection

---

## Uninstall

```bash
rm -rf ~/.pubmed-gemini-extension ~/.gemini/extensions/pubmed-gemini
```

---

## Requirements

- **Gemini CLI** - Install from [gcli.dev](https://gcli.dev)
- **Internet connection** - To search PubMed

The installer handles Node.js and Python automatically.

---

## Important Note

This tool is for **research and educational purposes only**. Always consult healthcare professionals for medical decisions.

---

## License

MIT License - Free to use and modify.

---

Made with love by **Aviv at [Avivly]([https://avivly.com](https://physiotherapy.ai/))**

