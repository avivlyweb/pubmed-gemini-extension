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
    
    # NEW v2.8.1: Actionable advice
    advice: str = ""  # What to do about this reference
    fix_suggestion: str = ""  # Specific fix recommendation
    
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
    # ABC-TOM v3.0.0: New classification counts
    verified_legacy_doi_count: int = 0
    grey_literature_count: int = 0
    low_quality_source_count: int = 0
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
    
    # ABC-TOM v3.0.0: New classification counts
    verified_legacy_doi_count: int = 0
    grey_literature_count: int = 0
    low_quality_source_count: int = 0
    
    # Batch analysis results
    batch_analysis: Optional[Dict[str, Any]] = None
    
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
    
    ABC-TOM v3.0.0: Enhanced with 6-tier classification system.
    """
    
    # Status symbols for terminal output (ABC-TOM 6-tier classification)
    STATUS_SYMBOLS = {
        "VERIFIED": ("OK", "\033[92m"),            # Green
        "VERIFIED_LEGACY_DOI": ("LEGACY", "\033[96m"),  # Cyan
        "GREY_LITERATURE": ("GREY", "\033[94m"),   # Blue
        "LOW_QUALITY_SOURCE": ("LOW", "\033[93m"), # Yellow
        "SUSPICIOUS": ("WARN", "\033[93m"),        # Yellow
        "NOT_FOUND": ("MISS", "\033[91m"),         # Red
        "DEFINITE_FAKE": ("FAKE", "\033[91m"),     # Red (strong)
        "LIKELY_VALID": ("INFO", "\033[94m"),      # Blue
        "UNPARSEABLE": ("ERR", "\033[90m"),        # Gray
        "ERROR": ("ERR", "\033[91m"),              # Red
    }
    
    RESET_COLOR = "\033[0m"
    BOLD = "\033[1m"
    
    # Advice templates for each status (ABC-TOM v3.0.0)
    ADVICE_TEMPLATES = {
        "DEFINITE_FAKE": {
            "advice": "REMOVE or REPLACE this reference immediately. It shows clear signs of fabrication.",
            "icon": "FAKE"
        },
        "NOT_FOUND": {
            "advice": "Verify manually using Google Scholar. May be legitimate grey literature or a very new publication.",
            "icon": "MISS"
        },
        "SUSPICIOUS": {
            "advice": "Check the DOI and metadata carefully. The reference exists but has discrepancies.",
            "icon": "WARN"
        },
        "LIKELY_VALID": {
            "advice": "Probably valid. Not in PubMed because it's outside biomedical scope (book, non-medical journal, etc.).",
            "icon": "INFO"
        },
        "VERIFIED": {
            "advice": "No action needed. Reference verified in databases.",
            "icon": "OK"
        },
        "VERIFIED_LEGACY_DOI": {
            "advice": "Paper verified but DOI is broken/migrated. Consider updating the DOI.",
            "icon": "LEGACY"
        },
        "GREY_LITERATURE": {
            "advice": "Valid grey literature (government report, guideline, etc.). Not indexed in PubMed but legitimate.",
            "icon": "GREY"
        },
        "LOW_QUALITY_SOURCE": {
            "advice": "Real source but not peer-reviewed (preprint, ResearchGate, etc.). Consider replacing with peer-reviewed version.",
            "icon": "LOW"
        },
        "ERROR": {
            "advice": "Could not verify due to technical error. Try again or verify manually.",
            "icon": "ERR"
        }
    }
    
    def _generate_advice(self, ref_report: ReferenceReport) -> tuple:
        """
        Generate actionable advice for a reference based on its verification status.
        
        Returns:
            (advice: str, fix_suggestion: str)
        """
        status = ref_report.verification_status
        template = self.ADVICE_TEMPLATES.get(status, self.ADVICE_TEMPLATES["ERROR"])
        
        advice = template["advice"]
        fix_suggestion = ""
        
        # Generate specific fix suggestions based on indicators
        if status == "DEFINITE_FAKE":
            if ref_report.fake_indicators:
                indicator = ref_report.fake_indicators[0].lower()
                if "doi" in indicator and "mismatch" in indicator:
                    fix_suggestion = "The DOI points to a different paper. Search Google Scholar for the correct DOI, or remove the DOI entirely."
                elif "future" in indicator:
                    fix_suggestion = "This paper claims a future publication date. Check if it's a preprint or typo, otherwise remove."
                elif "truncated" in indicator:
                    fix_suggestion = "The DOI appears truncated (PDF parsing error). Find the complete DOI from the original source."
                elif "frankenstein" in indicator:
                    fix_suggestion = "This is a 'Frankenstein citation' - real DOI attached to wrong paper. Find the correct DOI."
                else:
                    fix_suggestion = "Search Google Scholar to find if this paper actually exists with correct metadata."
        
        elif status == "NOT_FOUND":
            if ref_report.discrepancies:
                if any("doi" in d.lower() for d in ref_report.discrepancies):
                    fix_suggestion = "The DOI doesn't resolve. Verify it's typed correctly, or search for the paper by title."
                else:
                    fix_suggestion = "Paper not found in databases. Check spelling and verify the source exists."
            else:
                fix_suggestion = "Search Google Scholar or the journal website directly to confirm this reference exists."
        
        elif status == "SUSPICIOUS":
            if ref_report.discrepancies:
                disc = ref_report.discrepancies[0].lower()
                if "year" in disc:
                    fix_suggestion = "Publication year doesn't match. Check the original source for correct year."
                elif "title" in disc:
                    fix_suggestion = "Title doesn't match well. Verify you're citing the correct paper."
                elif "doi" in disc:
                    fix_suggestion = "DOI mismatch detected. Verify the DOI links to the intended paper."
                else:
                    fix_suggestion = "Metadata discrepancies found. Double-check all citation details."
            else:
                fix_suggestion = "Some metadata doesn't match. Verify citation details against the original source."
        
        elif status == "LIKELY_VALID":
            if ref_report.false_positive_warnings:
                warning = ref_report.false_positive_warnings[0].lower()
                if "non-medical" in warning or "pubmed" in warning:
                    fix_suggestion = "This journal isn't indexed in PubMed. No action needed unless you doubt the source."
                elif "grey literature" in warning or "web" in warning:
                    fix_suggestion = "Web resource detected. Ensure you have 'Retrieved from [URL]' with access date."
                elif "classic" in warning:
                    fix_suggestion = "Classic/older work may show as different edition. Verify the edition you're citing."
                else:
                    fix_suggestion = "No action needed - this appears legitimate but is outside database coverage."
        
        # ABC-TOM v3.0.0: New status types
        elif status == "VERIFIED_LEGACY_DOI":
            if ref_report.false_positive_warnings:
                fix_suggestion = "Consider updating the DOI to a working version, or remove it and cite by title/journal."
            else:
                fix_suggestion = "The DOI is broken but the paper exists. Optionally update the DOI."
        
        elif status == "GREY_LITERATURE":
            if ref_report.false_positive_warnings:
                warning = ref_report.false_positive_warnings[0].lower()
                if "who" in warning or "government" in warning:
                    fix_suggestion = "Government/WHO reports are valid sources. Ensure proper citation format for grey literature."
                elif "guideline" in warning:
                    fix_suggestion = "Clinical guidelines are valid grey literature. Use proper guideline citation format."
                elif "book" in warning or "software" in warning:
                    fix_suggestion = "Books and software have different citation formats. Verify correct format is used."
                else:
                    fix_suggestion = "This is valid grey literature. Ensure you're using the appropriate citation format."
            else:
                fix_suggestion = "Grey literature source (not indexed in academic databases). Consider if a peer-reviewed alternative exists."
        
        elif status == "LOW_QUALITY_SOURCE":
            if ref_report.false_positive_warnings:
                warning = ref_report.false_positive_warnings[0].lower()
                if "preprint" in warning:
                    fix_suggestion = "Check if this preprint has been published in a peer-reviewed journal and cite that instead."
                elif "researchgate" in warning:
                    fix_suggestion = "Find the original published version of this paper instead of the ResearchGate copy."
                else:
                    fix_suggestion = "Consider replacing with a peer-reviewed source if one exists."
            else:
                fix_suggestion = "Non-peer-reviewed source. Consider replacing with peer-reviewed version if available."
        
        return advice, fix_suggestion
    
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
        
        # Count by status (ABC-TOM 6-tier classification)
        verified = suspicious = not_found = errors = 0
        definite_fake = likely_valid = 0
        verified_legacy_doi = grey_literature = low_quality_source = 0
        reference_reports = []
        apa_errors_total = 0
        apa_warnings_total = 0
        apa_by_type: Dict[str, int] = {}
        
        for i, result in enumerate(verification_results):
            status = result.status.value if hasattr(result.status, 'value') else str(result.status)
            
            if status == "VERIFIED":
                verified += 1
            elif status == "VERIFIED_LEGACY_DOI":
                verified_legacy_doi += 1
            elif status == "GREY_LITERATURE":
                grey_literature += 1
            elif status == "LOW_QUALITY_SOURCE":
                low_quality_source += 1
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
            
            # Generate advice for this reference
            advice, fix_suggestion = self._generate_advice(ref_report)
            ref_report.advice = advice
            ref_report.fix_suggestion = fix_suggestion
            
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
            # ABC-TOM v3.0.0: New classification counts
            verified_legacy_doi_count=verified_legacy_doi,
            grey_literature_count=grey_literature,
            low_quality_source_count=low_quality_source,
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
        """Render rich terminal output with ANSI colors and actionable advice."""
        lines = []
        
        # Header
        lines.append("")
        lines.append(f"{self.BOLD}{'═' * 70}{self.RESET_COLOR}")
        lines.append(f"{self.BOLD}📋 REFERENCE VERIFICATION REPORT{self.RESET_COLOR}")
        lines.append(f"{'═' * 70}")
        lines.append("")
        
        # Document info
        lines.append(f"Document: {report.document_name}")
        lines.append(f"Checked:  {report.timestamp}")
        lines.append("")
        
        # Summary with action alert
        lines.append(f"{self.BOLD}📊 SUMMARY{self.RESET_COLOR}")
        lines.append("─" * 50)
        lines.append(f"Total References: {report.total_references}")
        lines.append("")
        
        verified_pct = (report.verified_count / max(report.total_references, 1)) * 100
        suspicious_pct = (report.suspicious_count / max(report.total_references, 1)) * 100
        not_found_pct = (report.not_found_count / max(report.total_references, 1)) * 100
        definite_fake_pct = (report.definite_fake_count / max(report.total_references, 1)) * 100
        likely_valid_pct = (report.likely_valid_count / max(report.total_references, 1)) * 100
        
        lines.append(f"✅ Verified:      {report.verified_count:3d} ({verified_pct:.0f}%)")
        
        if report.definite_fake_count > 0:
            lines.append(f"🚨 Definite Fake: {report.definite_fake_count:3d} ({definite_fake_pct:.0f}%) ← ACTION REQUIRED")
        
        lines.append(f"⚠️  Suspicious:    {report.suspicious_count:3d} ({suspicious_pct:.0f}%)")
        lines.append(f"❌ Not Found:     {report.not_found_count:3d} ({not_found_pct:.0f}%)")
        
        if report.likely_valid_count > 0:
            lines.append(f"ℹ️  Likely Valid:  {report.likely_valid_count:3d} ({likely_valid_pct:.0f}%)")
        
        if report.error_count > 0:
            lines.append(f"💥 Errors:        {report.error_count:3d}")
        
        lines.append("")
        
        # Action required alert
        problem_count = report.definite_fake_count + report.suspicious_count + report.not_found_count
        if problem_count > 0:
            lines.append(f"{self.BOLD}⚡ ACTION NEEDED: {problem_count} reference(s) require attention{self.RESET_COLOR}")
            lines.append("")
        
        # Separate sections by severity
        definite_fakes = [r for r in report.references if r.verification_status == "DEFINITE_FAKE"]
        suspicious = [r for r in report.references if r.verification_status == "SUSPICIOUS"]
        not_found = [r for r in report.references if r.verification_status == "NOT_FOUND"]
        likely_valid = [r for r in report.references if r.verification_status == "LIKELY_VALID"]
        
        # DEFINITE_FAKE section (most critical)
        if definite_fakes:
            lines.append(f"{self.BOLD}🚨 DEFINITE FAKES - MUST FIX OR REMOVE{self.RESET_COLOR}")
            lines.append("═" * 50)
            lines.append("")
            
            for ref in definite_fakes:
                self._render_reference_with_advice(lines, ref)
        
        # SUSPICIOUS section
        if suspicious:
            lines.append(f"{self.BOLD}⚠️ SUSPICIOUS - VERIFY MANUALLY{self.RESET_COLOR}")
            lines.append("═" * 50)
            lines.append("")
            
            for ref in suspicious:
                self._render_reference_with_advice(lines, ref)
        
        # NOT_FOUND section
        if not_found:
            lines.append(f"{self.BOLD}❌ NOT FOUND - CHECK THESE{self.RESET_COLOR}")
            lines.append("═" * 50)
            lines.append("")
            
            for ref in not_found:
                self._render_reference_with_advice(lines, ref)
        
        # LIKELY_VALID section (informational)
        if likely_valid:
            lines.append(f"{self.BOLD}ℹ️ LIKELY VALID (outside database coverage){self.RESET_COLOR}")
            lines.append("─" * 50)
            lines.append("These weren't found in PubMed but appear legitimate:")
            lines.append("")
            
            for ref in likely_valid[:5]:
                citation = ref.raw_citation[:70] + "..." if len(ref.raw_citation) > 70 else ref.raw_citation
                lines.append(f"[{ref.reference_number}] \"{citation}\"")
                if ref.false_positive_warnings:
                    lines.append(f"    → {ref.false_positive_warnings[0][:80]}")
                lines.append("")
            
            if len(likely_valid) > 5:
                lines.append(f"    ... and {len(likely_valid) - 5} more")
                lines.append("")
        
        # APA Issues summary
        if report.apa_errors_total > 0 or report.apa_warnings_total > 0:
            lines.append(f"{self.BOLD}📝 APA STYLE ISSUES{self.RESET_COLOR}")
            lines.append("─" * 50)
            lines.append(f"Errors: {report.apa_errors_total}, Warnings: {report.apa_warnings_total}")
            lines.append("")
        
        # Quick reference guide
        lines.append(f"{self.BOLD}💡 QUICK VERIFICATION GUIDE{self.RESET_COLOR}")
        lines.append("─" * 50)
        lines.append("• Google Scholar: https://scholar.google.com")
        lines.append("• CrossRef Search: https://search.crossref.org")
        lines.append("• DOI Resolver: https://doi.org/[YOUR_DOI]")
        lines.append("")
        
        # Footer with disclaimer
        lines.append(f"{self.BOLD}📌 IMPORTANT NOTES{self.RESET_COLOR}")
        lines.append("─" * 50)
        lines.append("• 🚨 DEFINITE_FAKE = High confidence fake (DOI mismatch, future dates)")
        lines.append("• ⚠️  SUSPICIOUS = Exists but has discrepancies")
        lines.append("• ❌ NOT_FOUND = May be legitimate but not in databases")
        lines.append("• ℹ️  LIKELY_VALID = Outside PubMed scope (non-medical, books)")
        lines.append("• Always verify flagged references before submitting")
        lines.append("")
        lines.append("═" * 70)
        lines.append(f"Generated by PubMed Reference Checker v2.8.1 | 和み (Nagomi)")
        lines.append("═" * 70)
        
        return "\n".join(lines)
    
    def _render_reference_with_advice(self, lines: list, ref: ReferenceReport) -> None:
        """Render a single reference with actionable advice."""
        symbol, color = self.STATUS_SYMBOLS.get(ref.verification_status, ("?", self.RESET_COLOR))
        
        # Reference header
        lines.append(f"{symbol} [{ref.reference_number}] {ref.verification_status}")
        lines.append("─" * 40)
        
        # Citation (truncated)
        citation = ref.raw_citation
        if len(citation) > 100:
            citation = citation[:100] + "..."
        lines.append(f'"{citation}"')
        lines.append("")
        
        # Problem description
        lines.append(f"  📍 Problem:")
        if ref.fake_indicators:
            for indicator in ref.fake_indicators[:2]:
                lines.append(f"     • {indicator}")
        elif ref.discrepancies:
            for disc in ref.discrepancies[:2]:
                lines.append(f"     • {disc}")
        elif ref.doi_valid is False:
            lines.append("     • DOI does not resolve to any paper")
        else:
            lines.append("     • Reference not found in PubMed/CrossRef")
        lines.append("")
        
        # Advice and fix suggestion
        lines.append(f"  ✏️  What to do:")
        lines.append(f"     {ref.advice}")
        if ref.fix_suggestion:
            lines.append(f"     → {ref.fix_suggestion}")
        lines.append("")
        
        # Verification links
        if ref.manual_verify_links:
            lines.append(f"  🔗 Verify here:")
            for source, url in list(ref.manual_verify_links.items())[:2]:
                lines.append(f"     • {source}: {url}")
        lines.append("")
    
    def _render_json(self, report: VerificationReport) -> str:
        """Render as JSON with full advice fields (v2.8.1)."""
        # Convert dataclasses to dicts
        total = max(report.total_references, 1)
        data = {
            "document_name": report.document_name,
            "timestamp": report.timestamp,
            "version": "2.8.1",
            "summary": {
                "total_references": report.total_references,
                "verified": report.verified_count,
                "suspicious": report.suspicious_count,
                "not_found": report.not_found_count,
                "definite_fake": report.definite_fake_count,
                "likely_valid": report.likely_valid_count,
                "errors": report.error_count,
                "verified_percentage": round((report.verified_count / total) * 100, 1),
                "action_required": report.definite_fake_count + report.suspicious_count + report.not_found_count
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
                    "fake_indicators": ref.fake_indicators,
                    "false_positive_warnings": ref.false_positive_warnings,
                    "advice": ref.advice,
                    "fix_suggestion": ref.fix_suggestion,
                    "manual_verify_links": ref.manual_verify_links,
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
        .reference.definite-fake {{ 
            background: #fee2e2; 
            border-color: #dc2626;
            border-width: 3px;
        }}
        .reference.likely-valid {{ 
            background: #eff6ff; 
            border-color: #3b82f6;
        }}
        
        .advice-box {{
            margin-top: 0.75rem;
            padding: 0.75rem;
            background: #fefce8;
            border-radius: 6px;
            font-size: 0.85rem;
        }}
        .advice-box .label {{
            font-weight: bold;
            color: #854d0e;
        }}
        .verify-links {{
            margin-top: 0.5rem;
            font-size: 0.8rem;
        }}
        .verify-links a {{
            color: #2563eb;
            margin-right: 1rem;
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
        
        # Add flagged references (include DEFINITE_FAKE)
        flagged = [r for r in report.references 
                   if r.verification_status in ["DEFINITE_FAKE", "SUSPICIOUS", "NOT_FOUND", "ERROR"]]
        
        if flagged:
            for ref in flagged:
                status_class = ref.verification_status.lower().replace("_", "-")
                citation = ref.raw_citation[:150] + "..." if len(ref.raw_citation) > 150 else ref.raw_citation
                
                # Icon based on status
                icon = {"DEFINITE_FAKE": "🚨", "SUSPICIOUS": "⚠️", "NOT_FOUND": "❌", "ERROR": "💥"}.get(ref.verification_status, "?")
                
                html += f'''
            <div class="reference {status_class}">
                <div class="reference-header">
                    <span class="reference-number">[{ref.reference_number}] {icon}</span>
                    <span class="status-badge {status_class}">{ref.verification_status}</span>
                </div>
                <div class="citation">"{citation}"</div>
                <div class="confidence">Confidence: {ref.confidence:.0%}</div>
                <div class="issues">
'''
                # Show fake indicators first (most important)
                for indicator in ref.fake_indicators[:2]:
                    html += f'                    <div class="issue" style="color: #dc2626; font-weight: bold;">🚨 {indicator}</div>\n'
                
                for disc in ref.discrepancies[:2]:
                    html += f'                    <div class="issue">→ {disc}</div>\n'
                
                if ref.doi_valid is False:
                    html += '                    <div class="issue">→ DOI does not resolve</div>\n'
                
                # Add advice box
                html += f'''                </div>
                <div class="advice-box">
                    <div class="label">✏️ What to do:</div>
                    <div>{ref.advice}</div>
                    <div style="margin-top: 0.25rem;">→ {ref.fix_suggestion}</div>
                </div>
'''
                # Add verification links
                if ref.manual_verify_links:
                    html += '                <div class="verify-links">🔗 Verify: '
                    for source, url in list(ref.manual_verify_links.items())[:2]:
                        html += f'<a href="{url}" target="_blank">{source}</a> '
                    html += '</div>\n'
                
                html += '''            </div>
'''
        else:
            html += '            <p style="text-align: center; color: var(--verified);">✅ All references verified successfully!</p>\n'
        
        html += f'''
        </div>
        
        <div class="card">
            <h2>💡 How to Verify References</h2>
            <ul style="margin-left: 1.5rem; color: var(--muted);">
                <li><a href="https://scholar.google.com" target="_blank">Google Scholar</a> - Search by title or author</li>
                <li><a href="https://search.crossref.org" target="_blank">CrossRef</a> - Search academic databases</li>
                <li><strong>DOI Check</strong> - Visit https://doi.org/[DOI] to verify</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>Generated by PubMed Reference Checker v2.8.1 | 和み (Nagomi)</p>
            <p>Powered by PubMed, DOI.org, CrossRef, and OpenAlex</p>
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
