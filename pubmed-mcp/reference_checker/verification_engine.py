"""
Verification Engine - Check reference existence across multiple sources.

Sources:
- PubMed (via existing PubMedClient)
- DOI.org (direct resolution)
- CrossRef API (fallback for non-medical papers)

Uses fuzzy matching to compare cited reference with database records.
"""

import asyncio
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


class VerificationStatus(str, Enum):
    """Status of reference verification."""
    VERIFIED = "VERIFIED"           # High confidence match found
    SUSPICIOUS = "SUSPICIOUS"       # Partial match, some discrepancies
    NOT_FOUND = "NOT_FOUND"         # No match found in databases
    DEFINITE_FAKE = "DEFINITE_FAKE" # 100% certain fake (DOI points to wrong paper, impossible dates)
    LIKELY_VALID = "LIKELY_VALID"   # Probably valid but not in our databases (grey literature, non-medical)
    UNPARSEABLE = "UNPARSEABLE"     # Could not parse reference
    ERROR = "ERROR"                 # Verification error occurred


class FakeIndicator(str, Enum):
    """Indicators of definitely fake references."""
    DOI_FIELD_MISMATCH = "DOI_FIELD_MISMATCH"     # DOI points to completely different field
    FUTURE_DATE = "FUTURE_DATE"                   # Publication date is in the future
    TRUNCATED_DOI = "TRUNCATED_DOI"               # DOI is malformed/truncated
    DOI_DIFFERENT_PAPER = "DOI_DIFFERENT_PAPER"   # DOI resolves to different paper entirely


@dataclass
class PubMedMatch:
    """Match result from PubMed."""
    pmid: str
    title: str
    authors: List[str]
    year: Optional[int]
    journal: Optional[str]
    doi: Optional[str]
    confidence: float  # 0.0 - 1.0


@dataclass
class CrossRefMatch:
    """Match result from CrossRef."""
    doi: str
    title: str
    authors: List[str]
    year: Optional[int]
    journal: Optional[str]
    confidence: float


@dataclass
class VerificationResult:
    """Result of verifying a single reference."""
    status: VerificationStatus
    confidence: float  # 0.0 - 1.0
    
    # Match details
    pubmed_match: Optional[PubMedMatch] = None
    crossref_match: Optional[CrossRefMatch] = None
    doi_valid: Optional[bool] = None
    
    # Discrepancies found
    discrepancies: List[str] = field(default_factory=list)
    
    # NEW: Fake indicators (for DEFINITE_FAKE status)
    fake_indicators: List[str] = field(default_factory=list)
    
    # NEW: False positive warnings (why this might NOT be fake)
    false_positive_warnings: List[str] = field(default_factory=list)
    
    # NEW: Manual verification links
    manual_verify_links: Dict[str, str] = field(default_factory=dict)
    
    # Additional info
    verification_sources: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


# Confidence thresholds
THRESHOLD_VERIFIED = 0.80
THRESHOLD_SUSPICIOUS = 0.50
THRESHOLD_TITLE_MATCH = 0.60  # Minimum title similarity to accept a match

# Try to import rapidfuzz for better string similarity
try:
    from rapidfuzz import fuzz as rapidfuzz_fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

# Medical/biomedical journal keywords (for field detection)
MEDICAL_JOURNAL_KEYWORDS = {
    'medicine', 'medical', 'clinical', 'health', 'disease', 'therapy', 'therapeutic',
    'pharmaceutical', 'drug', 'cancer', 'cardiology', 'neurology', 'surgery', 'nursing',
    'psychiatry', 'psychology', 'pediatric', 'lancet', 'bmj', 'jama', 'nejm', 'annals',
    'archives', 'journal of biological', 'biochem', 'molecular', 'cell', 'genetics',
    'immunology', 'infection', 'virus', 'pathology', 'pharmacology', 'toxicology',
    'epidemiology', 'public health', 'nutrition', 'obesity', 'diabetes', 'heart',
    'lung', 'kidney', 'liver', 'brain', 'blood', 'bone', 'skin', 'eye', 'ear',
    'dental', 'oral', 'rehabilitation', 'physical therapy', 'occupational therapy',
    'radiology', 'imaging', 'ultrasound', 'mri', 'oncology', 'hospice', 'palliative'
}

# Non-medical journal indicators (likely false positive if not found in PubMed)
NON_MEDICAL_INDICATORS = {
    'computer', 'computing', 'software', 'information system', 'artificial intelligence',
    'machine learning', 'data science', 'engineering', 'physics', 'chemistry', 'materials',
    'education', 'educational', 'learning', 'teaching', 'pedagogy', 'curriculum',
    'business', 'management', 'economics', 'finance', 'marketing', 'organization',
    'social', 'sociology', 'anthropology', 'political', 'law', 'legal', 'humanities',
    'philosophy', 'ethics', 'literature', 'linguistics', 'history', 'art', 'music',
    'environment', 'ecology', 'sustainability', 'energy', 'renewable', 'climate',
    'expert systems', 'decision support', 'automation', 'robotics', 'ieee', 'acm'
}

# Truncated DOI patterns that indicate parsing errors
TRUNCATED_DOI_PATTERNS = [
    r'^10\.\d{4}/[a-z]$',           # e.g., "10.1016/j" 
    r'^10\.\d{4}/[a-z]{1,2}$',      # e.g., "10.1016/jo"
    r'^10\.\d{4}$',                 # e.g., "10.1016"
    r'^10\.\d{4}/[a-z]\.$',         # e.g., "10.1016/j."
    r'^10\.\d{4,}/978-$',           # Truncated book DOI
]


class VerificationEngine:
    """
    Multi-source reference verification.
    
    Checks references against:
    1. PubMed (reuses existing PubMedClient)
    2. DOI.org (HTTP resolution)
    3. CrossRef API (fallback)
    """
    
    # API base URLs for multi-source fallback
    CROSSREF_API = "https://api.crossref.org/works"
    DOI_RESOLVER = "https://doi.org"
    OPENALEX_API = "https://api.openalex.org/works"
    EUROPE_PMC_API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    
    def __init__(self, pubmed_client=None, email: Optional[str] = None):
        """
        Initialize verification engine.
        
        Args:
            pubmed_client: Optional PubMedClient instance (will create one if not provided)
            email: Optional email for CrossRef polite pool (recommended)
        """
        self._pubmed_client = pubmed_client
        self._owns_pubmed_client = False
        self._email = email
        self._http_client = None
        self._cache: Dict[str, VerificationResult] = {}
    
    async def _get_pubmed_client(self):
        """Get or create PubMed client."""
        if self._pubmed_client is None:
            # Import here to avoid circular imports
            import sys
            sys.path.insert(0, '..')
            from pubmed_mcp import PubMedClient
            self._pubmed_client = PubMedClient()
            self._owns_pubmed_client = True
        return self._pubmed_client
    
    async def _get_http_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            import httpx
            headers = {"User-Agent": "ReferenceChecker/1.0"}
            if self._email:
                headers["User-Agent"] = f"ReferenceChecker/1.0 (mailto:{self._email})"
            self._http_client = httpx.AsyncClient(timeout=30.0, headers=headers)
        return self._http_client
    
    async def close(self):
        """Close HTTP clients."""
        if self._owns_pubmed_client and self._pubmed_client:
            await self._pubmed_client.close()
        if self._http_client:
            await self._http_client.aclose()
    
    async def verify(self, ref: 'ParsedReference') -> VerificationResult:
        """
        Verify a single reference with tiered confidence system.
        
        Verification cascade:
        1. Check for DEFINITE_FAKE indicators (100% certain fakes)
        2. If DOI present -> check DOI resolution (with retry)
        3. Search PubMed by title + author + year
        4. If no PubMed match -> try CrossRef API
        5. Check for LIKELY_VALID indicators (probable false positives)
        6. Calculate overall confidence and status
        """
        from .reference_extractor import ParsedReference
        from datetime import datetime
        import urllib.parse
        
        # Check cache
        cache_key = self._get_cache_key(ref)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        sources_checked = []
        discrepancies = []
        fake_indicators = []
        false_positive_warnings = []
        manual_verify_links = {}
        best_confidence = 0.0
        pubmed_match = None
        crossref_match = None
        doi_valid = None
        
        try:
            current_year = datetime.now().year
            
            # === STEP 0: Check for DEFINITE_FAKE indicators ===
            
            # Check for truncated/malformed DOI (parsing error indicator)
            if ref.doi:
                for pattern in TRUNCATED_DOI_PATTERNS:
                    if re.match(pattern, ref.doi, re.IGNORECASE):
                        fake_indicators.append(f"Truncated/malformed DOI: {ref.doi} (likely PDF parsing error)")
                        break
            
            # Check for future publication dates (impossible)
            if ref.year and ref.year > current_year:
                fake_indicators.append(f"Future publication date: {ref.year} (currently {current_year})")
            
            # === STEP 1: Check DOI if present (with multi-source fallback) ===
            doi_metadata = None
            if ref.doi and not any("Truncated" in fi for fi in fake_indicators):
                # First try HEAD request with retry
                doi_valid = await self._check_doi_with_retry(ref.doi)
                sources_checked.append("DOI.org")
                
                if doi_valid:
                    best_confidence = max(best_confidence, 0.9)
                    # Get metadata for Frankenstein detection
                    _, doi_metadata = await self._multi_source_doi_check(ref.doi)
                elif doi_valid is False:
                    # DOI doesn't exist per doi.org, but try other sources
                    doi_exists, doi_metadata = await self._multi_source_doi_check(ref.doi)
                    sources_checked.append("CrossRef-DOI")
                    sources_checked.append("OpenAlex")
                    
                    if doi_exists:
                        doi_valid = True
                        best_confidence = max(best_confidence, 0.85)
                    else:
                        discrepancies.append(f"DOI does not resolve (checked doi.org, CrossRef, OpenAlex): {ref.doi}")
                else:
                    # Indeterminate (network issues) - try fallback sources
                    doi_exists, doi_metadata = await self._multi_source_doi_check(ref.doi)
                    if doi_exists:
                        doi_valid = True
                        best_confidence = max(best_confidence, 0.85)
                        sources_checked.append("CrossRef-DOI")
                
                # Frankenstein detection: DOI exists but metadata doesn't match citation
                if doi_valid and doi_metadata and ref.title:
                    metadata_title = doi_metadata.get("title", "")
                    if metadata_title:
                        title_sim = self._string_similarity(ref.title.lower(), metadata_title.lower())
                        if title_sim < 0.30:
                            fake_indicators.append(
                                f"FRANKENSTEIN CITATION: DOI resolves to different paper. "
                                f"Cited: '{ref.title[:50]}...' vs DOI actual: '{metadata_title[:50]}...'"
                            )
            
            # === STEP 2: Search PubMed ===
            pubmed_match = await self._check_pubmed(ref)
            sources_checked.append("PubMed")
            
            if pubmed_match:
                best_confidence = max(best_confidence, pubmed_match.confidence)
                # Check for discrepancies
                ref_discrepancies = self._find_discrepancies(ref, pubmed_match)
                discrepancies.extend(ref_discrepancies)
                
                # Check for DOI pointing to completely different paper (DEFINITE_FAKE)
                if ref.doi and pubmed_match.doi:
                    if ref.doi.lower() != pubmed_match.doi.lower():
                        # Check if fields are completely different
                        if self._is_field_mismatch(ref, pubmed_match):
                            fake_indicators.append(
                                f"DOI mismatch with field difference: cited DOI for '{ref.journal or 'unknown'}' "
                                f"but PubMed match is from '{pubmed_match.journal}'"
                            )
            
            # === STEP 3: If no good PubMed match, try CrossRef ===
            if best_confidence < THRESHOLD_VERIFIED:
                crossref_match = await self._check_crossref(ref)
                sources_checked.append("CrossRef")
                
                if crossref_match:
                    best_confidence = max(best_confidence, crossref_match.confidence)
                    
                    # If CrossRef found it but PubMed didn't, check if non-medical field
                    if crossref_match.confidence >= THRESHOLD_VERIFIED and not pubmed_match:
                        if self._is_non_medical_journal(ref.journal or crossref_match.journal or ""):
                            false_positive_warnings.append(
                                f"Not in PubMed but found in CrossRef - this appears to be a non-medical "
                                f"journal ('{crossref_match.journal}') which PubMed may not index"
                            )
            
            # === STEP 3.5: If still no good match, try Europe PMC ===
            if best_confidence < THRESHOLD_VERIFIED:
                europe_pmc_result = await self._check_via_europe_pmc(ref)
                if europe_pmc_result:
                    sources_checked.append("Europe PMC")
                    # Calculate confidence based on title match
                    if europe_pmc_result.get("title") and ref.title:
                        title_sim = self._string_similarity(
                            ref.title.lower(), 
                            europe_pmc_result["title"].lower()
                        )
                        pmc_confidence = title_sim * 0.8  # Slightly lower weight
                        best_confidence = max(best_confidence, pmc_confidence)
                        
                        if pmc_confidence >= THRESHOLD_VERIFIED and not pubmed_match:
                            false_positive_warnings.append(
                                f"Found in Europe PMC (PMID: {europe_pmc_result.get('pmid', 'N/A')}) - "
                                f"may be a European publication or preprint"
                            )
            
            # === STEP 4: Check for LIKELY_VALID indicators ===
            
            # Classic works (pre-1980) often show wrong years due to reprints
            if ref.year and ref.year < 1980:
                if pubmed_match and pubmed_match.year and pubmed_match.year > 2000:
                    false_positive_warnings.append(
                        f"Classic work from {ref.year} - database shows {pubmed_match.year} "
                        f"(likely a modern reprint/ebook edition, not necessarily fake)"
                    )
            
            # Web resources / grey literature
            if ref.raw_text and any(indicator in ref.raw_text.lower() for indicator in 
                ['retrieved from', 'accessed', 'http://', 'https://', '.gov', '.org/report']):
                if best_confidence < THRESHOLD_SUSPICIOUS:
                    false_positive_warnings.append(
                        "This appears to be a web resource or grey literature - "
                        "these are not indexed in academic databases but may still be valid"
                    )
            
            # Non-medical journal not in PubMed
            if not pubmed_match and ref.journal:
                if self._is_non_medical_journal(ref.journal):
                    false_positive_warnings.append(
                        f"Journal '{ref.journal}' appears to be outside PubMed's biomedical scope - "
                        f"not finding it in PubMed is expected, not an indicator of fakeness"
                    )
            
            # === STEP 5: Generate manual verification links ===
            if ref.title:
                encoded_title = urllib.parse.quote(ref.title[:100])
                manual_verify_links["google_scholar"] = f"https://scholar.google.com/scholar?q={encoded_title}"
                manual_verify_links["crossref"] = f"https://search.crossref.org/?q={encoded_title}"
            if ref.doi:
                manual_verify_links["doi_resolver"] = f"https://doi.org/{ref.doi}"
            
            # === STEP 6: Determine final status ===
            
            # DEFINITE_FAKE: Strong indicators of fabrication
            if fake_indicators and not false_positive_warnings:
                # Future date + not found = definitely fake
                if any("Future publication" in fi for fi in fake_indicators) and best_confidence < THRESHOLD_SUSPICIOUS:
                    status = VerificationStatus.DEFINITE_FAKE
                # DOI points to completely different field = definitely fake  
                elif any("field difference" in fi for fi in fake_indicators):
                    status = VerificationStatus.DEFINITE_FAKE
                # Frankenstein citation = definitely fake
                elif any("FRANKENSTEIN" in fi for fi in fake_indicators):
                    status = VerificationStatus.DEFINITE_FAKE
                else:
                    status = VerificationStatus.SUSPICIOUS
            
            # LIKELY_VALID: Has false positive warnings and some match
            elif false_positive_warnings and best_confidence >= 0.3:
                status = VerificationStatus.LIKELY_VALID
            
            # Standard confidence-based status
            elif best_confidence >= THRESHOLD_VERIFIED:
                status = VerificationStatus.VERIFIED
            elif best_confidence >= THRESHOLD_SUSPICIOUS:
                status = VerificationStatus.SUSPICIOUS
            else:
                # NOT_FOUND but check if we should warn about false positives
                if false_positive_warnings:
                    status = VerificationStatus.LIKELY_VALID
                else:
                    status = VerificationStatus.NOT_FOUND
            
            result = VerificationResult(
                status=status,
                confidence=best_confidence,
                pubmed_match=pubmed_match,
                crossref_match=crossref_match,
                doi_valid=doi_valid,
                discrepancies=discrepancies,
                fake_indicators=fake_indicators,
                false_positive_warnings=false_positive_warnings,
                manual_verify_links=manual_verify_links,
                verification_sources=sources_checked
            )
            
        except Exception as e:
            result = VerificationResult(
                status=VerificationStatus.ERROR,
                confidence=0.0,
                error_message=str(e),
                verification_sources=sources_checked
            )
        
        # Cache result
        self._cache[cache_key] = result
        return result
    
    def _is_non_medical_journal(self, journal: str) -> bool:
        """Check if journal is likely non-medical (would cause false PubMed negatives)."""
        journal_lower = journal.lower()
        
        # Check for medical indicators first
        for keyword in MEDICAL_JOURNAL_KEYWORDS:
            if keyword in journal_lower:
                return False
        
        # Check for non-medical indicators
        for keyword in NON_MEDICAL_INDICATORS:
            if keyword in journal_lower:
                return True
        
        return False
    
    def _is_field_mismatch(self, ref: 'ParsedReference', match: PubMedMatch) -> bool:
        """Check if reference and match are from completely different fields."""
        ref_journal = (ref.journal or "").lower()
        match_journal = (match.journal or "").lower()
        
        # If one is medical and other is not, it's a mismatch
        ref_is_medical = any(kw in ref_journal for kw in MEDICAL_JOURNAL_KEYWORDS)
        match_is_medical = any(kw in match_journal for kw in MEDICAL_JOURNAL_KEYWORDS)
        
        ref_is_non_medical = any(kw in ref_journal for kw in NON_MEDICAL_INDICATORS)
        match_is_non_medical = any(kw in match_journal for kw in NON_MEDICAL_INDICATORS)
        
        # Clear mismatch: one is medical, other is non-medical
        if (ref_is_non_medical and match_is_medical) or (ref_is_medical and match_is_non_medical):
            return True
        
        return False

    def _is_metadata_mismatch(self, ref: 'ParsedReference', match: PubMedMatch) -> bool:
        """
        Check for 'Frankenstein' citation: DOI exists but belongs to a different paper.
        
        Returns True if there is a significant mismatch between the cited title/year
        and the metadata retrieved from the DOI resolution.
        """
        if not ref.title or not match.title:
            return False

        # Title Similarity Check
        # Frankenstein cases often have completely different titles (e.g. "LLM feedback" vs "Scoping studies")
        title_sim = self._string_similarity(ref.title.lower(), match.title.lower())
        
        # Threshold: If titles are less than 30% similar, it's extremely suspicious
        if title_sim < 0.3:
            return True
            
        # Year Check
        # If years are widely apart (e.g. 2024 vs 2005)
        if ref.year and match.year:
            year_diff = abs(ref.year - match.year)
            if year_diff > 5: # 5 year tolerance for reprints, but 20 is suspicious
                 # Combining low-ish similarity with bad year
                 if title_sim < 0.5:
                     return True
                     
        return False

    
    async def _check_doi_with_retry(self, doi: str, max_retries: int = 3) -> bool:
        """Check if DOI resolves with retry logic for network issues."""
        import asyncio
        
        for attempt in range(max_retries):
            try:
                client = await self._get_http_client()
                url = f"{self.DOI_RESOLVER}/{doi}"
                response = await client.head(url, follow_redirects=True, timeout=10.0)
                if response.status_code == 200:
                    return True
                elif response.status_code == 404:
                    return False  # Definitely doesn't exist
            except Exception:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                    continue
        
        # After retries, assume network issue - don't mark as fake
        return None  # Indeterminate
    
    async def verify_batch(self, refs: List['ParsedReference'], 
                          max_concurrent: int = 5) -> List[VerificationResult]:
        """
        Verify multiple references with rate limiting.
        
        Args:
            refs: List of parsed references
            max_concurrent: Maximum concurrent verifications
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def verify_with_limit(ref):
            async with semaphore:
                return await self.verify(ref)
        
        tasks = [verify_with_limit(ref) for ref in refs]
        return await asyncio.gather(*tasks)
    
    async def _check_doi(self, doi: str) -> bool:
        """Check if DOI resolves."""
        try:
            client = await self._get_http_client()
            url = f"{self.DOI_RESOLVER}/{doi}"
            response = await client.head(url, follow_redirects=True)
            return response.status_code == 200
        except Exception:
            return False
    
    async def _check_pubmed(self, ref: 'ParsedReference') -> Optional[PubMedMatch]:
        """Search PubMed for matching article."""
        try:
            client = await self._get_pubmed_client()
            
            # Build search query
            query_parts = []
            
            if ref.title:
                # Use title with quotes for phrase search
                clean_title = re.sub(r'[^\w\s]', '', ref.title)[:100]
                query_parts.append(f'"{clean_title}"[Title]')
            
            if ref.authors and len(ref.authors) > 0:
                # Add first author
                first_author = ref.authors[0].split(',')[0]  # Last name only
                query_parts.append(f'{first_author}[Author]')
            
            if ref.year:
                query_parts.append(f'{ref.year}[Date - Publication]')
            
            if not query_parts:
                return None
            
            query = " AND ".join(query_parts)
            pmids = await client.search(query, max_results=5)
            
            if not pmids:
                # Try broader search with just title keywords
                if ref.title:
                    words = ref.title.split()[:5]
                    query = " ".join(words)
                    pmids = await client.search(query, max_results=5)
            
            if not pmids:
                return None
            
            # Fetch first article and calculate match confidence
            article = await client.fetch_article(pmids[0])
            if not article:
                return None
            
            # Calculate fuzzy match confidence
            confidence = self._calculate_match_confidence(ref, article)
            
            # Extract year from pub_date
            year = None
            if article.pub_date:
                year_match = re.search(r'\d{4}', article.pub_date)
                if year_match:
                    year = int(year_match.group())
            
            return PubMedMatch(
                pmid=article.pmid,
                title=article.title,
                authors=article.authors,
                year=year,
                journal=article.journal,
                doi=article.doi,
                confidence=confidence
            )
            
        except Exception as e:
            # Log error but don't fail
            return None
    
    async def _check_crossref(self, ref: 'ParsedReference') -> Optional[CrossRefMatch]:
        """Search CrossRef for matching article."""
        try:
            client = await self._get_http_client()
            
            params = {}
            if ref.title:
                params["query.title"] = ref.title[:200]
            if ref.authors and len(ref.authors) > 0:
                # First author's last name
                first_author = ref.authors[0].split(',')[0]
                params["query.author"] = first_author
            
            if not params:
                return None
            
            params["rows"] = 5
            
            response = await client.get(self.CROSSREF_API, params=params)
            if response.status_code != 200:
                return None
            
            data = response.json()
            items = data.get("message", {}).get("items", [])
            
            if not items:
                return None
            
            # Take first result
            item = items[0]
            
            # Extract data
            title = ""
            if item.get("title"):
                title = item["title"][0] if isinstance(item["title"], list) else item["title"]
            
            authors = []
            for author in item.get("author", []):
                if author.get("family"):
                    name = author.get("family", "")
                    if author.get("given"):
                        name = f"{author['given']} {name}"
                    authors.append(name)
            
            year = None
            if item.get("published-print", {}).get("date-parts"):
                year = item["published-print"]["date-parts"][0][0]
            elif item.get("published-online", {}).get("date-parts"):
                year = item["published-online"]["date-parts"][0][0]
            
            journal = None
            if item.get("container-title"):
                journal = item["container-title"][0] if isinstance(item["container-title"], list) else item["container-title"]
            
            # Calculate confidence
            confidence = self._calculate_crossref_confidence(ref, item)
            
            return CrossRefMatch(
                doi=item.get("DOI", ""),
                title=title,
                authors=authors,
                year=year,
                journal=journal,
                confidence=confidence
            )
            
        except Exception:
            return None
    
    async def _check_doi_via_crossref(self, doi: str) -> Optional[CrossRefMatch]:
        """
        Direct CrossRef lookup by DOI when HEAD request fails.
        
        This is more reliable than HEAD to doi.org because:
        1. Some DOIs don't respond to HEAD but exist in CrossRef
        2. CrossRef provides metadata to detect Frankenstein citations
        """
        try:
            client = await self._get_http_client()
            url = f"{self.CROSSREF_API}/{doi}"
            
            response = await client.get(url, timeout=15.0)
            if response.status_code != 200:
                return None
            
            data = response.json()
            item = data.get("message", {})
            
            if not item:
                return None
            
            # Extract metadata
            title = ""
            if item.get("title"):
                title = item["title"][0] if isinstance(item["title"], list) else item["title"]
            
            authors = []
            for author in item.get("author", []):
                if author.get("family"):
                    name = author.get("family", "")
                    if author.get("given"):
                        name = f"{author['given']} {name}"
                    authors.append(name)
            
            year = None
            if item.get("published-print", {}).get("date-parts"):
                year = item["published-print"]["date-parts"][0][0]
            elif item.get("published-online", {}).get("date-parts"):
                year = item["published-online"]["date-parts"][0][0]
            
            journal = None
            if item.get("container-title"):
                journal = item["container-title"][0] if isinstance(item["container-title"], list) else item["container-title"]
            
            return CrossRefMatch(
                doi=doi,
                title=title,
                authors=authors,
                year=year,
                journal=journal,
                confidence=1.0  # Direct DOI match = high confidence
            )
            
        except Exception:
            return None
    
    async def _check_doi_via_openalex(self, doi: str) -> Optional[dict]:
        """
        OpenAlex lookup by DOI - free API, no key required.
        
        Returns dict with title, authors, year for Frankenstein detection.
        """
        try:
            client = await self._get_http_client()
            # OpenAlex uses doi: prefix in the URL
            url = f"{self.OPENALEX_API}/doi:{doi}"
            
            response = await client.get(url, timeout=15.0)
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            title = data.get("title", "")
            year = data.get("publication_year")
            
            authors = []
            for authorship in data.get("authorships", []):
                author = authorship.get("author", {})
                if author.get("display_name"):
                    authors.append(author["display_name"])
            
            journal = None
            primary_location = data.get("primary_location", {})
            if primary_location:
                source = primary_location.get("source", {})
                if source:
                    journal = source.get("display_name")
            
            return {
                "doi": doi,
                "title": title,
                "authors": authors,
                "year": year,
                "journal": journal,
                "source": "OpenAlex"
            }
            
        except Exception:
            return None
    
    async def _check_via_europe_pmc(self, ref: 'ParsedReference') -> Optional[dict]:
        """
        Europe PMC search - better coverage for European biomedical papers.
        
        Also indexes preprints and has different coverage than PubMed.
        """
        try:
            client = await self._get_http_client()
            
            # Build query
            query_parts = []
            if ref.title:
                # Use first 100 chars of title
                clean_title = re.sub(r'[^\w\s]', '', ref.title)[:100]
                query_parts.append(f'TITLE:"{clean_title}"')
            
            if ref.authors and len(ref.authors) > 0:
                first_author = ref.authors[0].split(',')[0]
                query_parts.append(f'AUTH:"{first_author}"')
            
            if not query_parts:
                return None
            
            query = " AND ".join(query_parts)
            
            params = {
                "query": query,
                "format": "json",
                "pageSize": 5,
                "resultType": "core"
            }
            
            response = await client.get(self.EUROPE_PMC_API, params=params)
            if response.status_code != 200:
                return None
            
            data = response.json()
            results = data.get("resultList", {}).get("result", [])
            
            if not results:
                return None
            
            # Take first result
            item = results[0]
            
            authors = []
            if item.get("authorString"):
                # "Smith J, Jones B, et al." -> ["Smith J", "Jones B"]
                author_str = item["authorString"].replace(" et al.", "")
                authors = [a.strip() for a in author_str.split(",")]
            
            return {
                "pmid": item.get("pmid"),
                "pmcid": item.get("pmcid"),
                "doi": item.get("doi"),
                "title": item.get("title", ""),
                "authors": authors,
                "year": int(item.get("pubYear", 0)) if item.get("pubYear") else None,
                "journal": item.get("journalTitle"),
                "source": "Europe PMC"
            }
            
        except Exception:
            return None
    
    async def _multi_source_doi_check(self, doi: str) -> tuple:
        """
        Try multiple sources to verify DOI exists and get metadata.
        
        Returns:
            (exists: bool, metadata: Optional[dict])
            - exists: True if DOI found in any source
            - metadata: Dict with title, authors, year from best source
        """
        # Try CrossRef direct lookup first (most reliable)
        crossref_result = await self._check_doi_via_crossref(doi)
        if crossref_result:
            return True, {
                "title": crossref_result.title,
                "authors": crossref_result.authors,
                "year": crossref_result.year,
                "journal": crossref_result.journal,
                "source": "CrossRef"
            }
        
        # Try OpenAlex
        openalex_result = await self._check_doi_via_openalex(doi)
        if openalex_result:
            return True, openalex_result
        
        # If all fail, DOI likely doesn't exist
        return False, None
    
    def _calculate_match_confidence(self, ref: 'ParsedReference', article) -> float:
        """
        Calculate fuzzy match confidence between reference and PubMed article.
        
        IMPORTANT: Enforces minimum title similarity threshold (THRESHOLD_TITLE_MATCH)
        to prevent false positives where author matches but title is completely different.
        """
        scores = []
        title_sim = 0.0
        
        # Title similarity (60% weight)
        if ref.title and article.title:
            title_sim = self._string_similarity(ref.title.lower(), article.title.lower())
            scores.append(("title", title_sim, 0.6))
            
            # CRITICAL: Reject match entirely if title similarity is too low
            # This prevents "Frankenstein" matches where author matches but paper is wrong
            if title_sim < THRESHOLD_TITLE_MATCH:
                return 0.0  # Reject this match
        
        # Author match (25% weight)
        if ref.authors and article.authors:
            author_match = self._author_similarity(ref.authors, article.authors)
            scores.append(("author", author_match, 0.25))
        
        # Year match (15% weight)
        if ref.year and article.pub_date:
            year_match = re.search(r'\d{4}', article.pub_date)
            if year_match:
                article_year = int(year_match.group())
                year_sim = 1.0 if ref.year == article_year else 0.0
                scores.append(("year", year_sim, 0.15))
        
        if not scores:
            return 0.0
        
        # Weighted average
        total_weight = sum(w for _, _, w in scores)
        weighted_sum = sum(s * w for _, s, w in scores)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _calculate_crossref_confidence(self, ref: 'ParsedReference', item: dict) -> float:
        """
        Calculate confidence for CrossRef match.
        
        Enforces minimum title similarity threshold to prevent false positives.
        """
        scores = []
        title_sim = 0.0
        
        # Title similarity
        if ref.title and item.get("title"):
            item_title = item["title"][0] if isinstance(item["title"], list) else item["title"]
            title_sim = self._string_similarity(ref.title.lower(), item_title.lower())
            
            # CRITICAL: Reject match if title is too different
            if title_sim < THRESHOLD_TITLE_MATCH:
                return 0.0
            
            scores.append(title_sim * 0.6)
        
        # Author match
        if ref.authors and item.get("author"):
            ref_first_author = ref.authors[0].split(',')[0].lower() if ref.authors else ""
            item_authors = [a.get("family", "").lower() for a in item.get("author", [])]
            if ref_first_author and ref_first_author in item_authors:
                scores.append(0.25)
        
        # Year match
        if ref.year:
            item_year = None
            if item.get("published-print", {}).get("date-parts"):
                item_year = item["published-print"]["date-parts"][0][0]
            elif item.get("published-online", {}).get("date-parts"):
                item_year = item["published-online"]["date-parts"][0][0]
            if item_year == ref.year:
                scores.append(0.15)
        
        return sum(scores) if scores else 0.0
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """
        Calculate string similarity using best available method.
        
        Uses rapidfuzz if available (much better for typos, word order variations),
        falls back to token overlap Jaccard if not.
        """
        if not s1 or not s2:
            return 0.0
        
        # Normalize strings
        s1_clean = s1.lower().strip()
        s2_clean = s2.lower().strip()
        
        if HAS_RAPIDFUZZ:
            # Use token_set_ratio which handles word order and partial matches well
            # Returns 0-100, we need 0.0-1.0
            score = rapidfuzz_fuzz.token_set_ratio(s1_clean, s2_clean) / 100.0
            return score
        else:
            # Fallback: token-based Jaccard similarity
            tokens1 = set(re.findall(r'\w+', s1_clean))
            tokens2 = set(re.findall(r'\w+', s2_clean))
            
            if not tokens1 or not tokens2:
                return 0.0
            
            intersection = tokens1 & tokens2
            union = tokens1 | tokens2
            
            return len(intersection) / len(union) if union else 0.0
    
    def _author_similarity(self, ref_authors: List[str], article_authors: List[str]) -> float:
        """Calculate author list similarity."""
        if not ref_authors or not article_authors:
            return 0.0
        
        # Normalize names (last names only)
        ref_last_names = {a.split(',')[0].lower().strip() for a in ref_authors}
        article_last_names = {a.split()[-1].lower().strip() for a in article_authors}
        
        intersection = ref_last_names & article_last_names
        
        # At least first author should match
        ref_first = list(ref_authors)[0].split(',')[0].lower().strip()
        article_first = article_authors[0].split()[-1].lower().strip() if article_authors else ""
        
        first_match = 1.0 if ref_first == article_first else 0.5
        
        # Overlap ratio
        overlap = len(intersection) / max(len(ref_last_names), 1)
        
        return (first_match * 0.6) + (overlap * 0.4)
    
    def _find_discrepancies(self, ref: 'ParsedReference', match: PubMedMatch) -> List[str]:
        """Find discrepancies between reference and matched article."""
        discrepancies = []
        
        # Check for Frankenstein mismatch (Wrong DOI)
        if self._is_metadata_mismatch(ref, match):
             discrepancies.append(
                 f"METADATA MISMATCH: Cited '{ref.title[:50]}...' ({ref.year}) but DOI resolves to "
                 f"'{match.title[:50]}...' ({match.year}). This DOI likely belongs to a different paper."
             )
        
        # Year mismatch
        if ref.year and match.year and ref.year != match.year:
            discrepancies.append(f"Year: cited {ref.year}, actual {match.year}")
        
        # Title significantly different
        if ref.title and match.title:
            sim = self._string_similarity(ref.title, match.title)
            if sim < 0.5:
                discrepancies.append(f"Title differs significantly (similarity: {sim:.0%})")
        
        # DOI mismatch
        if ref.doi and match.doi and ref.doi.lower() != match.doi.lower():
            discrepancies.append(f"DOI mismatch: cited {ref.doi}, actual {match.doi}")
        
        return discrepancies
    
    def _get_cache_key(self, ref: 'ParsedReference') -> str:
        """Generate cache key for reference."""
        parts = []
        if ref.doi:
            parts.append(f"doi:{ref.doi}")
        if ref.pmid:
            parts.append(f"pmid:{ref.pmid}")
        if ref.title:
            parts.append(f"title:{ref.title[:50]}")
        if ref.year:
            parts.append(f"year:{ref.year}")
        return "|".join(parts) if parts else ref.raw_text[:100]
