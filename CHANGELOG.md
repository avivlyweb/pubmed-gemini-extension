# Changelog

All notable changes to the **PubMed Gemini Extension** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.2.0] - 2025-01-19

### Added

#### Evidence Trend Analysis
Understand how evidence is evolving over time:

- **Recency Trend Detection**: Compare recent vs older study results
  - `strengthening`: Support increasing over time (↑)
  - `weakening`: Support decreasing over time (↓)
  - `stable`: Consistent evidence across time periods (→)
  - Shows recent support % vs older support %

- **Research Activity Level**: How actively is this topic being researched?
  - `active`: 5+ studies in the past 5 years
  - `moderate`: 2-4 recent studies
  - `limited`: 0-1 recent studies

- **Sample Size Weighting**: Larger studies carry more weight
  - Studies with bigger sample sizes contribute more to the verdict
  - Shown separately from quality-weighted score when meaningfully different

- **Enhanced ASCII Display**: New EVIDENCE TREND section
  ```
  ║  EVIDENCE TREND                                              ║
  ║  ──────────────────                                          ║
  ║    → All 5 studies are from the past 5 years                 ║
  ║    Studies: 5 recent, 0 older (2022-2023)                    ║
  ║    Research activity: active                                 ║
  ```

- **Year Range Tracking**: See the full span of evidence (oldest to newest)

### Technical
- Added `RecencyTrendResult` dataclass
- Added `_extract_year()`, `_analyze_recency_trend()`, `_calculate_sample_size_weighted_score()` methods
- Extended `EvidenceCompassResult` with `recency_trend` and `sample_size_weighted_percent` fields
- Updated JSON output with full recency trend data

---

## [2.1.0] - 2025-01-19

### Added

#### Evidence Compass - Weighted Evidence Analysis System

A new feature that goes beyond simple "consensus meters" by weighting evidence by quality:

- **Weighted Verdict Scoring**: Studies are weighted by evidence grade
  - Grade A (Systematic Reviews): 4x weight
  - Grade B (RCTs): 2.5x weight
  - Grade C (Observational): 1.5x weight
  - Grade D (Case Reports): 0.5x weight

- **Verdict Types**:
  - Strong Support (80-100% weighted)
  - Moderate Support (60-79%)
  - Mixed Evidence (40-59%)
  - Moderate Against (20-39%)
  - Strong Against (0-19%)

- **Confidence Level Calculation**: High/Medium/Low with detailed reasons
  - Based on number of studies
  - Based on presence of Grade A/B studies
  - Based on agreement among high-quality studies
  - Based on overall consistency

- **Grade Breakdown**: See exactly how studies voted by evidence quality
  ```
  Grade A: 3 support, 0 against
  Grade B: 1 support, 0 against
  ```

- **Clinical Bottom Line**: Actionable summary for practice
  - "Strong evidence supports this intervention..."
  - "Consider for clinical practice..."

- **Visual ASCII Display**: Progress bars for terminal output
  ```
  Support ████████████████████ 100% (weighted)
  Against ░░░░░░░░░░░░░░░░░░░░ 0%
  ```

- **Sentiment Analysis**: Classifies each study as support/against/neutral
  - Analyzes abstract and title text
  - Weights conclusion sections more heavily
  - Context-aware based on query terms

### Technical
- Added `EvidenceCompass` class (~400 lines)
- Added `EvidenceCompassResult` dataclass
- Integrated with `ResearchSynthesizer` for `/pubmed:synthesis` command
- Updated test suite with Evidence Compass validation

---

## [2.0.0] - 2025-01-19

### Added

#### Enhanced PICO Extraction System
- **3-Tier Complexity Detection**: Automatically identifies query sophistication level
  - Level 1 (Casual): General public questions like "Is coffee bad for you?"
  - Level 2 (Clinical): Healthcare professional questions like "Does yoga help anxiety?"
  - Level 3 (Research): PhD-level questions with biomarkers and mechanisms

- **Medical Domain Detection**: Identifies the primary medical specialty
  - Geriatric (elderly care, falls, dementia)
  - Orthopedics (bones, joints, back pain)
  - Neurology (brain, stroke, Parkinson's)
  - Rehabilitation (physical therapy, mobility)
  - Cardiology (heart, blood pressure)
  - Pulmonology (lungs, COPD, asthma)
  - Psychiatry (depression, anxiety, mental health)
  - Oncology (cancer)
  - Pediatrics (children, neonates)
  - Endocrinology (diabetes, thyroid, obesity)

- **Common PICO Patterns Database**: Pre-defined patterns for common queries
  - yoga + anxiety → GAD-7, STAI outcomes
  - exercise + COPD → 6-minute walk test
  - vitamin D + elderly → bone mineral density
  - meditation + stress → perceived stress scale
  - physical therapy + back pain → VAS/NRS pain scales

- **Interactive Suggestions**: AI-powered tips to improve query specificity
  - Population refinement suggestions
  - Validated outcome measure recommendations
  - Comparison group suggestions

- **Confidence Scoring**: 0-100 score indicating extraction quality

- **Optimized Search Terms**: Auto-generated PubMed-optimized keywords

### Changed
- MCP handler now returns enhanced PICO metadata in responses
- Improved population extraction with condition-based patterns
- Better intervention detection across 5 categories (exercise, therapy, pharmacological, supplements, other)
- Enhanced outcome extraction with domain-specific defaults

### Technical
- Added `EnhancedPICOAnalysis` dataclass with full metadata
- Refactored `PICOExtractor` class with 600+ lines of pattern matching
- Added comprehensive test suite with 9 test cases
- All tests pass including full PubMed integration test

---

## [1.0.0] - 2025-01-15

### Added
- **Core MCP Server**: Node.js wrapper for Python PubMed analysis engine
- **Custom Commands**: `/pubmed:search`, `/pubmed:analyze`, `/pubmed:synthesis`
- **Medical Research Tools**:
  - Enhanced PubMed search with query optimization
  - Article trustworthiness analysis (0-100 trust scores)
  - Research summary generation
- **Quality Assessment Engine**: Automated evaluation of study design and evidence strength
- **Basic PICO Analysis**: Automatic clinical question structuring
- **One-Click Installers**: Bash script for Mac/Linux, PowerShell for Windows

### Technical
- **Gemini CLI Extension Framework**: Full integration with Gemini CLI
- **Model Context Protocol (MCP)**: Standardized AI-tool communication
- **PubMed API Integration**: Direct access to 35+ million medical articles
- **TypeScript/Node.js Wrapper**: Modern extension architecture
- **Python Backend**: Robust medical research analysis engine

---

## Version Numbering

This project uses [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

---

## Upcoming Features

### Planned for v2.3.0
- **Contradiction Explainer**: Why do some studies disagree?
- **Population Matching**: Flag when studies used different populations
- Citation export (BibTeX, RIS, EndNote)
- Integration with Cochrane Library

### Planned for v3.0.0
- **Effect Size Extraction**: How big is the effect?
- **NNT Calculator**: Number needed to treat
- Multi-language abstract translation

---

*For the latest updates, see the [GitHub Releases](https://github.com/avivlyweb/pubmed-gemini-extension/releases) page.*
