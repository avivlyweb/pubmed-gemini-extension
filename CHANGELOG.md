# Changelog

All notable changes to the **PubMed Gemini Extension** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

### Planned for v2.1.0
- Citation export (BibTeX, RIS, EndNote)
- Batch processing for multiple queries
- Custom PICO pattern definitions
- Search history and favorites

### Planned for v2.2.0
- Integration with Cochrane Library
- Multi-language abstract translation
- Evidence synthesis across multiple queries
- Research gap visualization

---

*For the latest updates, see the [GitHub Releases](https://github.com/avivlyweb/pubmed-gemini-extension/releases) page.*
