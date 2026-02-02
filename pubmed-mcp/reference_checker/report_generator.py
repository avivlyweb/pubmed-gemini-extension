"""
Report Generator - Generate verification reports in multiple formats.

Supports:
- Terminal (rich ANSI-colored output)
- JSON (machine-parseable)
- HTML (styled report)
- PDF (via HTML conversion)
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


@dataclass
class ReferenceReport:
    """Report for a single reference."""
    reference_number: int
    raw_citation: str
    verification_status: str  # VERIFIED, SUSPICIOUS, NOT_FOUND, DEFINITE_FAKE, LIKELY_VALID, etc.
    confidence: float
    
    # Verification details
    pubmed_pmid: Optional[str] = None
    doi_valid: Optional[bool] = None
    discrepancies: List[str] = field(default_factory=list)
    
    # NEW: Fake indicators (for DEFINITE_FAKE status)
    fake_indicators: List[str] = field(default_factory=list)
    
    # NEW: False positive warnings (why this might NOT be fake)
    false_positive_warnings: List[str] = field(default_factory=list)
    
    # NEW: Manual verification links
    manual_verify_links: Dict[str, str] = field(default_factory=dict)
    
    # APA issues
    apa_errors: int = 0
    apa_warnings: int = 0
    apa_issues: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class BatchSummary:
    """Summary for batch verification."""
    total_documents: int
    total_references: int
    verified_count: int
    suspicious_count: int
    not_found_count: int
    definite_fake_count: int = 0
    likely_valid_count: int = 0
    documents: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class VerificationReport:
    """Complete verification report."""
    document_name: str
    timestamp: str
    total_references: int
    verified_count: int
    suspicious_count: int
    not_found_count: int
    error_count: int
    
    # NEW: Additional status counts
    definite_fake_count: int = 0
    likely_valid_count: int = 0
    
    # Detailed results
    references: List[ReferenceReport] = field(default_factory=list)
    
    # APA summary
    apa_errors_total: int = 0
    apa_warnings_total: int = 0
    apa_issues_by_type: Dict[str, int] = field(default_factory=dict)
    
    # Batch mode
    batch_summary: Optional[BatchSummary] = None
    
    # Warnings from parsing
    parsing_warnings: List[str] = field(default_factory=list)


class ReportGenerator:
    """
    Generate verification reports in multiple formats.
    """
    
    # Status symbols for terminal output
    STATUS_SYMBOLS = {
        "VERIFIED": ("✅", "\033[92m"),      # Green
        "SUSPICIOUS": ("⚠️", "\033[93m"),    # Yellow
        "NOT_FOUND": ("❌", "\033[91m"),     # Red
        "DEFINITE_FAKE": ("🚨", "\033[91m"), # Red (strong)
        "LIKELY_VALID": ("ℹ️", "\033[94m"),   # Blue
        "UNPARSEABLE": ("❓", "\033[90m"),   # Gray
        "ERROR": ("💥", "\033[91m"),         # Red
    }
    
    RESET_COLOR = "\033[0m"
    BOLD = "\033[1m"
    
    def build_report(self, 
                     verification_results: List[Any],
                     document_name: str = "Unknown Document",
                     raw_citations: Optional[List[str]] = None,
                     apa_results: Optional[List[Any]] = None,
                     parsing_warnings: Optional[List[str]] = None) -> VerificationReport:
        """
        Build a VerificationReport from raw verification results.
        
        Args:
            verification_results: List of VerificationResult objects from VerificationEngine
            document_name: Name of the source document
            raw_citations: Original citation strings (parallel to results)
            apa_results: List of APACheckResult objects (parallel to results)
            parsing_warnings: Any warnings from parsing stage
            
        Returns:
            VerificationReport ready for rendering
        """
        from datetime import datetime
        
        # Count by status
        verified = suspicious = not_found = errors = 0
        definite_fake = likely_valid = 0
        reference_reports = []
        apa_errors_total = 0
        apa_warnings_total = 0
        apa_by_type: Dict[str, int] = {}
        
        for i, result in enumerate(verification_results):
            status = result.status.value if hasattr(result.status, 'value') else str(result.status)
            
            if status == "VERIFIED":
                verified += 1
            elif status == "SUSPICIOUS":
                suspicious += 1
            elif status == "NOT_FOUND":
                not_found += 1
            elif status == "DEFINITE_FAKE":
                definite_fake += 1
            elif status == "LIKELY_VALID":
                likely_valid += 1
            else:
                errors += 1
            
            # Build individual reference report
            raw_citation = raw_citations[i] if raw_citations and i < len(raw_citations) else ""
            
            # Get APA info if available
            apa_issues = []
            apa_err = 0
            apa_warn = 0
            if apa_results and i < len(apa_results):
                apa_result = apa_results[i]
                if hasattr(apa_result, 'issues'):
                    for issue in apa_result.issues:
                        severity = issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity)
                        apa_issues.append({
                            'message': issue.message,
                            'field': issue.field if hasattr(issue, 'field') else None,
                            'severity': severity
                        })
                        if severity == 'error':
                            apa_err += 1
                            apa_errors_total += 1
                        else:
                            apa_warn += 1
                            apa_warnings_total += 1
                        
                        # Count by type
                        issue_type = issue.issue_type.value if hasattr(issue.issue_type, 'value') else 'unknown'
                        apa_by_type[issue_type] = apa_by_type.get(issue_type, 0) + 1
            
            ref_report = ReferenceReport(
                reference_number=i + 1,
                raw_citation=raw_citation[:200] + "..." if len(raw_citation) > 200 else raw_citation,
                verification_status=status,
                confidence=result.confidence,
                pubmed_pmid=result.pubmed_match.pmid if hasattr(result, 'pubmed_match') and result.pubmed_match else None,
                doi_valid=result.doi_valid if hasattr(result, 'doi_valid') else None,
                discrepancies=result.discrepancies if hasattr(result, 'discrepancies') else [],
                fake_indicators=result.fake_indicators if hasattr(result, 'fake_indicators') else [],
                false_positive_warnings=result.false_positive_warnings if hasattr(result, 'false_positive_warnings') else [],
                manual_verify_links=result.manual_verify_links if hasattr(result, 'manual_verify_links') else {},
                apa_errors=apa_err,
                apa_warnings=apa_warn,
                apa_issues=apa_issues
            )
            reference_reports.append(ref_report)
        
        return VerificationReport(
            document_name=document_name,
            timestamp=datetime.now().isoformat(),
            total_references=len(verification_results),
            verified_count=verified,
            suspicious_count=suspicious,
            not_found_count=not_found,
            error_count=errors,
            definite_fake_count=definite_fake,
            likely_valid_count=likely_valid,
            references=reference_reports,
            apa_errors_total=apa_errors_total,
            apa_warnings_total=apa_warnings_total,
            apa_issues_by_type=apa_by_type,
            parsing_warnings=parsing_warnings or []
        )
    
    def generate(self, report: VerificationReport, 
                 format: Literal["terminal", "json", "html", "pdf"] = "terminal") -> str:
        """
        Generate report in specified format.
        
        Args:
            report: VerificationReport object
            format: Output format
            
        Returns:
            Formatted report string (or bytes for PDF)
        """
        if format == "terminal":
            return self._render_terminal(report)
        elif format == "json":
            return self._render_json(report)
        elif format == "html":
            return self._render_html(report)
        elif format == "pdf":
            return self._render_pdf(report)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _render_terminal(self, report: VerificationReport) -> str:
        """Render rich terminal output with ANSI colors."""
        lines = []
        
        # Header
        lines.append("")
        lines.append(f"{self.BOLD}{'═' * 60}{self.RESET_COLOR}")
        lines.append(f"{self.BOLD}REFERENCE VERIFICATION REPORT{self.RESET_COLOR}")
        lines.append(f"{'═' * 60}")
        lines.append("")
        
        # Document info
        lines.append(f"Document: {report.document_name}")
        lines.append(f"Checked:  {report.timestamp}")
        lines.append("")
        
        # Summary
        lines.append(f"{self.BOLD}SUMMARY{self.RESET_COLOR}")
        lines.append("─" * 40)
        lines.append(f"Total References: {report.total_references}")
        
        verified_pct = (report.verified_count / max(report.total_references, 1)) * 100
        suspicious_pct = (report.suspicious_count / max(report.total_references, 1)) * 100
        not_found_pct = (report.not_found_count / max(report.total_references, 1)) * 100
        definite_fake_pct = (report.definite_fake_count / max(report.total_references, 1)) * 100
        likely_valid_pct = (report.likely_valid_count / max(report.total_references, 1)) * 100
        
        lines.append(f"✅ Verified:     {report.verified_count:3d} ({verified_pct:.0f}%)")
        
        if report.definite_fake_count > 0:
            lines.append(f"🚨 Definite Fake:{report.definite_fake_count:3d} ({definite_fake_pct:.0f}%)")
        
        lines.append(f"⚠️  Suspicious:   {report.suspicious_count:3d} ({suspicious_pct:.0f}%)")
        lines.append(f"❌ Not Found:    {report.not_found_count:3d} ({not_found_pct:.0f}%)")
        
        if report.likely_valid_count > 0:
            lines.append(f"ℹ️  Likely Valid: {report.likely_valid_count:3d} ({likely_valid_pct:.0f}%)")
        
        if report.error_count > 0:
            lines.append(f"💥 Errors:       {report.error_count:3d}")
        
        lines.append("")
        lines.append(f"APA Issues:   {report.apa_errors_total} errors, {report.apa_warnings_total} warnings")
        lines.append("")
        
        # Flagged references (only show problematic ones)
        flagged = [r for r in report.references 
                   if r.verification_status in ["DEFINITE_FAKE", "SUSPICIOUS", "NOT_FOUND", "ERROR"]]
        
        # Also show LIKELY_VALID with notes
        likely_valid = [r for r in report.references 
                        if r.verification_status == "LIKELY_VALID"]
        
        if flagged:
            lines.append(f"{self.BOLD}FLAGGED REFERENCES{self.RESET_COLOR}")
            lines.append("─" * 40)
            lines.append("")
            
            for ref in flagged:
                symbol, color = self.STATUS_SYMBOLS.get(
                    ref.verification_status, ("?", self.RESET_COLOR)
                )
                
                lines.append(f"[{ref.reference_number}] {symbol} {ref.verification_status} (confidence: {ref.confidence:.2f})")
                
                # Show truncated citation
                citation = ref.raw_citation
                if len(citation) > 100:
                    citation = citation[:100] + "..."
                lines.append(f'    "{citation}"')
                
                # Show PMID if found
                if ref.pubmed_pmid:
                    lines.append(f"    → Partial match: PMID {ref.pubmed_pmid}")
                
                # Show fake indicators (most important for DEFINITE_FAKE)
                for indicator in ref.fake_indicators[:3]:
                    lines.append(f"    🚨 {indicator}")
                
                # Show discrepancies
                for disc in ref.discrepancies[:3]:
                    lines.append(f"    → {disc}")
                
                # Show DOI status
                if ref.doi_valid is False:
                    lines.append("    → DOI does not resolve")
                
                # Show manual verification links
                if ref.manual_verify_links:
                    lines.append("    → Verify manually:")
                    for source, url in list(ref.manual_verify_links.items())[:2]:
                        lines.append(f"      {source}: {url}")
                
                lines.append("")
        else:
            lines.append(f"{self.BOLD}All references verified successfully!{self.RESET_COLOR}")
            lines.append("")
        
        # Show LIKELY_VALID references with context
        if likely_valid:
            lines.append(f"{self.BOLD}LIKELY VALID (but not in databases){self.RESET_COLOR}")
            lines.append("─" * 40)
            lines.append("These references were not found in PubMed/CrossRef but are likely valid:")
            lines.append("")
            
            for ref in likely_valid[:5]:  # Limit to first 5
                citation = ref.raw_citation[:80] + "..." if len(ref.raw_citation) > 80 else ref.raw_citation
                lines.append(f"[{ref.reference_number}] ℹ️  \"{citation}\"")
                for warning in ref.false_positive_warnings[:1]:
                    lines.append(f"    → {warning}")
            
            if len(likely_valid) > 5:
                lines.append(f"    ... and {len(likely_valid) - 5} more")
            lines.append("")
        
        # APA Issues summary
        if report.apa_errors_total > 0 or report.apa_warnings_total > 0:
            lines.append(f"{self.BOLD}APA STYLE ISSUES{self.RESET_COLOR}")
            lines.append("─" * 40)
            
            # Group by type
            for issue_type, count in sorted(report.apa_issues_by_type.items()):
                lines.append(f"  {issue_type}: {count}")
            
            lines.append("")
            
            # Show specific issues (limit to first 10)
            issue_count = 0
            for ref in report.references:
                for issue in ref.apa_issues:
                    if issue_count >= 10:
                        remaining = sum(len(r.apa_issues) for r in report.references) - 10
                        if remaining > 0:
                            lines.append(f"  ... and {remaining} more issues")
                        break
                    
                    severity = "⚠️" if issue.get('severity') == 'warning' else "❌"
                    lines.append(f"[{ref.reference_number}] {severity} {issue.get('message', '')}")
                    issue_count += 1
                
                if issue_count >= 10:
                    break
            
            lines.append("")
        
        # Parsing warnings
        if report.parsing_warnings:
            lines.append(f"{self.BOLD}PARSING NOTES{self.RESET_COLOR}")
            lines.append("─" * 40)
            for warning in report.parsing_warnings[:5]:
                lines.append(f"  ⚠️ {warning}")
            lines.append("")
        
        # Disclaimer
        lines.append(f"{self.BOLD}LIMITATIONS{self.RESET_COLOR}")
        lines.append("─" * 40)
        lines.append("• PubMed primarily indexes biomedical literature")
        lines.append("• Non-medical journals may show false 'Not Found' results")
        lines.append("• 🚨 DEFINITE_FAKE = high confidence fake (future dates, DOI→wrong field)")
        lines.append("• ℹ️  LIKELY_VALID = probably real but outside our database coverage")
        lines.append("• Always verify flagged references manually before drawing conclusions")
        lines.append("")
        
        # Footer
        lines.append("═" * 60)
        
        return "\n".join(lines)
    
    def _render_json(self, report: VerificationReport) -> str:
        """Render as JSON."""
        # Convert dataclasses to dicts
        data = {
            "document_name": report.document_name,
            "timestamp": report.timestamp,
            "summary": {
                "total_references": report.total_references,
                "verified": report.verified_count,
                "suspicious": report.suspicious_count,
                "not_found": report.not_found_count,
                "errors": report.error_count,
                "verified_percentage": round(
                    (report.verified_count / max(report.total_references, 1)) * 100, 1
                )
            },
            "apa_summary": {
                "errors": report.apa_errors_total,
                "warnings": report.apa_warnings_total,
                "by_type": report.apa_issues_by_type
            },
            "references": [
                {
                    "number": ref.reference_number,
                    "citation": ref.raw_citation,
                    "status": ref.verification_status,
                    "confidence": ref.confidence,
                    "pubmed_pmid": ref.pubmed_pmid,
                    "doi_valid": ref.doi_valid,
                    "discrepancies": ref.discrepancies,
                    "apa_issues": ref.apa_issues
                }
                for ref in report.references
            ],
            "parsing_warnings": report.parsing_warnings
        }
        
        if report.batch_summary:
            data["batch_summary"] = {
                "total_documents": report.batch_summary.total_documents,
                "total_references": report.batch_summary.total_references,
                "verified": report.batch_summary.verified_count,
                "suspicious": report.batch_summary.suspicious_count,
                "not_found": report.batch_summary.not_found_count
            }
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def _render_html(self, report: VerificationReport) -> str:
        """Render as HTML report."""
        # Calculate percentages
        total = max(report.total_references, 1)
        verified_pct = (report.verified_count / total) * 100
        suspicious_pct = (report.suspicious_count / total) * 100
        not_found_pct = (report.not_found_count / total) * 100
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reference Verification Report</title>
    <style>
        :root {{
            --verified: #22c55e;
            --suspicious: #f59e0b;
            --not-found: #ef4444;
            --bg: #f8fafc;
            --card: #ffffff;
            --text: #1e293b;
            --muted: #64748b;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
        }}
        
        .container {{ max-width: 900px; margin: 0 auto; }}
        
        .header {{
            text-align: center;
            margin-bottom: 2rem;
            padding: 2rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 12px;
        }}
        
        .header h1 {{ font-size: 1.8rem; margin-bottom: 0.5rem; }}
        .header .meta {{ opacity: 0.9; font-size: 0.9rem; }}
        
        .card {{
            background: var(--card);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .card h2 {{
            font-size: 1.1rem;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--bg);
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
        }}
        
        .stat {{
            text-align: center;
            padding: 1rem;
            background: var(--bg);
            border-radius: 8px;
        }}
        
        .stat-value {{ font-size: 2rem; font-weight: bold; }}
        .stat-label {{ font-size: 0.85rem; color: var(--muted); }}
        
        .stat.verified .stat-value {{ color: var(--verified); }}
        .stat.suspicious .stat-value {{ color: var(--suspicious); }}
        .stat.not-found .stat-value {{ color: var(--not-found); }}
        
        .progress-bar {{
            height: 24px;
            background: var(--bg);
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            margin: 1rem 0;
        }}
        
        .progress-segment {{
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: bold;
            color: white;
        }}
        
        .reference {{
            padding: 1rem;
            margin-bottom: 0.75rem;
            border-radius: 8px;
            border-left: 4px solid;
        }}
        
        .reference.verified {{ 
            background: #f0fdf4; 
            border-color: var(--verified);
        }}
        .reference.suspicious {{ 
            background: #fffbeb; 
            border-color: var(--suspicious);
        }}
        .reference.not-found {{ 
            background: #fef2f2; 
            border-color: var(--not-found);
        }}
        
        .reference-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }}
        
        .reference-number {{
            font-weight: bold;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.85rem;
        }}
        
        .status-badge {{
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        .status-badge.verified {{ background: var(--verified); color: white; }}
        .status-badge.suspicious {{ background: var(--suspicious); color: white; }}
        .status-badge.not-found {{ background: var(--not-found); color: white; }}
        
        .citation {{
            font-style: italic;
            color: var(--muted);
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }}
        
        .issues {{ margin-top: 0.5rem; }}
        .issue {{
            font-size: 0.85rem;
            padding: 0.25rem 0;
            color: var(--muted);
        }}
        
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--muted);
            font-size: 0.85rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Reference Verification Report</h1>
            <div class="meta">
                <div>{report.document_name}</div>
                <div>Generated: {report.timestamp}</div>
            </div>
        </div>
        
        <div class="card">
            <h2>Summary</h2>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{report.total_references}</div>
                    <div class="stat-label">Total References</div>
                </div>
                <div class="stat verified">
                    <div class="stat-value">{report.verified_count}</div>
                    <div class="stat-label">Verified</div>
                </div>
                <div class="stat suspicious">
                    <div class="stat-value">{report.suspicious_count}</div>
                    <div class="stat-label">Suspicious</div>
                </div>
                <div class="stat not-found">
                    <div class="stat-value">{report.not_found_count}</div>
                    <div class="stat-label">Not Found</div>
                </div>
            </div>
            
            <div class="progress-bar">
                <div class="progress-segment" style="width: {verified_pct}%; background: var(--verified);">
                    {verified_pct:.0f}%
                </div>
                <div class="progress-segment" style="width: {suspicious_pct}%; background: var(--suspicious);">
                    {suspicious_pct:.0f}%
                </div>
                <div class="progress-segment" style="width: {not_found_pct}%; background: var(--not-found);">
                    {not_found_pct:.0f}%
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>APA Style Check</h2>
            <div class="stats">
                <div class="stat not-found">
                    <div class="stat-value">{report.apa_errors_total}</div>
                    <div class="stat-label">Errors</div>
                </div>
                <div class="stat suspicious">
                    <div class="stat-value">{report.apa_warnings_total}</div>
                    <div class="stat-label">Warnings</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Flagged References</h2>
'''
        
        # Add flagged references
        flagged = [r for r in report.references 
                   if r.verification_status in ["SUSPICIOUS", "NOT_FOUND", "ERROR"]]
        
        if flagged:
            for ref in flagged:
                status_class = ref.verification_status.lower().replace("_", "-")
                citation = ref.raw_citation[:150] + "..." if len(ref.raw_citation) > 150 else ref.raw_citation
                
                html += f'''
            <div class="reference {status_class}">
                <div class="reference-header">
                    <span class="reference-number">[{ref.reference_number}]</span>
                    <span class="status-badge {status_class}">{ref.verification_status}</span>
                </div>
                <div class="citation">"{citation}"</div>
                <div class="confidence">Confidence: {ref.confidence:.0%}</div>
                <div class="issues">
'''
                if ref.pubmed_pmid:
                    html += f'                    <div class="issue">→ Partial match: PMID {ref.pubmed_pmid}</div>\n'
                
                for disc in ref.discrepancies[:3]:
                    html += f'                    <div class="issue">→ {disc}</div>\n'
                
                if ref.doi_valid is False:
                    html += '                    <div class="issue">→ DOI does not resolve</div>\n'
                
                html += '''                </div>
            </div>
'''
        else:
            html += '            <p style="text-align: center; color: var(--verified);">All references verified successfully!</p>\n'
        
        html += f'''
        </div>
        
        <div class="footer">
            <p>Generated by PubMed Reference Checker v2.7.0</p>
            <p>Powered by PubMed, DOI.org, and CrossRef</p>
        </div>
    </div>
</body>
</html>'''
        
        return html
    
    def _render_pdf(self, report: VerificationReport) -> bytes:
        """Render as PDF (via HTML conversion)."""
        try:
            from weasyprint import HTML
            html_content = self._render_html(report)
            pdf_bytes = HTML(string=html_content).write_pdf()
            return pdf_bytes
        except ImportError:
            raise ImportError(
                "PDF generation requires weasyprint. Install with: pip install weasyprint"
            )
    
    def save(self, report: VerificationReport, file_path: str, 
             format: Optional[str] = None) -> None:
        """
        Save report to file.
        
        Args:
            report: VerificationReport object
            file_path: Output file path
            format: Optional format override (inferred from extension if not provided)
        """
        from pathlib import Path
        
        path = Path(file_path)
        
        # Infer format from extension if not provided
        if format is None:
            ext = path.suffix.lower()
            format_map = {
                '.json': 'json',
                '.html': 'html',
                '.htm': 'html',
                '.pdf': 'pdf',
                '.txt': 'terminal'
            }
            format = format_map.get(ext, 'terminal')
        
        content = self.generate(report, format)
        
        if format == 'pdf':
            path.write_bytes(content)
        else:
            path.write_text(content, encoding='utf-8')
