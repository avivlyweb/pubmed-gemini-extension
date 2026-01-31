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
    NOT_FOUND = "NOT_FOUND"         # No match found - likely fake
    UNPARSEABLE = "UNPARSEABLE"     # Could not parse reference
    ERROR = "ERROR"                 # Verification error occurred


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
    
    # Additional info
    verification_sources: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


# Confidence thresholds
THRESHOLD_VERIFIED = 0.80
THRESHOLD_SUSPICIOUS = 0.50


class VerificationEngine:
    """
    Multi-source reference verification.
    
    Checks references against:
    1. PubMed (reuses existing PubMedClient)
    2. DOI.org (HTTP resolution)
    3. CrossRef API (fallback)
    """
    
    # CrossRef API base URL
    CROSSREF_API = "https://api.crossref.org/works"
    DOI_RESOLVER = "https://doi.org"
    
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
        Verify a single reference.
        
        Verification cascade:
        1. If DOI present -> check DOI resolution first
        2. Search PubMed by title + author + year
        3. If no PubMed match -> try CrossRef API
        4. Calculate overall confidence
        """
        from .reference_extractor import ParsedReference
        
        # Check cache
        cache_key = self._get_cache_key(ref)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        sources_checked = []
        discrepancies = []
        best_confidence = 0.0
        pubmed_match = None
        crossref_match = None
        doi_valid = None
        
        try:
            # 1. Check DOI if present
            if ref.doi:
                doi_valid = await self._check_doi(ref.doi)
                sources_checked.append("DOI.org")
                if doi_valid:
                    best_confidence = max(best_confidence, 0.9)
                else:
                    discrepancies.append(f"DOI does not resolve: {ref.doi}")
            
            # 2. Search PubMed
            pubmed_match = await self._check_pubmed(ref)
            sources_checked.append("PubMed")
            
            if pubmed_match:
                best_confidence = max(best_confidence, pubmed_match.confidence)
                # Check for discrepancies
                discrepancies.extend(self._find_discrepancies(ref, pubmed_match))
            
            # 3. If no good PubMed match, try CrossRef
            if best_confidence < THRESHOLD_VERIFIED:
                crossref_match = await self._check_crossref(ref)
                sources_checked.append("CrossRef")
                
                if crossref_match:
                    best_confidence = max(best_confidence, crossref_match.confidence)
            
            # Determine status
            if best_confidence >= THRESHOLD_VERIFIED:
                status = VerificationStatus.VERIFIED
            elif best_confidence >= THRESHOLD_SUSPICIOUS:
                status = VerificationStatus.SUSPICIOUS
            else:
                status = VerificationStatus.NOT_FOUND
            
            result = VerificationResult(
                status=status,
                confidence=best_confidence,
                pubmed_match=pubmed_match,
                crossref_match=crossref_match,
                doi_valid=doi_valid,
                discrepancies=discrepancies,
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
    
    def _calculate_match_confidence(self, ref: 'ParsedReference', article) -> float:
        """Calculate fuzzy match confidence between reference and PubMed article."""
        scores = []
        
        # Title similarity (60% weight)
        if ref.title and article.title:
            title_sim = self._string_similarity(ref.title.lower(), article.title.lower())
            scores.append(("title", title_sim, 0.6))
        
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
        """Calculate confidence for CrossRef match."""
        scores = []
        
        # Title similarity
        if ref.title and item.get("title"):
            item_title = item["title"][0] if isinstance(item["title"], list) else item["title"]
            title_sim = self._string_similarity(ref.title.lower(), item_title.lower())
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
        """Calculate string similarity using token overlap."""
        # Simple token-based similarity
        tokens1 = set(re.findall(r'\w+', s1.lower()))
        tokens2 = set(re.findall(r'\w+', s2.lower()))
        
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
