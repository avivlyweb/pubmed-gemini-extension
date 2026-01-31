#!/usr/bin/env python3
"""
Tests for Reference Checker module.

Tests the new reference verification functionality without modifying existing code.
"""

import asyncio
import sys
sys.path.insert(0, '.')

from reference_checker import (
    ReferenceExtractor, ParsedReference,
    APAChecker, APAIssue, IssueSeverity,
    ReportGenerator, VerificationReport, ReferenceReport,
    VerificationStatus
)


# ==================== REFERENCE EXTRACTOR TESTS ====================

def test_extract_doi():
    """Extract DOI from citation."""
    extractor = ReferenceExtractor()
    
    # Standard DOI format
    ref = extractor.extract(
        "Smith, J. (2023). Title. Journal, 10(2), 123-145. https://doi.org/10.1234/abc.123"
    )
    assert ref.doi == "10.1234/abc.123", f"Expected DOI, got {ref.doi}"
    print("  [PASS] test_extract_doi")


def test_extract_year():
    """Extract year from citation."""
    extractor = ReferenceExtractor()
    
    # Year in parentheses (APA style)
    ref = extractor.extract("Smith, J. (2023). Title of article.")
    assert ref.year == 2023, f"Expected 2023, got {ref.year}"
    
    # Year without parentheses
    ref2 = extractor.extract("Smith, J. 2023. Title of article.")
    assert ref2.year == 2023, f"Expected 2023, got {ref2.year}"
    
    print("  [PASS] test_extract_year")


def test_extract_authors():
    """Extract authors from citation."""
    extractor = ReferenceExtractor()
    
    ref = extractor.extract(
        "Smith, J. A., & Doe, M. B. (2023). Title of article. Journal Name, 10(2), 123."
    )
    
    assert len(ref.authors) >= 1, "Should extract at least one author"
    assert "Smith" in ref.authors[0], f"First author should be Smith, got {ref.authors}"
    print("  [PASS] test_extract_authors")


def test_extract_pmid():
    """Extract PMID from citation."""
    extractor = ReferenceExtractor()
    
    ref = extractor.extract(
        "Smith, J. (2023). Title. Journal. PMID: 12345678"
    )
    assert ref.pmid == "12345678", f"Expected PMID 12345678, got {ref.pmid}"
    print("  [PASS] test_extract_pmid")


def test_parse_confidence():
    """Parse confidence reflects extraction quality."""
    extractor = ReferenceExtractor()
    
    # Well-formed citation
    good_ref = extractor.extract(
        "Smith, J. A. (2023). Complete title here. Journal Name, 10(2), 123-145. https://doi.org/10.1234/abc"
    )
    
    # Malformed citation
    bad_ref = extractor.extract("Some random text that is not a citation")
    
    assert good_ref.parse_confidence > bad_ref.parse_confidence, \
        "Good citation should have higher confidence"
    print("  [PASS] test_parse_confidence")


def test_batch_extract():
    """Batch extraction of multiple references."""
    extractor = ReferenceExtractor()
    
    entries = [
        "Smith, J. (2023). First article. Journal A, 1(1), 1-10.",
        "Doe, A. (2022). Second article. Journal B, 2(2), 20-30.",
        "Johnson, R. (2021). Third article. Journal C, 3(3), 30-40."
    ]
    
    refs = extractor.extract_batch(entries)
    
    assert len(refs) == 3, f"Expected 3 refs, got {len(refs)}"
    assert refs[0].reference_number == 1, "First ref should be numbered 1"
    assert refs[2].reference_number == 3, "Third ref should be numbered 3"
    print("  [PASS] test_batch_extract")


# ==================== APA CHECKER TESTS ====================

def test_apa_author_format():
    """Check APA author format validation."""
    checker = APAChecker()
    
    # Create reference with wrong author format
    ref = ParsedReference(
        raw_text="John Smith (2023). Title. Journal.",
        reference_number=1,
        authors=["John Smith"],  # Wrong format
        year=2023
    )
    
    issues = checker.check(ref)
    author_issues = [i for i in issues if i.field == "author"]
    
    assert len(author_issues) > 0, "Should detect author format issue"
    print("  [PASS] test_apa_author_format")


def test_apa_year_format():
    """Check APA year format validation."""
    checker = APAChecker()
    
    # Reference without proper year parentheses
    ref = ParsedReference(
        raw_text="Smith, J. 2023 Title of article.",
        reference_number=1,
        authors=["Smith, J."],
        year=2023
    )
    
    issues = checker.check(ref)
    year_issues = [i for i in issues if i.field == "year"]
    
    # Should detect missing parentheses
    assert len(year_issues) > 0, "Should detect year format issue"
    print("  [PASS] test_apa_year_format")


def test_apa_doi_format():
    """Check APA DOI format validation."""
    checker = APAChecker()
    
    # Reference with old DOI format
    ref = ParsedReference(
        raw_text="Smith, J. (2023). Title. Journal. doi: 10.1234/abc",
        reference_number=1,
        authors=["Smith, J."],
        year=2023,
        doi="10.1234/abc"
    )
    
    issues = checker.check(ref)
    doi_issues = [i for i in issues if i.field == "doi"]
    
    # Should suggest https://doi.org/ format
    assert any("https://doi.org/" in (i.suggestion or "") for i in doi_issues), \
        "Should suggest https://doi.org/ format"
    print("  [PASS] test_apa_doi_format")


def test_apa_missing_doi_warning():
    """Warn about missing DOI for recent articles."""
    checker = APAChecker()
    
    # Recent article without DOI
    ref = ParsedReference(
        raw_text="Smith, J. (2020). Title. Journal, 10(2), 123-145.",
        reference_number=1,
        authors=["Smith, J."],
        year=2020,
        title="Title",
        doi=None
    )
    
    issues = checker.check(ref)
    doi_issues = [i for i in issues if i.field == "doi"]
    
    # Should have warning about missing DOI
    assert any(i.severity == IssueSeverity.WARNING for i in doi_issues), \
        "Should warn about missing DOI for recent article"
    print("  [PASS] test_apa_missing_doi_warning")


def test_apa_batch_check():
    """Batch APA checking with summary."""
    checker = APAChecker()
    
    refs = [
        ParsedReference(
            raw_text="Smith J (2023). Title. Journal.",
            reference_number=1,
            authors=["Smith J"],
            year=2023
        ),
        ParsedReference(
            raw_text="Doe, A. (2022). Title. Journal.",
            reference_number=2,
            authors=["Doe, A."],
            year=2022
        )
    ]
    
    result = checker.check_batch(refs)
    
    assert "summary" in result, "Should have summary"
    assert "total_errors" in result, "Should have error count"
    assert "total_warnings" in result, "Should have warning count"
    print("  [PASS] test_apa_batch_check")


# ==================== REPORT GENERATOR TESTS ====================

def test_report_terminal_output():
    """Generate terminal report."""
    generator = ReportGenerator()
    
    report = VerificationReport(
        document_name="test_document.pdf",
        timestamp="2024-01-31 12:00:00",
        total_references=10,
        verified_count=7,
        suspicious_count=2,
        not_found_count=1,
        error_count=0,
        references=[
            ReferenceReport(
                reference_number=1,
                raw_citation="Smith, J. (2023). Test article.",
                verification_status="VERIFIED",
                confidence=0.95
            ),
            ReferenceReport(
                reference_number=2,
                raw_citation="Fake, A. (2023). Hallucinated paper.",
                verification_status="NOT_FOUND",
                confidence=0.15,
                discrepancies=["No match found in PubMed or CrossRef"]
            )
        ]
    )
    
    output = generator.generate(report, "terminal")
    
    assert "REFERENCE VERIFICATION REPORT" in output, "Should have header"
    assert "test_document.pdf" in output, "Should include document name"
    assert "VERIFIED" in output or "Verified" in output, "Should show verified status"
    assert "NOT_FOUND" in output or "Not Found" in output, "Should show not found"
    print("  [PASS] test_report_terminal_output")


def test_report_json_output():
    """Generate JSON report."""
    generator = ReportGenerator()
    
    report = VerificationReport(
        document_name="test.pdf",
        timestamp="2024-01-31 12:00:00",
        total_references=5,
        verified_count=4,
        suspicious_count=1,
        not_found_count=0,
        error_count=0
    )
    
    output = generator.generate(report, "json")
    
    import json
    data = json.loads(output)
    
    assert data["document_name"] == "test.pdf", "Should have document name"
    assert data["summary"]["verified"] == 4, "Should have verified count"
    assert "verified_percentage" in data["summary"], "Should have percentage"
    print("  [PASS] test_report_json_output")


def test_report_html_output():
    """Generate HTML report."""
    generator = ReportGenerator()
    
    report = VerificationReport(
        document_name="thesis.pdf",
        timestamp="2024-01-31 12:00:00",
        total_references=20,
        verified_count=18,
        suspicious_count=1,
        not_found_count=1,
        error_count=0,
        apa_errors_total=3,
        apa_warnings_total=5
    )
    
    output = generator.generate(report, "html")
    
    assert "<!DOCTYPE html>" in output, "Should be valid HTML"
    assert "thesis.pdf" in output, "Should include document name"
    assert "Reference Verification Report" in output, "Should have title"
    assert "PubMed Reference Checker" in output, "Should have footer"
    print("  [PASS] test_report_html_output")


# ==================== INTEGRATION TEST ====================

def test_full_workflow():
    """Test full reference checking workflow (without actual API calls)."""
    from reference_checker import ReferenceExtractor, APAChecker, ReportGenerator
    from reference_checker import VerificationReport, ReferenceReport
    
    # Simulate a workflow
    extractor = ReferenceExtractor()
    apa_checker = APAChecker()
    report_generator = ReportGenerator()
    
    # Sample references
    sample_refs = [
        "Smith, J. A., & Doe, M. B. (2023). Effects of yoga on anxiety: A meta-analysis. Journal of Clinical Psychology, 79(3), 456-478. https://doi.org/10.1002/jclp.23456",
        "Johnson, R. (2022). Fake Study Title That Does Not Exist. Imaginary Journal, 1(1), 1-10.",
        "Brown K (2021) Improperly Formatted Reference Missing Punctuation"
    ]
    
    # Extract
    parsed_refs = extractor.extract_batch(sample_refs)
    assert len(parsed_refs) == 3, "Should parse 3 references"
    
    # Check APA
    all_apa_issues = []
    for ref in parsed_refs:
        issues = apa_checker.check(ref)
        all_apa_issues.extend(issues)
    
    # The third reference should have issues
    ref3_issues = [i for i in apa_checker.check(parsed_refs[2])]
    assert len(ref3_issues) > 0, "Third reference should have APA issues"
    
    # Generate report
    report = VerificationReport(
        document_name="test_paper.pdf",
        timestamp="2024-01-31",
        total_references=3,
        verified_count=1,
        suspicious_count=1,
        not_found_count=1,
        error_count=0,
        apa_errors_total=sum(1 for i in all_apa_issues if i.severity == IssueSeverity.ERROR),
        apa_warnings_total=sum(1 for i in all_apa_issues if i.severity == IssueSeverity.WARNING),
        references=[
            ReferenceReport(
                reference_number=i+1,
                raw_citation=r.raw_text[:100],
                verification_status="VERIFIED" if i == 0 else "NOT_FOUND" if i == 1 else "SUSPICIOUS",
                confidence=0.9 if i == 0 else 0.1 if i == 1 else 0.6
            )
            for i, r in enumerate(parsed_refs)
        ]
    )
    
    # Test all output formats
    terminal = report_generator.generate(report, "terminal")
    assert "VERIFICATION REPORT" in terminal, "Terminal output should have header"
    
    json_out = report_generator.generate(report, "json")
    assert '"verified": 1' in json_out, "JSON should have verified count"
    
    html_out = report_generator.generate(report, "html")
    assert "<html" in html_out, "HTML should be valid"
    
    print("  [PASS] test_full_workflow")


# ==================== SMOKE TEST ====================

def smoke_test():
    """Quick smoke test for Reference Checker module."""
    print("\n" + "=" * 60)
    print("REFERENCE CHECKER MODULE - SMOKE TEST")
    print("=" * 60)
    
    all_passed = True
    
    print("\n--- Reference Extractor Tests ---")
    try:
        test_extract_doi()
        test_extract_year()
        test_extract_authors()
        test_extract_pmid()
        test_parse_confidence()
        test_batch_extract()
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    except Exception as e:
        print(f"  [ERROR] {e}")
        all_passed = False
    
    print("\n--- APA Checker Tests ---")
    try:
        test_apa_author_format()
        test_apa_year_format()
        test_apa_doi_format()
        test_apa_missing_doi_warning()
        test_apa_batch_check()
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    except Exception as e:
        print(f"  [ERROR] {e}")
        all_passed = False
    
    print("\n--- Report Generator Tests ---")
    try:
        test_report_terminal_output()
        test_report_json_output()
        test_report_html_output()
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    except Exception as e:
        print(f"  [ERROR] {e}")
        all_passed = False
    
    print("\n--- Integration Tests ---")
    try:
        test_full_workflow()
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    except Exception as e:
        print(f"  [ERROR] {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL REFERENCE CHECKER TESTS PASSED")
    else:
        print("SOME TESTS FAILED - Review output above")
    print("=" * 60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = smoke_test()
    sys.exit(0 if success else 1)
