"""
Reference Checker Module v2.7.0

Verify academic paper references for:
- Existence in PubMed, DOI.org, and CrossRef
- APA 7th Edition style compliance
- Detection of AI-hallucinated/fake citations

This module is additive - it does NOT modify any existing PubMed MCP functionality.
"""

__version__ = "2.7.0"

# Import components with error handling for optional dependencies
from .document_parser import DocumentParser, DocumentContent
from .reference_extractor import ReferenceExtractor, ParsedReference
from .verification_engine import (
    VerificationEngine, 
    VerificationResult,
    VerificationStatus,
    PubMedMatch,
    CrossRefMatch
)
from .apa_checker import APAChecker, APAIssue, IssueSeverity
from .report_generator import (
    ReportGenerator, 
    VerificationReport,
    ReferenceReport,
    BatchSummary
)

__all__ = [
    # Version
    "__version__",
    # Document parsing
    "DocumentParser",
    "DocumentContent", 
    # Reference extraction
    "ReferenceExtractor",
    "ParsedReference",
    # Verification
    "VerificationEngine",
    "VerificationResult",
    "VerificationStatus",
    "PubMedMatch",
    "CrossRefMatch",
    # APA checking
    "APAChecker",
    "APAIssue",
    "IssueSeverity",
    # Report generation
    "ReportGenerator",
    "VerificationReport",
    "ReferenceReport",
    "BatchSummary",
]
