<div align="center">

![Nagomi Clinical Forensic](docs/images/sakura-banner.svg)

**Forensic-grade clinical research engine for Gemini CLI**

[![Gemini CLI Extension](https://img.shields.io/badge/Gemini_CLI-Extension-4a6a8f?style=flat-square)](https://gcli.dev)
[![PubMed](https://img.shields.io/badge/PubMed-NCBI-7abaed?style=flat-square)](https://pubmed.ncbi.nlm.nih.gov)
[![CrossRef](https://img.shields.io/badge/CrossRef-API-5ac88e?style=flat-square)](https://www.crossref.org)
[![OpenAlex](https://img.shields.io/badge/OpenAlex-API-a080d0?style=flat-square)](https://openalex.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-e87da0?style=flat-square)](#license)

</div>

---

Nagomi (和み) means *calm, balanced clarity*. This extension transforms Gemini CLI into a research engine that searches PubMed, verifies citations, grades evidence quality, and exports bibliographies — with forensic precision.

> [!TIP]
> **Quick start** — two commands and you're searching:
> ```bash
> gemini extensions install https://github.com/avivlyweb/pubmed-gemini-extension
> ```
> Then inside Gemini CLI:
> ```
> /nagomi:search yoga and neuroplasticity
> ```

---

## What It Does

| Capability | Command | Description |
|:--|:--|:--|
| **Evidence Search** | `/nagomi:search` | PICO-optimized PubMed queries with trust scoring |
| **Quality Appraisal** | `/nagomi:analyze` | Methodological audit by PMID with grade assignment |
| **Research Synthesis** | `/nagomi:synthesis` | PhD-level collation across multiple studies |
| **Citation Verification** | `/nagomi:verify` | Detects fabricated authors, mismatched DOIs, anomalies |
| **Bibliography Export** | via tools | BibTeX, RIS, EndNote format generation |

---

## Usage Examples

**Synthesize evidence on a clinical topic:**
```bash
/nagomi:synthesis the effects of running outside on brain function
/nagomi:synthesis pharmacological interventions for neuroinflammation
```

**Verify a citation or DOI:**
```bash
/nagomi:verify 10.1001/jama.2023.12345
/nagomi:verify ~/Documents/dissertation.pdf
```

**Analyze a specific article:**
```bash
/nagomi:analyze 34580864
```

**Export references:**
```bash
/nagomi:export 15612906 format=ris
/nagomi:export "yoga for anxiety" format=bibtex
```

---

## Screenshots

<details>
<summary>Evidence search with PICO analysis</summary>

![Search](docs/images/Screenshot%202026-01-25%20at%2013.41.13.png)

</details>

<details>
<summary>Research synthesis output</summary>

![Synthesis](docs/images/Screenshot%202026-01-25%20at%2013.41.57.png)

</details>

<details>
<summary>Citation verification</summary>

![Verify](docs/images/Screenshot%202026-01-25%20at%2013.46.49.png)

</details>

---

## How It Works

The Nagomi Cascade — a 4-level validation protocol on every query:

```mermaid
graph LR
    A[Query] --> B[Registry Match]
    B --> C[Author Verification]
    C --> D[Field Mismatch Check]
    D --> E[Anomaly Report]

    style A fill:#1a1520,stroke:#e87da0,color:#f0e8ec
    style B fill:#1e3a5f,stroke:#4a6a8f,color:#7abaed
    style C fill:#1a3a2e,stroke:#3a7a5e,color:#5ac88e
    style D fill:#2a1a4a,stroke:#6a4a9a,color:#a080d0
    style E fill:#3a1a2a,stroke:#8a4a5a,color:#e87da0
```

1. **Registry Match** — Validates DOI/PMID exists in authoritative databases
2. **Author Verification** — Cross-references cited authors against registered metadata
3. **Field Mismatch Check** — Detects if a DOI resolves to a journal outside the cited domain
4. **Anomaly Report** — Flags "Frankenstein" citations or future-dated confabulations

---

## Evidence Grading

Built on the GRADE framework combined with Nagomi Trust Quotients (0–100):

| Grade | Level | Source Types | Trust Range |
|:-----:|:------|:-------------|:------------|
| **A** | Strong | Systematic Reviews, Meta-Analyses | 80–100 |
| **B** | Reliable | Randomized Controlled Trials | 60–79 |
| **C** | Indicative | Cohort & Observational Studies | 40–59 |
| **D** | Limited | Case Series, Expert Opinion | 0–39 |

---

## Installation

```bash
gemini extensions install https://github.com/avivlyweb/pubmed-gemini-extension
```

<details>
<summary>Manual installation</summary>

```bash
git clone https://github.com/avivlyweb/pubmed-gemini-extension.git
cd pubmed-gemini-extension
bash install.sh
```

</details>

**Requirements:** Gemini CLI, Node.js 18+, Python 3.9+

---

## MCP Tools

The extension exposes 5 tools via the Model Context Protocol:

| Tool | Purpose |
|:-----|:--------|
| `enhanced_pubmed_search` | PubMed search with PICO analysis and trust scoring |
| `analyze_article_trustworthiness` | Methodological quality analysis by PMID |
| `generate_research_summary` | Multi-article evidence synthesis |
| `export_citations` | BibTeX / RIS / EndNote export |
| `verify_references` | Reference verification with ABC-TOM framework |

> [!NOTE]
> The MCP server is agent-agnostic — it also works with Claude Code, Codex, and other MCP-compatible tools.

---

## Contributing

Found an anomaly in the forensic engine? Open an [issue](https://github.com/avivlyweb/pubmed-gemini-extension/issues).

---

## License

MIT

---

> [!IMPORTANT]
> Nagomi Clinical Forensic is a research tool for scholarly exploration. It does not constitute medical advice. Clinical decisions should always be mediated by qualified practitioners.

<div align="center">
<sub>和み — engineered with precision for the scientific community</sub>
</div>
