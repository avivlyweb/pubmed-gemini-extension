# PubMed Gemini Extension

**Search 35+ million medical research articles with AI-powered analysis - right from your terminal.**

**Version 2.1.0** - Now with Evidence Compass!

---

## What's New in v2.1 - Evidence Compass

**Evidence Compass** is our killer feature that goes beyond simple "consensus meters":

| Feature | Other Tools | Evidence Compass |
|---------|-------------|------------------|
| Shows % agreement | Yes | Yes |
| **Weighted by study quality** | No | **Yes** (Grade A counts 4x more than Grade D) |
| **Confidence level** | No | **Yes** (High/Medium/Low with reasons) |
| **Breakdown by grade** | No | **Yes** (See how A/B/C/D studies voted) |
| **Clinical bottom line** | No | **Yes** (Actionable summary) |

### Example Evidence Compass Output

```
EVIDENCE COMPASS

  VERDICT: Strong Support

  Support ████████████████████ 100% (weighted)
  Against ░░░░░░░░░░░░░░░░░░░░ 0%

  Raw agreement: 100% | Weighted: 100%

  Studies: 4 support, 0 against, 1 neutral

  EVIDENCE BREAKDOWN BY GRADE:
    Grade A: 3 support, 0 against
    Grade B: 1 support, 0 against

  CONFIDENCE: High
    • 5 studies analyzed (moderate volume)
    • 5 high-quality studies (Grade A/B)
    • High-quality studies agree (all support)
    • Strong consistency across studies (>80% agree)

  CLINICAL BOTTOM LINE:
    Strong evidence supports this intervention. 
    3 systematic review(s)/meta-analysis confirm benefit. 
    Consider for clinical practice.
```

---

## All Features

### Core Features
- **PubMed Search** - Access 35+ million medical research articles
- **Trust Scoring** - Each article scored 0-100 for quality
- **Evidence Grades** - A/B/C/D grades based on study design
- **PICO Analysis** - Automatic clinical question structuring

### v2.0 Features
- **Smart Query Understanding** - Detects casual, clinical, or research-level questions
- **Medical Domain Detection** - Identifies specialty (geriatric, orthopedics, neurology, etc.)
- **Intelligent Suggestions** - Tips to improve your search
- **100+ Pre-built Patterns** - Common clinical questions recognized instantly

### v2.1 Features (NEW!)
- **Evidence Compass** - Weighted verdict with confidence scoring
- **Quality-Weighted Percentages** - Grade A studies count more than case reports
- **Grade Breakdown** - See support/against by evidence quality
- **Clinical Bottom Line** - Actionable summary for practice

---

## Quick Install (2 Minutes)

### Step 1: Install Gemini CLI

```bash
npm install -g @google/gemini-cli
```

> Don't have npm? Install Node.js first from [nodejs.org](https://nodejs.org)

### Step 2: Install This Extension

**Mac or Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/avivlyweb/pubmed-gemini-extension/main/install.sh | bash
```

**Windows (PowerShell as Admin):**
```powershell
irm https://raw.githubusercontent.com/avivlyweb/pubmed-gemini-extension/main/install.ps1 | iex
```

### Step 3: Start Using It

```bash
gemini
```

---

## Available Commands

| Command | What It Does | Example |
|---------|--------------|---------|
| `/pubmed:search` | Search for medical research | `/pubmed:search does coffee affect sleep` |
| `/pubmed:analyze` | Analyze one specific article | `/pubmed:analyze 34580864` |
| `/pubmed:synthesis` | Get full research summary with Evidence Compass | `/pubmed:synthesis meditation for stress` |

---

## Example: Full Research Synthesis

```
You: /pubmed:synthesis exercises to improve walking in COPD patients

Gemini: 

================================================================================
ENHANCED PICO ANALYSIS
================================================================================
  Complexity:   Level 2 (Clinical)
  Domain:       Rehabilitation
  Confidence:   100/100
  
  Population:   Patients with COPD (GOLD stages I-IV)
  Intervention: Exercise training (aerobic, resistance, or combined)
  Comparison:   Usual care or no exercise
  Outcome:      6-minute walk distance

  Suggestion: Consider including 6-minute walk test as an outcome measure

================================================================================
ARTICLES FOUND
================================================================================
1. [A] Trust: 84/100 - "Impact of resistance training on the 6-minute walk test..."
   Journal: Annals of Physical Medicine | 2022 | Systematic Review

2. [A] Trust: 81/100 - "Effects of exercise-based pulmonary rehabilitation..."
   Journal: Therapeutic Advances | 2023 | Systematic Review

3. [A] Trust: 80/100 - "Effect of pulmonary rehabilitation programs..."
   Journal: Respiratory Investigation | 2020 | Systematic Review

4. [B] Trust: 70/100 - "Impact of inspiratory muscle training in COPD..."
   Journal: European Respiratory Journal | 2011 | Systematic Review

5. [B] Trust: 69/100 - "Effects of specific inspiratory muscle training..."
   Journal: PLoS ONE | 2021 | RCT

================================================================================
EVIDENCE COMPASS
================================================================================

  VERDICT: Strong Support

  Support ████████████████████ 100% (weighted)
  Against ░░░░░░░░░░░░░░░░░░░░ 0%

  Raw agreement: 100% | Weighted: 100%

  Studies: 4 support, 0 against, 1 neutral

  EVIDENCE BREAKDOWN BY GRADE:
    Grade A: 3 support, 0 against
    Grade B: 1 support, 0 against

  CONFIDENCE: High
    • 5 studies analyzed (moderate volume)
    • 5 high-quality studies (Grade A/B)
    • High-quality studies agree (all support)
    • Strong consistency across studies (>80% agree)

  CLINICAL BOTTOM LINE:
    Strong evidence supports this intervention. 
    3 systematic review(s)/meta-analysis confirm benefit. 
    Consider for clinical practice.

================================================================================
EVIDENCE SUMMARY
================================================================================
  Average Trust Score: 76.8/100
  Score Range: 69-84
  Grade Distribution: A=3, B=2, C=0, D=0
  Evidence Quality: HIGH

================================================================================
RECOMMENDATIONS
================================================================================
  - Strong evidence supports consideration in clinical practice
  - Consider long-term follow-up studies
```

---

## Example Queries by User Type

### For Everyone (Casual)
```
/pubmed:search is coffee bad for you
/pubmed:search what foods are healthy
/pubmed:search does sleep affect memory
```

### For Healthcare Professionals (Clinical)
```
/pubmed:synthesis does yoga help anxiety
/pubmed:synthesis best exercises for COPD patients
/pubmed:synthesis vitamin D for bone health in elderly
/pubmed:synthesis physical therapy for chronic back pain
```

### For Researchers (PhD-level)
```
/pubmed:synthesis effect of SSRI on HPA-axis in treatment-resistant depression
/pubmed:synthesis gut microbiome interventions for neonatal neuroinflammation
/pubmed:synthesis epigenetic markers in precision cancer prevention
```

---

## Understanding Evidence Compass

### Verdict Types
| Verdict | Weighted Score | Meaning |
|---------|---------------|---------|
| **Strong Support** | 80-100% | High-quality studies consistently support |
| **Moderate Support** | 60-79% | Majority of evidence supports |
| **Mixed Evidence** | 40-59% | Studies show conflicting results |
| **Moderate Against** | 20-39% | Majority of evidence does not support |
| **Strong Against** | 0-19% | High-quality studies consistently oppose |

### Why Weighted is Better Than Raw

| Study Type | Raw Count | Weighted Impact |
|------------|-----------|-----------------|
| Systematic Review (Grade A) | 1 vote | 4x weight |
| RCT (Grade B) | 1 vote | 2.5x weight |
| Cohort Study (Grade C) | 1 vote | 1.5x weight |
| Case Report (Grade D) | 1 vote | 0.5x weight |

**Example:** If 3 case reports say "no effect" but 1 systematic review says "effective":
- Raw: 75% against
- Weighted: 73% **support** (because the systematic review counts more)

### Confidence Levels
| Level | Meaning |
|-------|---------|
| **High** | 10+ studies, multiple Grade A/B, strong agreement |
| **Medium** | 5-9 studies, some Grade A/B, moderate agreement |
| **Low** | <5 studies, few Grade A/B, or conflicting results |

---

## Understanding PICO Analysis

Every search is analyzed using the PICO framework:

| Component | Description | Example |
|-----------|-------------|---------|
| **P**opulation | Who is being studied? | Patients with COPD |
| **I**ntervention | What treatment/action? | Exercise training |
| **C**omparison | Compared to what? | Usual care |
| **O**utcome | What result measured? | 6-minute walk distance |

### Complexity Levels
- **Level 1 (Casual)**: General health questions from the public
- **Level 2 (Clinical)**: Healthcare professional questions with specific conditions
- **Level 3 (Research)**: PhD-level questions with biomarkers and mechanisms

### Medical Domains Detected
Geriatric, Orthopedics, Neurology, Rehabilitation, Cardiology, Pulmonology, Psychiatry, Oncology, Pediatrics, Endocrinology

---

## Trust Scores & Evidence Grades

### Trust Scores
| Score | Quality |
|-------|---------|
| 80-100 | Excellent |
| 60-79 | Good |
| 40-59 | Fair |
| 0-39 | Limited |

### Evidence Grades
| Grade | Study Types |
|-------|-------------|
| **A** | Systematic reviews, meta-analyses |
| **B** | Randomized controlled trials |
| **C** | Cohort, case-control studies |
| **D** | Case reports, expert opinion |

---

## Pro Tips

1. **Use `/pubmed:synthesis` for Evidence Compass**
   - This command gives you the full weighted analysis

2. **Be specific about the population**
   - Instead of: "exercise for breathing"
   - Try: "exercise for COPD patients"

3. **Include the outcome you care about**
   - Instead of: "yoga anxiety"
   - Try: "does yoga reduce anxiety symptoms"

4. **Check the confidence level**
   - High = Trust the verdict
   - Low = More research needed

5. **Look at the grade breakdown**
   - If all Grade A studies agree, that's strong evidence
   - If only Grade D studies support, be cautious

---

## Troubleshooting

**"Command not found"**
```bash
npm install -g @google/gemini-cli
```

**"Extension not working"**
```bash
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

## Version History

- **v2.1.0** - Evidence Compass with weighted verdict scoring
- **v2.0.0** - Enhanced PICO extraction with tiered complexity detection
- **v1.0.0** - Initial release with basic search and trust scoring

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

Made with love by **Aviv at [Avivly](https://physiotherapy.ai/)**
