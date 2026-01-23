# PubMed Gemini Extension

> **Your AI Research Assistant for 35+ Million Medical Studies**

[![Version](https://img.shields.io/badge/version-2.6.0-blue.svg)](https://github.com/avivlyweb/pubmed-gemini-extension/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PubMed](https://img.shields.io/badge/PubMed-35M%2B%20articles-orange.svg)](https://pubmed.ncbi.nlm.nih.gov/)

---

## Installation

### Method 1: Official Gemini CLI (Recommended)

If you already have Gemini CLI installed:
```bash
gemini extensions install github:avivlyweb/pubmed-gemini-extension
```

That's it! The extension will be ready to use.

---

### Method 2: Quick Install Script

**Mac or Linux:**

**Step 1:** Open Terminal (search "Terminal" in Spotlight)

**Step 2:** Copy and paste this command, then press Enter:
```bash
curl -fsSL https://raw.githubusercontent.com/avivlyweb/pubmed-gemini-extension/main/install.sh | bash
```

**Step 3:** Wait for "Installation complete!" message (about 1-2 minutes)

---

**Windows:**

**Step 1:** Open PowerShell as Administrator
- Press Windows key
- Type "PowerShell"
- Right-click → "Run as administrator"

**Step 2:** Copy and paste this command, then press Enter:
```powershell
irm https://raw.githubusercontent.com/avivlyweb/pubmed-gemini-extension/main/install.ps1 | iex
```

**Step 3:** Wait for "Installation complete!" message (about 1-2 minutes)

---

## Start Using It

After installation, open a new terminal/command prompt and type:
```
gemini
```

Then ask any medical research question:
```
Does yoga help with anxiety?
```

That's it! Gemini will search PubMed and give you an evidence-based answer.

---

## What Can You Do?

| You Ask | You Get |
|---------|---------|
| "Does yoga help anxiety?" | Evidence verdict from 15+ studies with quality weighting |
| "Find COPD exercise studies" | Ranked articles with trust scores & direct PDF links |
| "Export those to BibTeX" | Ready-to-use citations for your paper |
| "Is this treatment effective?" | AI synthesis with clinical bottom line |

**One command. PhD-level analysis. Seconds.**

---

## New in v2.5 - Key Findings & Contradiction Explainer

### See the Numbers That Matter

Every study now shows the **actual statistical results**:

```
KEY FINDING:
  Statement: "Yoga significantly reduced anxiety scores compared to waitlist control"
  Direction: POSITIVE
  Effect Size: SMD = 0.77 (medium effect)
  P-value: p < 0.001
  95% CI: [0.52, 1.02]
  Practical Significance: MEDIUM
```

**What gets extracted:**
| Metric | Example | Why It Matters |
|--------|---------|----------------|
| Effect Size | SMD=0.77, 34% reduction, OR=0.65 | How big is the effect? |
| P-value | p<0.001, p=0.03 | Is it statistically significant? |
| Confidence Interval | 95% CI [0.52, 1.02] | How precise is the estimate? |
| Practical Significance | Large/Medium/Small | Does it matter clinically? |

### Why Do Studies Disagree?

When evidence conflicts, you now get an **explanation**:

```
CONTRADICTION ANALYSIS:
  Conflicting results: 8 studies support, 3 oppose

  Key Differences Identified:
  - Intervention Dose: Supporting studies: 4000 IU/day. Opposing: 400 IU/day
  - Study Duration: Supporting studies: 24 weeks. Opposing: 8 weeks
  - Population Age: Supporting: elderly (≥65). Opposing: adults 30-50

  SYNTHESIS: The conflicting results suggest that dose may be critical 
  for effectiveness, and longer treatment periods may be needed.
```

---

## New in v2.4 - Study Snapshots & Full-Text Links

### Instant Article Understanding

Every article now comes with a **2-sentence AI snapshot**:

```
"This systematic review with 319 participants (2018) examined yoga for anxiety. 
 Results showed significant reduction in anxiety scores (p<0.001) at 8 weeks."
```

### One-Click Full Text Access

Direct links to read the full paper:

| Link Type | What You Get |
|-----------|--------------|
| **PubMed** | Abstract page |
| **DOI** | Publisher's site |
| **PMC Full Text** | Free full article (when available) |
| **PMC PDF** | Direct PDF download |
| **Open Access** | Badge showing if it's free to read |

---

## All Features at a Glance

### Search & Discovery
- **Smart Search** - Natural language queries understood
- **35M+ Articles** - Full PubMed database access
- **Relevance Ranking** - Best matches first

### Evidence Analysis
- **Trust Scores** - Each article rated 0-100
- **Evidence Grades** - A/B/C/D quality classification
- **Evidence Compass** - Weighted verdict across all studies
- **Trend Analysis** - Is evidence strengthening or weakening?

### AI Intelligence
- **Key Findings Extraction** - Effect sizes, p-values, confidence intervals
- **Contradiction Explainer** - Why do studies disagree?
- **Study Snapshots** - 2-sentence summaries per article
- **PICO Extraction** - Automatic clinical question structuring
- **Finding Direction** - Positive/negative/neutral/mixed detection
- **Sample Size** - Extracted automatically from abstracts

### Export & Integration
- **BibTeX** - For LaTeX documents
- **RIS** - For Zotero, Mendeley, EndNote
- **EndNote** - Native format support
- **Clickable URLs** - All links ready to use

---

## Commands

| Command | Purpose | Example |
|---------|---------|---------|
| Just ask naturally | Gemini understands you | "Does vitamin D help with depression?" |
| `/pubmed:search` | Find articles on a topic | `/pubmed:search vitamin D bone health` |
| `/pubmed:synthesis` | Full AI analysis with Evidence Compass | `/pubmed:synthesis yoga for anxiety` |
| `/pubmed:analyze` | Deep-dive on one article | `/pubmed:analyze 34580864` |
| `/pubmed:export` | Export citations | `/pubmed:export format=bibtex query="COPD exercise"` |

---

## Example: Full Research Synthesis

```
You: /pubmed:synthesis does yoga help anxiety

Gemini: Analyzing 15 PubMed articles...
```

### What You'll See:

#### 1. Evidence Compass
```
VERDICT: Strong Support

Support [####################] 100%
Against [--------------------] 0%

Studies: 12 support | 2 neutral | 1 against
Confidence: HIGH

CLINICAL BOTTOM LINE:
Strong evidence supports yoga for anxiety reduction.
3 systematic reviews confirm benefit. Consider for clinical practice.
```

#### 2. Top Articles with Snapshots
```
1. [A] Trust: 89/100 - Yoga for anxiety: A systematic review
   Journal: Depression and Anxiety | 2018
   
   SNAPSHOT: "This meta-analysis of 17 RCTs with 501 participants found yoga 
   significantly reduced anxiety (SMD=-0.77). Effects were sustained at 
   3-month follow-up."
   
   Finding: POSITIVE | Sample Size: 501
   
   LINKS:
   - PubMed: https://pubmed.ncbi.nlm.nih.gov/29697885/
   - DOI: https://doi.org/10.1002/da.22762
   - PMC Full Text: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6334...
   - PDF: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6334.../pdf/
   - Open Access: YES
```

#### 3. Evidence Trend
```
TREND: Stable (consistent positive findings)
Recent studies (2020-2024): 85% support
Older studies (2015-2019): 82% support
Research Activity: ACTIVE (12 studies in last 3 years)
```

#### 4. Export Ready
```
You: Export those to BibTeX

Gemini: Here are your citations:

@article{pmid29697885,
  author = {Cramer, Holger and Lauche, Romy...},
  title = {Yoga for anxiety: A systematic review...},
  journal = {Depression and anxiety},
  year = {2018},
  doi = {10.1002/da.22762}
}
...
```

---

## Who Is This For?

### Students
- Find sources for your paper in seconds
- Get instant quality assessment
- Export citations directly to your reference manager

### Clinicians
- Quick evidence check before recommending treatment
- See if latest research supports your practice
- Understand confidence level of findings

### Researchers
- Literature review acceleration
- Identify research gaps automatically
- Track evidence trends over time

### Everyone
- Understand if a health claim is backed by science
- Get plain-language summaries of complex studies
- Access full-text articles when available

---

## Understanding the Output

### Trust Scores (0-100)

| Score | Quality | Meaning |
|-------|---------|---------|
| 80-100 | Excellent | High-quality methodology, large sample |
| 60-79 | Good | Solid study with minor limitations |
| 40-59 | Fair | Useful but interpret with caution |
| 0-39 | Limited | Preliminary or low-quality evidence |

### Evidence Grades

| Grade | Study Type | Weight in Compass |
|-------|------------|-------------------|
| **A** | Systematic reviews, meta-analyses | 4x |
| **B** | Randomized controlled trials | 2.5x |
| **C** | Cohort, case-control studies | 1.5x |
| **D** | Case reports, expert opinion | 0.5x |

### Finding Direction

| Direction | Meaning |
|-----------|---------|
| **Positive** | Study supports the intervention/hypothesis |
| **Negative** | Study finds no effect or harm |
| **Neutral** | Inconclusive or needs more research |
| **Mixed** | Some outcomes positive, others not |

---

## Pro Tips

### 1. Use Natural Language
Instead of keywords, ask questions:
```
Does meditation reduce cortisol levels in stressed adults?
```

### 2. Be Specific About Population
```
yoga anxiety in elderly       # Better
yoga anxiety                   # Good
yoga                          # Too broad
```

### 3. Check Open Access First
Look for articles with `open_access: true` - you can read the full text immediately!

### 4. Trust the Weighted Score
If 5 case reports say "no" but 1 meta-analysis says "yes", the weighted score correctly favors the meta-analysis.

### 5. Export While You Research
```
/pubmed:synthesis your topic
# Review the results, then:
Export those top 5 articles to RIS format
```

---

## Example Queries

### General Health
```
/pubmed:search is intermittent fasting safe
/pubmed:search does sleep affect weight
/pubmed:synthesis coffee and heart health
```

### Clinical Questions
```
/pubmed:synthesis best exercises for knee osteoarthritis
/pubmed:synthesis CBT vs medication for depression
/pubmed:synthesis vitamin D supplementation in elderly
```

### Research Questions
```
/pubmed:synthesis gut microbiome and neuroinflammation
/pubmed:synthesis epigenetic markers in cancer prevention
/pubmed:synthesis HPA-axis dysfunction in treatment-resistant depression
```

---

## Version History

| Version | Features |
|---------|----------|
| **2.6.0** | Official Gemini CLI install support, GitHub Releases distribution |
| **2.5.0** | Key Findings Extraction (effect sizes, p-values, CIs), Contradiction Explainer |
| **2.4.0** | Study Snapshots, Full-Text Links (PMC/PDF), Open Access detection |
| **2.3.0** | Citation Export (BibTeX, RIS, EndNote) |
| **2.2.0** | Evidence Trend Analysis, Sample Size Weighting, Research Activity |
| **2.1.0** | Evidence Compass with weighted verdicts |
| **2.0.0** | Enhanced PICO, 3-tier complexity detection, 10+ medical domains |
| **1.0.0** | Core search, trust scores, basic PICO |

---

## Troubleshooting

### "gemini" command not found
The installer will tell you if Gemini CLI needs to be installed. Follow the link it provides.

### Extension not loading or showing errors
**Mac/Linux:** Run this again:
```bash
curl -fsSL https://raw.githubusercontent.com/avivlyweb/pubmed-gemini-extension/main/install.sh | bash
```

**Windows:** Run this again in PowerShell (as Admin):
```powershell
irm https://raw.githubusercontent.com/avivlyweb/pubmed-gemini-extension/main/install.ps1 | iex
```

Then restart Gemini by closing and reopening your terminal.

### "No results found"
- Try broader search terms
- Check spelling
- Use fewer keywords

### Need Help?
[Open an issue on GitHub](https://github.com/avivlyweb/pubmed-gemini-extension/issues)

---

## What Gets Installed?

The installer automatically sets up:
- Python (if not already installed)
- Required packages
- The PubMed extension

Everything is installed in:
- Mac/Linux: `~/.gemini/extensions/pubmed-gemini/`
- Windows: `%USERPROFILE%\.gemini\extensions\pubmed-gemini\`

---

## Important Note

This tool is for **research and educational purposes**. Always consult qualified healthcare professionals for medical decisions.

---

## Contributing

Found a bug? Have an idea? [Open an issue](https://github.com/avivlyweb/pubmed-gemini-extension/issues) or submit a PR!

---

## License

MIT License - Free to use, modify, and distribute.

---

<p align="center">
  <b>Made with science by <a href="https://physiotherapy.ai/">Aviv at Avivly</a></b>
  <br><br>
  Searching 35+ million studies so you don't have to.
</p>
