"""
APA Style Checker - Validate APA 7th Edition formatting.

Checks:
- Author format: Last, F. M., & Last, F. M.
- Year format: (2023).
- Title case: Sentence case for articles, Title Case for journals
- DOI format: https://doi.org/10.xxxx/xxxx
- Punctuation and spacing
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Literal
from enum import Enum


class IssueSeverity(str, Enum):
    """Severity level of APA issue."""
    ERROR = "error"      # Definite formatting error
    WARNING = "warning"  # Possible issue or style preference


@dataclass
class APAIssue:
    """A single APA formatting issue."""
    field: str           # "author", "year", "title", "journal", "doi", etc.
    severity: IssueSeverity
    message: str
    suggestion: Optional[str] = None  # Corrected format
    position: Optional[int] = None    # Character position in citation


class APAChecker:
    """
    Validate APA 7th Edition citation formatting.
    
    Based on:
    - Publication Manual of the American Psychological Association (7th ed.)
    - APA Style Blog guidelines
    """
    
    # ==================== PATTERNS ====================
    
    # Valid author format: Last, F. M. or Last, F.
    AUTHOR_PATTERN = re.compile(
        r'^[A-Z][a-z]+(?:[-\'][A-Z][a-z]+)?,\s+'  # Last name with comma
        r'[A-Z]\.\s*(?:[A-Z]\.)?$'                 # Initials
    )
    
    # Year in parentheses
    YEAR_PATTERN = re.compile(r'\((\d{4}[a-z]?)\)\.')
    
    # DOI format (APA 7th prefers https://doi.org/ format)
    DOI_PATTERN = re.compile(r'https://doi\.org/10\.\d+/[^\s]+$')
    DOI_OLD_FORMAT = re.compile(r'(?:doi:|DOI:)\s*10\.\d+')
    DOI_DX_FORMAT = re.compile(r'https?://dx\.doi\.org/')
    
    # URL patterns
    URL_PATTERN = re.compile(r'https?://[^\s]+')
    
    # Common title case words that should be lowercase in sentence case
    LOWERCASE_WORDS = {
        'a', 'an', 'the', 'and', 'but', 'or', 'nor', 'for', 'yet', 'so',
        'at', 'by', 'in', 'of', 'on', 'to', 'up', 'as', 'is', 'it'
    }
    
    def check(self, ref: 'ParsedReference') -> List[APAIssue]:
        """
        Run all APA checks on a parsed reference.
        
        Args:
            ref: ParsedReference object
            
        Returns:
            List of APAIssue objects
        """
        from .reference_extractor import ParsedReference
        
        issues = []
        
        # Check each component
        issues.extend(self._check_author_format(ref))
        issues.extend(self._check_year_format(ref))
        issues.extend(self._check_title_format(ref))
        issues.extend(self._check_doi_format(ref))
        issues.extend(self._check_punctuation(ref))
        issues.extend(self._check_required_fields(ref))
        
        return issues
    
    def check_batch(self, refs: List['ParsedReference']) -> dict:
        """
        Check multiple references and return summary.
        
        Returns:
            Dict with 'issues' list and 'summary' counts
        """
        all_issues = []
        issue_counts = {}
        
        for ref in refs:
            ref_issues = self.check(ref)
            for issue in ref_issues:
                all_issues.append({
                    'reference_number': ref.reference_number,
                    'issue': issue
                })
                key = issue.field
                issue_counts[key] = issue_counts.get(key, 0) + 1
        
        return {
            'issues': all_issues,
            'summary': issue_counts,
            'total_errors': sum(1 for i in all_issues if i['issue'].severity == IssueSeverity.ERROR),
            'total_warnings': sum(1 for i in all_issues if i['issue'].severity == IssueSeverity.WARNING)
        }
    
    def _check_author_format(self, ref: 'ParsedReference') -> List[APAIssue]:
        """Check author name formatting."""
        issues = []
        
        if not ref.authors:
            return issues
        
        for i, author in enumerate(ref.authors):
            # Check basic format: Last, F. M.
            if not self.AUTHOR_PATTERN.match(author):
                # Identify specific issue
                if ', ' not in author:
                    issues.append(APAIssue(
                        field="author",
                        severity=IssueSeverity.ERROR,
                        message=f"Author {i+1} missing comma after last name",
                        suggestion=self._suggest_author_format(author)
                    ))
                elif not re.search(r'[A-Z]\.', author):
                    issues.append(APAIssue(
                        field="author",
                        severity=IssueSeverity.ERROR,
                        message=f"Author {i+1} should use initials (e.g., 'Smith, J. A.')",
                        suggestion=self._suggest_author_format(author)
                    ))
        
        # Check ampersand usage for multiple authors
        raw = ref.raw_text
        if len(ref.authors) == 2:
            if ' and ' in raw.lower()[:raw.find('(') if '(' in raw else len(raw)]:
                if ' & ' not in raw[:raw.find('(') if '(' in raw else len(raw)]:
                    issues.append(APAIssue(
                        field="author",
                        severity=IssueSeverity.WARNING,
                        message="Use '&' instead of 'and' between authors",
                        suggestion="Smith, J., & Doe, A."
                    ))
        
        # Check for et al. usage (should only be in-text, not reference list)
        if 'et al' in raw.lower():
            issues.append(APAIssue(
                field="author",
                severity=IssueSeverity.ERROR,
                message="'et al.' should not appear in reference list - list all authors (up to 20)",
                suggestion="List all authors: Last, F., Last, F., & Last, F."
            ))
        
        return issues
    
    def _check_year_format(self, ref: 'ParsedReference') -> List[APAIssue]:
        """Check year formatting."""
        issues = []
        raw = ref.raw_text
        
        # Year should be in parentheses followed by period
        year_match = self.YEAR_PATTERN.search(raw)
        
        if ref.year:
            if not year_match:
                # Check if year exists but wrong format
                if str(ref.year) in raw:
                    if f'({ref.year})' not in raw:
                        issues.append(APAIssue(
                            field="year",
                            severity=IssueSeverity.ERROR,
                            message="Year should be in parentheses",
                            suggestion=f"({ref.year})."
                        ))
                    elif f'({ref.year}).' not in raw:
                        issues.append(APAIssue(
                            field="year",
                            severity=IssueSeverity.WARNING,
                            message="Period should follow closing parenthesis after year",
                            suggestion=f"({ref.year})."
                        ))
        
        return issues
    
    def _check_title_format(self, ref: 'ParsedReference') -> List[APAIssue]:
        """Check title formatting (should be sentence case)."""
        issues = []
        
        if not ref.title:
            return issues
        
        title = ref.title.strip()
        
        # Skip if title is very short
        if len(title) < 10:
            return issues
        
        # Check for all caps (common error)
        if title.isupper():
            issues.append(APAIssue(
                field="title",
                severity=IssueSeverity.ERROR,
                message="Title should not be in ALL CAPS - use sentence case",
                suggestion=self._to_sentence_case(title)
            ))
            return issues
        
        # Check for Title Case (common error)
        words = title.split()
        if len(words) >= 3:
            # Count capitalized words (excluding first word and acronyms)
            cap_count = sum(
                1 for w in words[1:] 
                if w[0].isupper() and not w.isupper() and len(w) > 3
                and w.lower() not in self.LOWERCASE_WORDS
            )
            
            if cap_count >= len(words) * 0.5:
                issues.append(APAIssue(
                    field="title",
                    severity=IssueSeverity.WARNING,
                    message="Title appears to be in Title Case - APA uses sentence case",
                    suggestion=self._to_sentence_case(title)
                ))
        
        return issues
    
    def _check_doi_format(self, ref: 'ParsedReference') -> List[APAIssue]:
        """Check DOI formatting (APA 7th prefers https://doi.org/ format)."""
        issues = []
        raw = ref.raw_text
        
        if ref.doi:
            # Check for preferred format
            if not self.DOI_PATTERN.search(raw):
                # Check for old format
                if self.DOI_OLD_FORMAT.search(raw):
                    issues.append(APAIssue(
                        field="doi",
                        severity=IssueSeverity.WARNING,
                        message="DOI should use https://doi.org/ format (APA 7th)",
                        suggestion=f"https://doi.org/{ref.doi}"
                    ))
                elif self.DOI_DX_FORMAT.search(raw):
                    issues.append(APAIssue(
                        field="doi",
                        severity=IssueSeverity.WARNING,
                        message="Use 'https://doi.org/' instead of 'http://dx.doi.org/'",
                        suggestion=f"https://doi.org/{ref.doi}"
                    ))
            
            # Check for period after DOI (should NOT have one)
            doi_in_text = ref.doi
            if f"{doi_in_text}." in raw or f"{doi_in_text}," in raw:
                issues.append(APAIssue(
                    field="doi",
                    severity=IssueSeverity.WARNING,
                    message="No period or comma after DOI at end of reference",
                    suggestion=f"https://doi.org/{ref.doi}"
                ))
        
        # Check for missing DOI (common for newer articles)
        if not ref.doi and ref.year and ref.year >= 2000:
            issues.append(APAIssue(
                field="doi",
                severity=IssueSeverity.WARNING,
                message="Consider adding DOI - most articles from 2000+ have DOIs",
                suggestion="Add DOI if available"
            ))
        
        return issues
    
    def _check_punctuation(self, ref: 'ParsedReference') -> List[APAIssue]:
        """Check punctuation and spacing."""
        issues = []
        raw = ref.raw_text
        
        # Check for double spaces
        if '  ' in raw:
            issues.append(APAIssue(
                field="spacing",
                severity=IssueSeverity.WARNING,
                message="Remove double spaces",
                suggestion=None
            ))
        
        # Check for space before period
        if re.search(r'\s+\.', raw):
            issues.append(APAIssue(
                field="punctuation",
                severity=IssueSeverity.WARNING,
                message="Remove space before period",
                suggestion=None
            ))
        
        # Check for proper journal italics (can't really detect, just note)
        # This would need to check the original document formatting
        
        return issues
    
    def _check_required_fields(self, ref: 'ParsedReference') -> List[APAIssue]:
        """Check for required fields."""
        issues = []
        
        if not ref.authors:
            issues.append(APAIssue(
                field="author",
                severity=IssueSeverity.ERROR,
                message="Missing author(s)",
                suggestion=None
            ))
        
        if not ref.year:
            issues.append(APAIssue(
                field="year",
                severity=IssueSeverity.ERROR,
                message="Missing publication year",
                suggestion=None
            ))
        
        if not ref.title:
            issues.append(APAIssue(
                field="title",
                severity=IssueSeverity.ERROR,
                message="Missing title",
                suggestion=None
            ))
        
        return issues
    
    def _suggest_author_format(self, author: str) -> str:
        """Suggest correct author format."""
        # Try to parse and reformat
        parts = re.split(r'[,\s]+', author.strip())
        if len(parts) >= 2:
            last_name = parts[0]
            initials = ''.join(f"{p[0].upper()}. " for p in parts[1:] if p)
            return f"{last_name}, {initials.strip()}"
        return author
    
    def _to_sentence_case(self, title: str) -> str:
        """Convert title to sentence case."""
        if not title:
            return title
        
        # Lowercase everything first
        result = title.lower()
        
        # Capitalize first letter
        result = result[0].upper() + result[1:]
        
        # Capitalize after colon
        result = re.sub(r':\s+([a-z])', lambda m: ': ' + m.group(1).upper(), result)
        
        # Keep acronyms uppercase (sequences of capitals in original)
        for match in re.finditer(r'\b[A-Z]{2,}\b', title):
            acronym = match.group()
            result = re.sub(
                rf'\b{acronym.lower()}\b',
                acronym,
                result,
                flags=re.IGNORECASE
            )
        
        return result
