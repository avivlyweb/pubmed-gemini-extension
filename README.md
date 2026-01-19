# PubMed Gemini Extension

**Search 35+ million medical research articles with AI-powered analysis - right from your terminal.**

**Version 2.0.0** - Now with Enhanced PICO Extraction!

---

## What's New in v2.0

- **Smart Query Understanding** - Automatically detects if you're a casual user, healthcare professional, or researcher
- **Medical Domain Detection** - Identifies your specialty (geriatric, orthopedics, neurology, rehabilitation, etc.)
- **Intelligent Suggestions** - Get tips to improve your search for better results
- **100+ Pre-built Patterns** - Common clinical questions are recognized instantly

---

## What Does This Do?

This extension lets you search PubMed (the world's largest medical research database) using simple commands. It automatically:

- Finds relevant medical research articles
- Scores each article's trustworthiness (0-100)
- Grades evidence quality (A, B, C, D)
- Analyzes your question using the PICO framework
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

## Example Queries by User Type

### For Everyone (Casual)
```
/pubmed:search is coffee bad for you
/pubmed:search what foods are healthy
/pubmed:search does sleep affect memory
```

### For Healthcare Professionals (Clinical)
```
/pubmed:search does yoga help anxiety
/pubmed:search best exercises for COPD patients
/pubmed:search vitamin D for bone health in elderly
/pubmed:search physical therapy for chronic back pain
```

### For Researchers (PhD-level)
```
/pubmed:search effect of SSRI on HPA-axis in treatment-resistant depression
/pubmed:search gut microbiome interventions for neonatal neuroinflammation
/pubmed:search epigenetic markers in precision cancer prevention
```

---

## Example Output

```
You: /pubmed:search exercises to improve walking in COPD patients

Gemini: 

PICO Analysis:
  Complexity:   Level 2 (Clinical)
  Domain:       Rehabilitation
  Confidence:   100/100
  
  Population:   Patients with COPD (GOLD stages I-IV)
  Intervention: Exercise training (aerobic, resistance, or combined)
  Comparison:   Usual care or no exercise
  Outcome:      6-minute walk distance

  Suggestion: Consider including 6-minute walk test as an outcome measure

Found 5 articles from PubMed:

1. [A] Trust: 84/100 - "Effects of exercise-based pulmonary rehabilitation..."
   Journal: Therapeutic Advances | 2023 | Systematic Review
   
2. [A] Trust: 81/100 - "Impact of resistance training on the 6-minute walk test..."
   Journal: Annals of Physical Medicine | 2022 | Systematic Review

3. [B] Trust: 70/100 - "Impact of inspiratory muscle training in COPD..."
   Journal: European Respiratory Journal | 2011 | Systematic Review

Evidence Summary:
  Average Trust Score: 76.8/100
  Grade Distribution: A=3, B=2
  Evidence Quality: HIGH

Clinical Recommendation: Strong evidence supports exercise-based 
pulmonary rehabilitation for improving walking ability in COPD patients.
```

---

## Understanding the Results

### Complexity Levels
- **Level 1 (Casual)**: General health questions from the public
- **Level 2 (Clinical)**: Healthcare professional questions with specific conditions
- **Level 3 (Research)**: PhD-level questions with biomarkers and mechanisms

### Medical Domains Detected
- Geriatric (elderly care)
- Orthopedics (bones, joints)
- Neurology (brain, nerves)
- Rehabilitation (physical therapy)
- Cardiology (heart)
- Pulmonology (lungs)
- Psychiatry (mental health)
- Oncology (cancer)
- Pediatrics (children)
- Endocrinology (diabetes, hormones)

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

## PICO Framework

Every search is automatically analyzed using the PICO framework:

| Component | Description | Example |
|-----------|-------------|---------|
| **P**opulation | Who is being studied? | Patients with COPD |
| **I**ntervention | What treatment/action? | Exercise training |
| **C**omparison | Compared to what? | Usual care |
| **O**utcome | What result measured? | 6-minute walk distance |

This helps you get more relevant research results.

---

## Pro Tips

1. **Be specific about the population**
   - Instead of: "exercise for breathing"
   - Try: "exercise for COPD patients"

2. **Include the outcome you care about**
   - Instead of: "yoga anxiety"
   - Try: "does yoga reduce anxiety symptoms"

3. **Use the suggestions**
   - The AI will suggest validated outcome measures (like GAD-7 for anxiety)

4. **Check the confidence score**
   - 80-100%: The AI understood your query well
   - Below 60%: Consider rephrasing

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
- Remove very specific jargon

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

## Version History

- **v2.0.0** - Enhanced PICO extraction with tiered complexity detection
- **v1.0.0** - Initial release with basic search and trust scoring

---

## License

MIT License - Free to use and modify.

---

Made with love by **Aviv at [Avivly](https://physiotherapy.ai/)**
