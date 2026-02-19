# PubMed Research Plugin for Claude Code

PhD-level medical research analysis powered by PubMed's 35M+ article database.

## Skills

| Skill | Invoke | Description |
|-------|--------|-------------|
| `pubmed-search` | `/pubmed-search does yoga help anxiety` | Evidence-weighted search with trust scores |
| `pubmed-analyze` | `/pubmed-analyze 34580864` | Deep analysis of a specific article by PMID |
| `pubmed-synthesis` | `/pubmed-synthesis exercise for COPD` | Systematic multi-study evidence synthesis |
| `pubmed-verify` | `/pubmed-verify Smith 2021 ...` | Citation fraud detection (ABC-TOM 6-tier) |

## MCP Server

The plugin connects to the PubMed MCP server at:
`/Users/avivly/Downloads/00_Inbox/website/pubmed_extension_repo/pubmed-mcp/pubmed_mcp.py`

The Node.js wrapper (`pubmed-wrapper.js`) auto-creates a Python venv on first run.

## Setup

The `.mcp.json` in this directory wires up the MCP server automatically when Claude Code
is run from this directory.

## Source

Based on the [PubMed Gemini Extension](https://github.com/avivlyweb/pubmed-gemini-extension)
by Aviv at [physiotherapy.ai](https://physiotherapy.ai).
