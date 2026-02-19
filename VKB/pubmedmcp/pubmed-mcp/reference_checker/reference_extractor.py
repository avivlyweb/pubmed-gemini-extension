"""
Reference Extractor - Parse individual citations into structured data.

Extracts from raw citation text:
- Authors
- Year
- Title
- Journal
- Volume, Issue, Pages
- DOI
- PMID (if present)
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ParsedReference:
    """Structured representation of a citation."""
    raw_text: str
    reference_number: int
    
    # Parsed fields
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    title: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None
    
    # Parsing confidence
    parse_confidence: float = 0.0  # 0.0 - 1.0
    parse_warnings: List[str] = field(default_factory=list)


class ReferenceExtractor:
    """
    Parse individual citations into structured data.
    
    Handles APA 7th Edition format primarily, with fallbacks for other styles.
    
    ABC-TOM v3.0.0: Includes text cleaning to remove PDF noise (headers, footers, etc.)
    """
    
    # ==========================================================================
    # ABC-TOM v3.0.0: PDF Noise Patterns to Filter
    # ==========================================================================
    PDF_NOISE_PATTERNS = [
        re.compile(r'^Downloaded from.*$', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^Available at.*$', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^Access provided by.*$', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^Vol\s*\d+.*$', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^Volume\s*\d+.*$', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^Copyright\s*©?.*$', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^All rights reserved.*$', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^\s*\d{1,3}\s*$', re.MULTILINE),  # Page numbers only
        re.compile(r'^https?://[^\s]+\s*$', re.MULTILINE),  # Bare URLs on own line
        re.compile(r'^This article.*$', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^Author.*manuscript.*$', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^Funding.*$', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^Conflict of interest.*$', re.IGNORECASE | re.MULTILINE),
    ]
    
    # Regex patterns for extraction
    
    # DOI pattern - matches various DOI formats
    DOI_PATTERN = re.compile(
        r'(?:https?://)?(?:dx\.)?doi\.org/(10\.\d{4,}/[^\s\]>]+)|'
        r'doi:\s*(10\.\d{4,}/[^\s\]>]+)|'
        r'\bdoi\s*[=:]\s*(10\.\d{4,}/[^\s\]>]+)',
        re.IGNORECASE
    )
    
    # PMID pattern
    PMID_PATTERN = re.compile(
        r'PMID:\s*(\d+)|'
        r'PubMed\s*(?:ID)?:\s*(\d+)|'
        r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)',
        re.IGNORECASE
    )
    
    # Year pattern - (2023) or 2023
    YEAR_PATTERN = re.compile(r'\((\d{4})\)|(?<!\d)(\d{4})(?!\d)')
    
    # Author patterns for APA style
    # Matches: Smith, J. A. or Smith, John A. or Smith, J.
    APA_AUTHOR_PATTERN = re.compile(
        r'([A-Z][a-z]+(?:[-\'][A-Z][a-z]+)?),\s*'  # Last name
        r'([A-Z]\.(?:\s*[A-Z]\.)*|[A-Z][a-z]+(?:\s+[A-Z]\.)?)',  # First/middle initials or name
        re.UNICODE
    )
    
    # Multiple authors connected by &, and, or comma
    AUTHOR_SEPARATOR = re.compile(r'\s*[,&]\s*|\s+and\s+', re.IGNORECASE)
    
    # Volume, issue, pages pattern: 15(3), 123-145 or Vol. 15, No. 3, pp. 123-145
    VOLUME_ISSUE_PAGES = re.compile(
        r'(\d+)\s*\((\d+(?:-\d+)?)\)\s*[,:]?\s*(\d+(?:[-–]\d+)?)|'  # 15(3), 123-145
        r'[Vv]ol\.?\s*(\d+).*?[Nn]o\.?\s*(\d+).*?[Pp]p\.?\s*(\d+(?:[-–]\d+)?)',
        re.IGNORECASE
    )
    
    # URL pattern
    URL_PATTERN = re.compile(
        r'https?://[^\s\]>]+',
        re.IGNORECASE
    )
    
    def extract(self, raw_text: str, reference_number: int = 0) -> ParsedReference:
        """
        Parse a raw citation text into structured data.
        
        Args:
            raw_text: The raw citation text
            reference_number: The reference number in the document
            
        Returns:
            ParsedReference with extracted fields
        """
        # ABC-TOM v3.0.0: Clean PDF noise before parsing
        cleaned_text = self.clean_pdf_noise(raw_text)
        
        ref = ParsedReference(
            raw_text=raw_text.strip(),  # Keep original for reference
            reference_number=reference_number
        )
        
        warnings = []
        confidence_scores = []
        
        # Extract DOI first (most reliable identifier)
        doi = self._extract_doi(cleaned_text)
        if doi:
            ref.doi = doi
            confidence_scores.append(1.0)
        
        # Extract PMID
        pmid = self._extract_pmid(cleaned_text)
        if pmid:
            ref.pmid = pmid
            confidence_scores.append(1.0)
        
        # Extract year
        year = self._extract_year(cleaned_text)
        if year:
            ref.year = year
            confidence_scores.append(0.9)
        else:
            warnings.append("Could not extract publication year")
        
        # Extract authors
        authors = self._extract_authors(cleaned_text)
        if authors:
            ref.authors = authors
            confidence_scores.append(0.8)
        else:
            warnings.append("Could not extract authors")
        
        # Extract title (text between year and journal/volume)
        title = self._extract_title(cleaned_text, year)
        if title:
            ref.title = title
            confidence_scores.append(0.7)
        else:
            warnings.append("Could not extract title")
        
        # Extract journal and volume/issue/pages
        journal, volume, issue, pages = self._extract_journal_info(cleaned_text)
        if journal:
            ref.journal = journal
            confidence_scores.append(0.6)
        if volume:
            ref.volume = volume
        if issue:
            ref.issue = issue
        if pages:
            ref.pages = pages
        
        # Extract URL
        url = self._extract_url(cleaned_text)
        if url and not ref.doi:  # Don't duplicate DOI URLs
            ref.url = url
        
        # Calculate overall confidence
        if confidence_scores:
            ref.parse_confidence = sum(confidence_scores) / len(confidence_scores)
        else:
            ref.parse_confidence = 0.1
            warnings.append("Very low parsing confidence - citation may be malformed")
        
        ref.parse_warnings = warnings
        
        return ref
    
    def clean_pdf_noise(self, text: str) -> str:
        """
        Remove common PDF parsing noise from reference text.
        
        ABC-TOM Learning Log patterns:
        - "Downloaded from..." lines (page footers)
        - "Vol 59..." lines (header contamination)
        - Page numbers on their own line
        - Copyright notices
        - "Access provided by..." watermarks
        
        Also fixes:
        - Hyphenation splits: "pharma-\\ncology" -> "pharmacology"
        - Excessive whitespace
        """
        if not text:
            return text
        
        cleaned = text
        
        # Remove lines matching noise patterns
        for pattern in self.PDF_NOISE_PATTERNS:
            cleaned = pattern.sub('', cleaned)
        
        # Fix hyphenation splits (word-\nontinuation -> wordcontinuation)
        # But preserve intentional hyphens (e.g., "well-known")
        cleaned = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', cleaned)
        
        # Collapse multiple newlines into single newline
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # Collapse multiple spaces into single space
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        
        # Strip leading/trailing whitespace from each line
        lines = [line.strip() for line in cleaned.split('\n')]
        cleaned = '\n'.join(line for line in lines if line)
        
        return cleaned.strip()
    
    def extract_batch(self, entries: List[str]) -> List[ParsedReference]:
        """Parse multiple citation entries."""
        return [self.extract(entry, i + 1) for i, entry in enumerate(entries)]
    
    def _normalize_doi_text(self, text: str) -> str:
        """
        Reconstruct DOIs that may be split across lines in PDFs.
        
        Handles:
        - Soft hyphens (Unicode U+00AD)
        - Hyphen-continued lines: "10.1186/s12909-\n024-06399-7" → "10.1186/s12909-024-06399-7"
        - Space-split DOIs: "10.1234/abc def" → "10.1234/abcdef"
        - Line breaks within DOIs
        """
        # Remove soft hyphens (invisible characters used for line breaks)
        text = text.replace('\u00ad', '')
        
        # Join hyphen-continued lines: "abc-\n  def" → "abc-def"
        # This handles DOIs split with hyphen at line end
        text = re.sub(r'-\s*[\n\r]+\s*', '-', text)
        
        # Join DOI-specific line breaks: "10.1234/x\n  y" → "10.1234/xy"
        # Match a partial DOI followed by newline and continuation
        text = re.sub(r'(10\.\d{4,}/[^\s\n]*?)[\n\r]+\s*([^\s\n]+)', r'\1\2', text)
        
        # Remove spaces within DOI suffix (PDF parsing artifact)
        # "10.1186/s12909-024-06399- 7" → "10.1186/s12909-024-06399-7"
        # Only do this for patterns that look like broken DOIs
        text = re.sub(r'(10\.\d{4,}/\S+)-\s+(\d)', r'\1-\2', text)
        
        return text
    
    def _extract_doi(self, text: str) -> Optional[str]:
        """Extract DOI from text, handling line breaks and PDF parsing artifacts."""
        # First, normalize the text to reconstruct split DOIs
        normalized = self._normalize_doi_text(text)
        
        match = self.DOI_PATTERN.search(normalized)
        if match:
            # Get the first non-None group
            for group in match.groups():
                if group:
                    # Clean up DOI (remove trailing punctuation)
                    doi = re.sub(r'[.,;:\s]+$', '', group)
                    return doi
        
        # Fallback: try original text if normalization didn't help
        if normalized != text:
            match = self.DOI_PATTERN.search(text)
            if match:
                for group in match.groups():
                    if group:
                        doi = re.sub(r'[.,;:\s]+$', '', group)
                        return doi
        
        return None
    
    def _extract_pmid(self, text: str) -> Optional[str]:
        """Extract PubMed ID from text."""
        match = self.PMID_PATTERN.search(text)
        if match:
            for group in match.groups():
                if group:
                    return group
        return None
    
    def _extract_year(self, text: str) -> Optional[int]:
        """Extract publication year."""
        # Look for year in parentheses first (APA style)
        paren_match = re.search(r'\((\d{4})\)', text)
        if paren_match:
            year = int(paren_match.group(1))
            if 1900 <= year <= 2030:
                return year
        
        # Look for any 4-digit year
        matches = self.YEAR_PATTERN.findall(text)
        for match in matches:
            year_str = match[0] or match[1]
            if year_str:
                year = int(year_str)
                if 1900 <= year <= 2030:
                    return year
        
        return None
    
    def _extract_authors(self, text: str) -> List[str]:
        """Extract author names."""
        authors = []
        
        # Find the part before the year (usually contains authors)
        year_match = re.search(r'\(\d{4}\)', text)
        if year_match:
            author_section = text[:year_match.start()]
        else:
            # Take first part before a period followed by title-case word
            parts = re.split(r'\.\s+(?=[A-Z])', text, maxsplit=1)
            author_section = parts[0] if parts else text[:200]
        
        # Find all author patterns
        matches = self.APA_AUTHOR_PATTERN.findall(author_section)
        for last_name, first_initials in matches:
            author = f"{last_name}, {first_initials}"
            if author not in authors:
                authors.append(author)
        
        # Limit to reasonable number
        return authors[:20]
    
    def _extract_title(self, text: str, year: Optional[int]) -> Optional[str]:
        """Extract article title."""
        # In APA, title comes after (Year). and before the journal (usually italicized)
        
        if year:
            # Find text after year
            year_pattern = rf'\({year}\)\.\s*'
            match = re.search(year_pattern, text)
            if match:
                after_year = text[match.end():]
                
                # Title ends at the first journal-like pattern or second period
                # Look for pattern: Title. Journal Name, volume
                title_match = re.match(r'([^.]+(?:\.[^.]+)?)\.\s*[A-Z]', after_year)
                if title_match:
                    return title_match.group(1).strip()
                
                # Fallback: take first sentence
                period_pos = after_year.find('.')
                if period_pos > 10:
                    return after_year[:period_pos].strip()
        
        # Fallback: try to find title between common markers
        # Look for quoted title or title followed by journal
        quoted = re.search(r'"([^"]+)"', text)
        if quoted:
            return quoted.group(1)
        
        return None
    
    def _extract_journal_info(self, text: str) -> tuple:
        """Extract journal name, volume, issue, and pages."""
        journal = None
        volume = None
        issue = None
        pages = None
        
        # Find volume(issue), pages pattern first
        vol_match = self.VOLUME_ISSUE_PAGES.search(text)
        if vol_match:
            groups = vol_match.groups()
            if groups[0]:  # Standard format: 15(3), 123-145
                volume = groups[0]
                issue = groups[1]
                pages = groups[2]
            elif groups[3]:  # Vol. / No. format
                volume = groups[3]
                issue = groups[4]
                pages = groups[5]
            
            # Journal name is usually before the volume/issue pattern
            # And after the title (which ends with a period)
            pre_volume = text[:vol_match.start()]
            # Find the last sentence before volume info
            sentences = pre_volume.split('.')
            if len(sentences) >= 2:
                potential_journal = sentences[-2].strip()
                # Journal names are usually Title Case
                if potential_journal and re.match(r'^[A-Z][a-zA-Z\s&]+$', potential_journal):
                    journal = potential_journal
        
        # Alternative: look for italic markers or known journal patterns
        if not journal:
            # Look for common journal name patterns
            journal_match = re.search(
                r'(?:journal of|annals of|archives of|[a-z]+ [a-z]+ journal)\s+[a-z\s]+',
                text,
                re.IGNORECASE
            )
            if journal_match:
                journal = journal_match.group().strip()
        
        return journal, volume, issue, pages
    
    def _extract_url(self, text: str) -> Optional[str]:
        """Extract URL from text."""
        match = self.URL_PATTERN.search(text)
        if match:
            url = match.group()
            # Don't return DOI URLs as regular URLs
            if 'doi.org' not in url:
                return url
        return None
