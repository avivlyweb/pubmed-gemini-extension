#!/usr/bin/env python3
"""
PubMed MCP Server - PhD-level medical research analysis
Standalone implementation compatible with Python 3.9+

Provides tools for searching PubMed, analyzing article trustworthiness, 
and generating research summaries with PICO analysis.
"""

import asyncio
import json
import re
import sys
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any, Callable, Tuple
from datetime import datetime

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip3 install httpx", file=sys.stderr)
    sys.exit(1)

# PubMed E-utilities base URLs
PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PUBMED_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# Study design keywords for classification
STUDY_DESIGN_PATTERNS = {
    "systematic_review": [
        r"systematic review", r"meta-analysis", r"meta analysis", 
        r"cochrane", r"prisma", r"pooled analysis"
    ],
    "rct": [
        r"randomized controlled trial", r"randomised controlled trial",
        r"rct", r"double-blind", r"placebo-controlled", r"randomization"
    ],
    "cohort": [
        r"cohort study", r"prospective study", r"longitudinal study",
        r"follow-up study", r"observational study"
    ],
    "case_control": [
        r"case-control", r"case control", r"retrospective study"
    ],
    "case_series": [
        r"case series", r"case report", r"case study"
    ],
    "cross_sectional": [
        r"cross-sectional", r"cross sectional", r"prevalence study", r"survey"
    ]
}

# Evidence hierarchy scores
STUDY_DESIGN_SCORES = {
    "systematic_review": 95,
    "rct": 85,
    "cohort": 70,
    "case_control": 60,
    "cross_sectional": 50,
    "case_series": 40,
    "unknown": 30
}

# Evidence grades
EVIDENCE_GRADES = {
    (80, 100): "A",
    (60, 79): "B", 
    (40, 59): "C",
    (0, 39): "D"
}


@dataclass
class PICOAnalysis:
    """PICO framework analysis results"""
    population: str
    intervention: str
    comparison: str
    outcome: str
    clinical_question: str


@dataclass
class EnhancedPICOAnalysis:
    """Enhanced PICO analysis with complexity level and suggestions"""
    population: str
    intervention: str
    comparison: str
    outcome: str
    clinical_question: str
    complexity_level: int  # 1=casual, 2=clinical, 3=research
    complexity_label: str  # "Casual", "Clinical", "Research"
    domain: str  # Medical domain detected
    suggestions: List[str] = field(default_factory=list)  # Suggestions to improve the query
    confidence_score: int = 50  # 0-100 confidence in extraction
    search_terms: List[str] = field(default_factory=list)  # Optimized PubMed search terms


@dataclass
class TrustScore:
    """Article trustworthiness assessment"""
    overall_score: int
    evidence_grade: str
    study_design: str
    methodology_score: int
    sample_size_score: int
    recency_score: int
    journal_score: int
    strengths: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)


@dataclass
class ArticleInfo:
    """PubMed article information"""
    pmid: str
    title: str
    authors: List[str]
    journal: str
    pub_date: str
    abstract: str
    doi: Optional[str]
    pub_types: List[str]
    mesh_terms: List[str]
    # v2.4.0: New fields for full-text access
    pmc_id: Optional[str] = None  # PubMed Central ID for free full text


@dataclass
class FullTextLinks:
    """Full-text access links for an article (v2.4.0)"""
    pubmed_url: str
    doi_url: Optional[str] = None
    pmc_url: Optional[str] = None
    pmc_pdf_url: Optional[str] = None
    open_access: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with only non-None values"""
        result: Dict[str, Any] = {"pubmed": self.pubmed_url}
        if self.doi_url:
            result["doi"] = self.doi_url
        if self.pmc_url:
            result["pmc_fulltext"] = self.pmc_url
        if self.pmc_pdf_url:
            result["pmc_pdf"] = self.pmc_pdf_url
        result["open_access"] = self.open_access
        return result


@dataclass 
class StudySnapshot:
    """2-sentence AI summary of a study (v2.4.0)"""
    summary: str  # 2-sentence summary
    key_finding: str  # "positive", "negative", "neutral", "mixed"
    sample_size: Optional[int] = None
    effect_description: Optional[str] = None  # e.g., "40% reduction", "significant improvement"


class StudySnapshotGenerator:
    """
    Generate 2-sentence study snapshots from abstracts (v2.4.0).
    
    Extracts:
    - Key methodology (what was done)
    - Main finding (what was found)
    - Direction of effect (positive/negative/neutral)
    """
    
    # Patterns for extracting conclusions from structured abstracts
    CONCLUSION_LABELS = [
        "conclusion", "conclusions", "findings", "results", 
        "main outcome", "main outcomes", "interpretation"
    ]
    
    # Patterns indicating positive findings
    POSITIVE_PATTERNS = [
        r"significant(?:ly)?\s+(?:improved|reduced|decreased|increased|better|effective)",
        r"(?:improved|reduced|decreased|increased)\s+significant",
        r"effective\s+(?:in|for|at)",
        r"beneficial\s+effect",
        r"positive\s+(?:effect|outcome|result|impact)",
        r"superior\s+to",
        r"better\s+than",
        r"recommended",
        r"safe\s+and\s+effective",
        r"well[\s-]tolerated",
        r"statistically\s+significant\s+(?:improvement|reduction|benefit)",
    ]
    
    # Patterns indicating negative/no effect findings
    NEGATIVE_PATTERNS = [
        r"no\s+significant\s+(?:difference|effect|improvement|change)",
        r"not\s+(?:effective|significant|associated)",
        r"failed\s+to\s+(?:show|demonstrate|improve)",
        r"no\s+(?:effect|benefit|improvement|difference)",
        r"similar\s+to\s+(?:placebo|control)",
        r"did\s+not\s+(?:improve|reduce|show)",
        r"insufficient\s+evidence",
        r"inconclusive",
        r"no\s+statistical(?:ly)?\s+significant",
    ]
    
    # Patterns for extracting sample size
    SAMPLE_SIZE_PATTERNS = [
        r"(?:n\s*=\s*)(\d+)",
        r"(\d+)\s*(?:patients|participants|subjects|individuals|adults|children)",
        r"(?:sample\s+(?:size|of)\s*)(\d+)",
        r"(?:total\s+of\s*)(\d+)",
        r"(\d+)\s*(?:were\s+(?:enrolled|included|randomized))",
    ]
    
    # Patterns for effect sizes/magnitudes
    EFFECT_PATTERNS = [
        r"(\d+(?:\.\d+)?)\s*%\s*(?:reduction|improvement|decrease|increase)",
        r"(?:reduced|improved|decreased|increased)\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*%",
        r"(?:OR|RR|HR)\s*[=:]\s*(\d+(?:\.\d+)?)",
        r"(?:effect\s+size|cohen['']?s?\s+d)\s*[=:]\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*(?:times|fold)\s+(?:higher|lower|greater|more)",
    ]
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns"""
        self.positive_regex = [re.compile(p, re.IGNORECASE) for p in self.POSITIVE_PATTERNS]
        self.negative_regex = [re.compile(p, re.IGNORECASE) for p in self.NEGATIVE_PATTERNS]
        self.sample_regex = [re.compile(p, re.IGNORECASE) for p in self.SAMPLE_SIZE_PATTERNS]
        self.effect_regex = [re.compile(p, re.IGNORECASE) for p in self.EFFECT_PATTERNS]
    
    def _extract_conclusion_section(self, abstract: str) -> str:
        """Extract conclusion/results section from structured abstract."""
        abstract_lower = abstract.lower()
        
        # Look for labeled sections
        for label in self.CONCLUSION_LABELS:
            # Pattern: "CONCLUSION: text" or "Conclusion: text"
            pattern = rf"{label}s?\s*:\s*(.+?)(?:(?:\n[A-Z]+:)|$)"
            match = re.search(pattern, abstract, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # If no labeled section, return last 2 sentences
        sentences = self._split_sentences(abstract)
        if len(sentences) >= 2:
            return " ".join(sentences[-2:])
        return abstract
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitter
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _determine_finding_direction(self, text: str) -> str:
        """Determine if finding is positive, negative, or neutral."""
        text_lower = text.lower()
        
        positive_count = sum(1 for regex in self.positive_regex if regex.search(text_lower))
        negative_count = sum(1 for regex in self.negative_regex if regex.search(text_lower))
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        elif positive_count > 0 and negative_count > 0:
            return "mixed"
        else:
            return "neutral"
    
    def _extract_sample_size(self, abstract: str) -> Optional[int]:
        """Extract sample size from abstract."""
        for regex in self.sample_regex:
            matches = regex.findall(abstract)
            if matches:
                # Return the largest number found (often the total N)
                try:
                    numbers = [int(m) for m in matches if m.isdigit() or m.replace(',', '').isdigit()]
                    if numbers:
                        return max(numbers)
                except ValueError:
                    continue
        return None
    
    def _extract_effect_description(self, text: str) -> Optional[str]:
        """Extract effect size or magnitude description."""
        for regex in self.effect_regex:
            match = regex.search(text)
            if match:
                # Return the matched text with some context
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                snippet = text[start:end].strip()
                # Clean up
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."
                return snippet
        return None
    
    def _generate_methodology_sentence(self, article: ArticleInfo) -> str:
        """Generate first sentence describing the study methodology."""
        # Determine study type
        study_type = "study"
        pub_types_lower = " ".join(article.pub_types).lower()
        abstract_lower = article.abstract.lower()
        
        if "systematic review" in pub_types_lower or "meta-analysis" in pub_types_lower:
            study_type = "systematic review"
        elif "randomized" in pub_types_lower or "randomized" in abstract_lower:
            study_type = "randomized controlled trial"
        elif "cohort" in abstract_lower:
            study_type = "cohort study"
        elif "cross-sectional" in abstract_lower:
            study_type = "cross-sectional study"
        elif "case-control" in abstract_lower:
            study_type = "case-control study"
        
        # Extract sample size
        sample_size = self._extract_sample_size(article.abstract)
        sample_str = f" with {sample_size} participants" if sample_size else ""
        
        # Get year
        year_match = re.search(r"(\d{4})", article.pub_date)
        year_str = f" ({year_match.group(1)})" if year_match else ""
        
        return f"This {study_type}{sample_str}{year_str} examined the research question."
    
    def _generate_finding_sentence(self, article: ArticleInfo) -> str:
        """Generate second sentence describing the main finding."""
        conclusion = self._extract_conclusion_section(article.abstract)
        direction = self._determine_finding_direction(conclusion)
        
        # Get first meaningful sentence from conclusion
        sentences = self._split_sentences(conclusion)
        if sentences:
            finding = sentences[0]
            # Truncate if too long
            if len(finding) > 200:
                finding = finding[:197] + "..."
            return finding
        
        # Fallback
        direction_text = {
            "positive": "showed beneficial effects",
            "negative": "found no significant effect", 
            "mixed": "showed mixed results",
            "neutral": "reported findings requiring further investigation"
        }
        return f"The study {direction_text.get(direction, 'reported findings')}."
    
    def generate(self, article: ArticleInfo) -> StudySnapshot:
        """Generate a 2-sentence snapshot for an article."""
        if article.abstract == "No abstract available":
            return StudySnapshot(
                summary="No abstract available for this article. Please access the full text for details.",
                key_finding="neutral",
                sample_size=None,
                effect_description=None
            )
        
        # Generate methodology sentence (customized)
        methodology = self._generate_methodology_sentence(article)
        
        # Generate finding sentence
        finding = self._generate_finding_sentence(article)
        
        # Combine into snapshot
        summary = f"{methodology} {finding}"
        
        # Determine overall direction
        key_finding = self._determine_finding_direction(article.abstract)
        
        # Extract additional metadata
        sample_size = self._extract_sample_size(article.abstract)
        effect_desc = self._extract_effect_description(article.abstract)
        
        return StudySnapshot(
            summary=summary,
            key_finding=key_finding,
            sample_size=sample_size,
            effect_description=effect_desc
        )


# ============================================================================
# Key Findings Extractor (v2.5.0)
# ============================================================================

@dataclass
class KeyFinding:
    """Extracted key finding from a study abstract (v2.5.0)"""
    statement: str  # The main finding sentence
    direction: str  # "positive", "negative", "neutral", "mixed"
    effect_size: Optional[str] = None  # e.g., "34% reduction", "SMD=0.77"
    p_value: Optional[str] = None  # e.g., "p<0.001"
    confidence_interval: Optional[str] = None  # e.g., "95% CI [0.65, 0.99]"
    nnt: Optional[int] = None  # Number needed to treat
    practical_significance: Optional[str] = None  # "large", "medium", "small", "negligible"


class KeyFindingsExtractor:
    """
    Extract the KEY finding from an abstract (v2.5.0).
    
    Instead of just truncating the abstract, this extracts:
    - The main result statement
    - Effect sizes (%, SMD, OR, RR, HR)
    - Statistical significance (p-values)
    - Confidence intervals
    - Practical significance assessment
    """
    
    # Patterns for finding result/conclusion sentences
    RESULT_INDICATORS = [
        r"(?:results?|findings?)\s*(?:showed?|indicated?|demonstrated?|revealed?|suggested?)",
        r"(?:we\s+)?found\s+that",
        r"(?:there\s+was|were)\s+(?:a\s+)?significant",
        r"(?:significantly|substantially)\s+(?:reduced|increased|improved|decreased)",
        r"compared\s+(?:to|with)\s+.{1,50}?,\s*.{1,100}?(?:was|were|had)",
        r"the\s+(?:primary|main|principal)\s+(?:outcome|finding|result)",
    ]
    
    # Patterns for effect sizes
    EFFECT_SIZE_PATTERNS = [
        # Percentage changes
        (r"(\d+(?:\.\d+)?)\s*%\s*(?:reduction|decrease|lower)", "reduction", "negative"),
        (r"(\d+(?:\.\d+)?)\s*%\s*(?:increase|improvement|higher)", "increase", "positive"),
        (r"(?:reduced|decreased)\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*%", "reduction", "positive"),
        (r"(?:increased|improved)\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*%", "increase", "positive"),
        # Standardized mean difference
        (r"(?:SMD|standardized mean difference)\s*[=:]\s*[-−]?(\d+(?:\.\d+)?)", "SMD", None),
        (r"(?:Cohen['']?s?\s*)?[dD]\s*[=:]\s*[-−]?(\d+(?:\.\d+)?)", "Cohen's d", None),
        # Odds/Risk/Hazard ratios
        (r"(?:OR|odds ratio)\s*[=:]\s*(\d+(?:\.\d+)?)", "OR", None),
        (r"(?:RR|risk ratio|relative risk)\s*[=:]\s*(\d+(?:\.\d+)?)", "RR", None),
        (r"(?:HR|hazard ratio)\s*[=:]\s*(\d+(?:\.\d+)?)", "HR", None),
        # Mean difference
        (r"(?:MD|mean difference)\s*[=:]\s*[-−]?(\d+(?:\.\d+)?)", "MD", None),
    ]
    
    # P-value patterns
    P_VALUE_PATTERNS = [
        r"p\s*[<≤=]\s*0?\.?\d+",
        r"p\s*-?\s*value\s*[<≤=:]\s*0?\.?\d+",
        r"(?:statistically\s+)?significant\s*\(p\s*[<≤=]\s*0?\.?\d+\)",
    ]
    
    # Confidence interval patterns
    CI_PATTERNS = [
        r"95\s*%?\s*CI\s*[:\s]*\[?\s*[-−]?\d+(?:\.\d+)?\s*[,;to-]+\s*[-−]?\d+(?:\.\d+)?\s*\]?",
        r"CI\s*95\s*%?\s*[:\s]*\[?\s*[-−]?\d+(?:\.\d+)?\s*[,;to-]+\s*[-−]?\d+(?:\.\d+)?\s*\]?",
        r"\(\s*[-−]?\d+(?:\.\d+)?\s*[,;to-]+\s*[-−]?\d+(?:\.\d+)?\s*\)",
    ]
    
    # No effect indicators
    NO_EFFECT_PATTERNS = [
        r"no\s+significant\s+(?:difference|effect|improvement|change)",
        r"did\s+not\s+(?:significantly\s+)?(?:differ|improve|change)",
        r"not\s+statistically\s+significant",
        r"failed\s+to\s+(?:show|demonstrate|reach)",
        r"similar\s+(?:to|between)",
        r"comparable\s+(?:to|between)",
        r"no\s+(?:evidence|benefit)",
    ]
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns"""
        self.result_regex = [re.compile(p, re.IGNORECASE) for p in self.RESULT_INDICATORS]
        self.p_value_regex = [re.compile(p, re.IGNORECASE) for p in self.P_VALUE_PATTERNS]
        self.ci_regex = [re.compile(p, re.IGNORECASE) for p in self.CI_PATTERNS]
        self.no_effect_regex = [re.compile(p, re.IGNORECASE) for p in self.NO_EFFECT_PATTERNS]
    
    def _extract_result_sentences(self, abstract: str) -> List[str]:
        """Extract sentences that contain results."""
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', abstract)
        
        result_sentences = []
        for sentence in sentences:
            # Check if sentence contains result indicators
            for regex in self.result_regex:
                if regex.search(sentence):
                    result_sentences.append(sentence.strip())
                    break
            # Also check for statistical values
            if re.search(r'p\s*[<≤=]\s*0?\.\d+', sentence, re.IGNORECASE):
                if sentence.strip() not in result_sentences:
                    result_sentences.append(sentence.strip())
        
        return result_sentences
    
    def _extract_conclusion_section(self, abstract: str) -> str:
        """Extract conclusion/results section from structured abstract."""
        # Look for labeled sections
        for label in ["conclusion", "conclusions", "results", "findings"]:
            pattern = rf"{label}s?\s*:\s*(.+?)(?:(?:\n[A-Z]+:)|$)"
            match = re.search(pattern, abstract, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        return ""
    
    def _extract_effect_size(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract effect size and determine direction."""
        for pattern, label, direction in self.EFFECT_SIZE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1)
                if label in ["reduction", "decrease"]:
                    return f"{value}% reduction", "positive"  # Reduction is usually good
                elif label in ["increase", "improvement"]:
                    return f"{value}% improvement", "positive"
                elif label == "SMD" or label == "Cohen's d":
                    # Assess practical significance
                    d_value = float(value)
                    if d_value >= 0.8:
                        return f"SMD = {value} (large effect)", None
                    elif d_value >= 0.5:
                        return f"SMD = {value} (medium effect)", None
                    elif d_value >= 0.2:
                        return f"SMD = {value} (small effect)", None
                    else:
                        return f"SMD = {value} (negligible)", None
                elif label in ["OR", "RR", "HR"]:
                    ratio = float(value)
                    if ratio < 1:
                        return f"{label} = {value} (protective)", "positive"
                    elif ratio > 1:
                        return f"{label} = {value} (risk factor)", "negative"
                    else:
                        return f"{label} = {value} (no effect)", "neutral"
                else:
                    return f"{label} = {value}", None
        return None, None
    
    def _extract_p_value(self, text: str) -> Optional[str]:
        """Extract p-value from text."""
        for regex in self.p_value_regex:
            match = regex.search(text)
            if match:
                return match.group(0).strip()
        return None
    
    def _extract_ci(self, text: str) -> Optional[str]:
        """Extract confidence interval from text."""
        for regex in self.ci_regex:
            match = regex.search(text)
            if match:
                return match.group(0).strip()
        return None
    
    def _determine_practical_significance(self, effect_size: Optional[str]) -> Optional[str]:
        """Determine practical significance from effect size."""
        if not effect_size:
            return None
        
        effect_lower = effect_size.lower()
        if "large" in effect_lower:
            return "large"
        elif "medium" in effect_lower:
            return "medium"
        elif "small" in effect_lower:
            return "small"
        elif "negligible" in effect_lower:
            return "negligible"
        
        # Try to infer from percentage
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", effect_size)
        if pct_match:
            pct = float(pct_match.group(1))
            if pct >= 50:
                return "large"
            elif pct >= 25:
                return "medium"
            elif pct >= 10:
                return "small"
            else:
                return "negligible"
        
        return None
    
    def _determine_direction(self, text: str, effect_direction: Optional[str]) -> str:
        """Determine if finding is positive, negative, or neutral."""
        text_lower = text.lower()
        
        # Check for no effect patterns
        for regex in self.no_effect_regex:
            if regex.search(text_lower):
                return "neutral"
        
        # Use effect direction if available
        if effect_direction:
            return effect_direction
        
        # Keyword-based fallback
        positive_keywords = ["effective", "beneficial", "improved", "reduced", "significant improvement"]
        negative_keywords = ["no effect", "ineffective", "no significant", "failed", "no benefit"]
        
        pos_count = sum(1 for kw in positive_keywords if kw in text_lower)
        neg_count = sum(1 for kw in negative_keywords if kw in text_lower)
        
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        else:
            return "neutral"
    
    def extract(self, article: ArticleInfo) -> KeyFinding:
        """Extract the key finding from an article."""
        if article.abstract == "No abstract available":
            return KeyFinding(
                statement="No abstract available",
                direction="neutral"
            )
        
        # Try to get conclusion section first
        conclusion = self._extract_conclusion_section(article.abstract)
        
        # Get result sentences
        result_sentences = self._extract_result_sentences(article.abstract)
        
        # Choose the best sentence for the key finding
        if conclusion:
            # First sentence of conclusion
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', conclusion)
            key_sentence = sentences[0] if sentences else conclusion[:200]
        elif result_sentences:
            # First result sentence
            key_sentence = result_sentences[0]
        else:
            # Fallback: last 2 sentences of abstract (usually conclusion)
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', article.abstract)
            key_sentence = sentences[-1] if sentences else article.abstract[-200:]
        
        # Truncate if too long
        if len(key_sentence) > 250:
            key_sentence = key_sentence[:247] + "..."
        
        # Extract statistical details from full abstract
        effect_size, effect_direction = self._extract_effect_size(article.abstract)
        p_value = self._extract_p_value(article.abstract)
        ci = self._extract_ci(article.abstract)
        practical = self._determine_practical_significance(effect_size)
        direction = self._determine_direction(key_sentence, effect_direction)
        
        return KeyFinding(
            statement=key_sentence,
            direction=direction,
            effect_size=effect_size,
            p_value=p_value,
            confidence_interval=ci,
            practical_significance=practical
        )


# ============================================================================
# Contradiction Explainer (v2.5.0)
# ============================================================================

@dataclass
class StudyCharacteristics:
    """Extracted characteristics for contradiction analysis (v2.5.0)"""
    population: Optional[str] = None
    population_age: Optional[str] = None
    population_condition: Optional[str] = None
    sample_size: Optional[int] = None
    intervention_dose: Optional[str] = None
    intervention_duration: Optional[str] = None
    intervention_frequency: Optional[str] = None
    follow_up: Optional[str] = None
    outcome_measure: Optional[str] = None
    country: Optional[str] = None
    setting: Optional[str] = None


@dataclass
class ContradictionExplanation:
    """Explanation for why studies show conflicting results (v2.5.0)"""
    has_contradiction: bool
    summary: str
    supporting_count: int
    opposing_count: int
    factors: List[Dict[str, str]]  # [{"factor": "Population", "detail": "..."}]
    synthesis: str  # Synthesized conclusion considering the differences


class ContradictionExplainer:
    """
    Explain WHY studies show conflicting results (v2.5.0).
    
    Analyzes differences in:
    - Population characteristics (age, condition severity, baseline)
    - Intervention parameters (dose, frequency, duration)
    - Study design (follow-up, outcome measures)
    - Setting (country, clinical vs community)
    """
    
    # Age patterns
    AGE_PATTERNS = [
        (r"(?:elderly|older\s+adults?|aged?)\s*(?:[>≥]\s*)?(\d+)", "elderly"),
        (r"(\d+)\s*[-–to]+\s*(\d+)\s*years?", "range"),
        (r"(?:mean|average)\s+age\s*[=:of]*\s*(\d+(?:\.\d+)?)", "mean"),
        (r"(?:children|pediatric|adolescent)", "pediatric"),
        (r"(?:adult|middle-aged)", "adult"),
    ]
    
    # Dose patterns
    DOSE_PATTERNS = [
        r"(\d+(?:,\d+)?(?:\.\d+)?)\s*(?:mg|g|mcg|μg|IU|iu|ml|mL)(?:/(?:day|d|kg|dose))?",
        r"(?:low|high|moderate)\s*(?:-?\s*)?dose",
        r"(\d+(?:\.\d+)?)\s*(?:mg|g|IU)/(?:day|kg)",
    ]
    
    # Duration patterns  
    DURATION_PATTERNS = [
        r"(\d+)\s*(?:weeks?|wks?)",
        r"(\d+)\s*(?:months?|mos?)",
        r"(\d+)\s*(?:years?|yrs?)",
        r"(\d+)\s*(?:days?)",
    ]
    
    # Frequency patterns
    FREQUENCY_PATTERNS = [
        r"(?:once|twice|three times?|thrice)\s*(?:daily|weekly|monthly|per\s+(?:day|week|month))",
        r"(\d+)\s*(?:times?|x)\s*(?:per|/)\s*(?:day|week|month)",
        r"(?:daily|weekly|monthly|annually)",
        r"(?:every|each)\s+(?:day|week|month|other\s+day)",
    ]
    
    # Outcome measure patterns
    OUTCOME_PATTERNS = [
        r"(?:primary\s+)?(?:outcome|endpoint)\s*(?:was|:)\s*([^.]+)",
        r"(?:measured|assessed)\s+(?:by|using|with)\s+([^.]+)",
    ]
    
    # Setting patterns
    SETTING_PATTERNS = [
        r"(?:hospital|clinic|outpatient|inpatient|community|primary care|nursing home)",
    ]
    
    # Country patterns
    COUNTRY_PATTERNS = [
        r"(?:in|from)\s+((?:the\s+)?(?:United States|USA|UK|United Kingdom|China|Japan|Germany|France|Italy|Spain|Australia|Canada|India|Brazil|Korea|Netherlands|Sweden|Switzerland))",
    ]
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile patterns."""
        self.dose_regex = [re.compile(p, re.IGNORECASE) for p in self.DOSE_PATTERNS]
        self.duration_regex = [re.compile(p, re.IGNORECASE) for p in self.DURATION_PATTERNS]
        self.frequency_regex = [re.compile(p, re.IGNORECASE) for p in self.FREQUENCY_PATTERNS]
    
    def _extract_characteristics(self, article: ArticleInfo) -> StudyCharacteristics:
        """Extract study characteristics from abstract."""
        abstract = article.abstract
        chars = StudyCharacteristics()
        
        # Extract age
        for pattern, age_type in self.AGE_PATTERNS:
            match = re.search(pattern, abstract, re.IGNORECASE)
            if match:
                if age_type == "elderly":
                    chars.population_age = f"elderly (≥{match.group(1)} years)" if match.lastindex else "elderly"
                elif age_type == "range":
                    chars.population_age = f"{match.group(1)}-{match.group(2)} years"
                elif age_type == "mean":
                    chars.population_age = f"mean age {match.group(1)} years"
                elif age_type == "pediatric":
                    chars.population_age = "pediatric"
                elif age_type == "adult":
                    chars.population_age = "adults"
                break
        
        # Extract sample size
        sample_patterns = [r"n\s*=\s*(\d+)", r"(\d+)\s*(?:patients|participants|subjects)"]
        for pattern in sample_patterns:
            matches = re.findall(pattern, abstract, re.IGNORECASE)
            if matches:
                try:
                    chars.sample_size = max(int(m) for m in matches)
                except:
                    pass
                break
        
        # Extract dose
        for regex in self.dose_regex:
            match = regex.search(abstract)
            if match:
                chars.intervention_dose = match.group(0)
                break
        
        # Extract duration
        for regex in self.duration_regex:
            match = regex.search(abstract)
            if match:
                chars.intervention_duration = match.group(0)
                break
        
        # Extract frequency
        for regex in self.frequency_regex:
            match = regex.search(abstract)
            if match:
                chars.intervention_frequency = match.group(0)
                break
        
        # Extract setting
        for pattern in self.SETTING_PATTERNS:
            match = re.search(pattern, abstract, re.IGNORECASE)
            if match:
                chars.setting = match.group(0).lower()
                break
        
        # Extract country
        for pattern in self.COUNTRY_PATTERNS:
            match = re.search(pattern, abstract, re.IGNORECASE)
            if match:
                chars.country = match.group(1)
                break
        
        return chars
    
    def _compare_characteristics(
        self, 
        supporting: List[StudyCharacteristics],
        opposing: List[StudyCharacteristics]
    ) -> List[Dict[str, str]]:
        """Compare characteristics between supporting and opposing studies."""
        factors = []
        
        # Compare sample sizes
        sup_sizes = [s.sample_size for s in supporting if s.sample_size]
        opp_sizes = [s.sample_size for s in opposing if s.sample_size]
        if sup_sizes and opp_sizes:
            sup_avg = sum(sup_sizes) / len(sup_sizes)
            opp_avg = sum(opp_sizes) / len(opp_sizes)
            if abs(sup_avg - opp_avg) > 100:
                larger = "Supporting" if sup_avg > opp_avg else "Opposing"
                factors.append({
                    "factor": "Sample Size",
                    "detail": f"{larger} studies had larger samples (avg {int(max(sup_avg, opp_avg))} vs {int(min(sup_avg, opp_avg))})"
                })
        
        # Compare ages
        sup_ages = [s.population_age for s in supporting if s.population_age]
        opp_ages = [s.population_age for s in opposing if s.population_age]
        if sup_ages and opp_ages:
            sup_age_str = ", ".join(set(sup_ages))
            opp_age_str = ", ".join(set(opp_ages))
            if sup_age_str != opp_age_str:
                factors.append({
                    "factor": "Population Age",
                    "detail": f"Supporting studies: {sup_age_str}. Opposing studies: {opp_age_str}"
                })
        
        # Compare doses
        sup_doses = [s.intervention_dose for s in supporting if s.intervention_dose]
        opp_doses = [s.intervention_dose for s in opposing if s.intervention_dose]
        if sup_doses and opp_doses:
            sup_dose_str = ", ".join(set(sup_doses))
            opp_dose_str = ", ".join(set(opp_doses))
            if sup_dose_str != opp_dose_str:
                factors.append({
                    "factor": "Intervention Dose",
                    "detail": f"Supporting studies: {sup_dose_str}. Opposing studies: {opp_dose_str}"
                })
        
        # Compare durations
        sup_durations = [s.intervention_duration for s in supporting if s.intervention_duration]
        opp_durations = [s.intervention_duration for s in opposing if s.intervention_duration]
        if sup_durations and opp_durations:
            sup_dur_str = ", ".join(set(sup_durations))
            opp_dur_str = ", ".join(set(opp_durations))
            if sup_dur_str != opp_dur_str:
                factors.append({
                    "factor": "Study Duration",
                    "detail": f"Supporting studies: {sup_dur_str}. Opposing studies: {opp_dur_str}"
                })
        
        # Compare settings
        sup_settings = [s.setting for s in supporting if s.setting]
        opp_settings = [s.setting for s in opposing if s.setting]
        if sup_settings and opp_settings:
            sup_set_str = ", ".join(set(sup_settings))
            opp_set_str = ", ".join(set(opp_settings))
            if sup_set_str != opp_set_str:
                factors.append({
                    "factor": "Study Setting",
                    "detail": f"Supporting studies: {sup_set_str}. Opposing studies: {opp_set_str}"
                })
        
        return factors
    
    def _generate_synthesis(
        self,
        query: str,
        supporting_count: int,
        opposing_count: int,
        factors: List[Dict[str, str]]
    ) -> str:
        """Generate a synthesized conclusion."""
        if not factors:
            if supporting_count > opposing_count:
                return f"Most studies support this intervention, but some conflicting results exist. More research needed to understand the discrepancy."
            else:
                return f"Evidence is mixed. Consider individual patient factors when making decisions."
        
        # Build synthesis based on factors found
        factor_names = [f["factor"] for f in factors]
        
        synthesis_parts = []
        
        if "Population Age" in factor_names:
            synthesis_parts.append("effects may vary by age group")
        if "Intervention Dose" in factor_names:
            synthesis_parts.append("dose may be critical for effectiveness")
        if "Study Duration" in factor_names:
            synthesis_parts.append("longer treatment periods may be needed")
        if "Sample Size" in factor_names:
            synthesis_parts.append("larger studies may provide more reliable estimates")
        if "Study Setting" in factor_names:
            synthesis_parts.append("results may differ between clinical and community settings")
        
        if synthesis_parts:
            return f"The conflicting results suggest that {', '.join(synthesis_parts)}. Consider these factors when applying evidence to specific patients."
        else:
            return "Studies show conflicting results. Individual patient characteristics should guide clinical decisions."
    
    def explain(
        self,
        query: str,
        articles: List[ArticleInfo],
        stances: List[str]  # "support", "oppose", "neutral"
    ) -> ContradictionExplanation:
        """Analyze and explain contradictions between studies."""
        
        # Separate studies by stance
        supporting_articles = [a for a, s in zip(articles, stances) if s == "support"]
        opposing_articles = [a for a, s in zip(articles, stances) if s == "oppose"]
        
        supporting_count = len(supporting_articles)
        opposing_count = len(opposing_articles)
        
        # Check if there's a real contradiction
        total = supporting_count + opposing_count
        if total == 0 or opposing_count == 0 or supporting_count == 0:
            return ContradictionExplanation(
                has_contradiction=False,
                summary="No significant contradiction detected in the evidence",
                supporting_count=supporting_count,
                opposing_count=opposing_count,
                factors=[],
                synthesis="Studies are generally consistent in their findings."
            )
        
        # Extract characteristics from each group
        supporting_chars = [self._extract_characteristics(a) for a in supporting_articles]
        opposing_chars = [self._extract_characteristics(a) for a in opposing_articles]
        
        # Compare and find differences
        factors = self._compare_characteristics(supporting_chars, opposing_chars)
        
        # Generate synthesis
        synthesis = self._generate_synthesis(query, supporting_count, opposing_count, factors)
        
        # Build summary
        if factors:
            summary = f"Conflicting results found: {supporting_count} studies support, {opposing_count} oppose. Key differences identified in: {', '.join(f['factor'] for f in factors)}."
        else:
            summary = f"Conflicting results found: {supporting_count} studies support, {opposing_count} oppose. Unable to identify clear methodological differences."
        
        return ContradictionExplanation(
            has_contradiction=True,
            summary=summary,
            supporting_count=supporting_count,
            opposing_count=opposing_count,
            factors=factors,
            synthesis=synthesis
        )


class PubMedClient:
    """Async client for PubMed E-utilities API"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self._last_request_time = 0
        self._min_request_interval = 0.4  # 400ms between requests (NCBI recommends max 3/sec)
    
    async def _rate_limit(self):
        """Ensure we don't exceed rate limits"""
        import time
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    async def _request_with_retry(self, url: str, params: dict, max_retries: int = 3) -> httpx.Response:
        """Make request with retry logic for rate limiting"""
        for attempt in range(max_retries):
            await self._rate_limit()
            response = await self.client.get(url, params=params)
            
            if response.status_code == 429:
                # Rate limited - wait and retry
                wait_time = (attempt + 1) * 2  # Exponential backoff
                print(f"Rate limited, waiting {wait_time}s...", file=sys.stderr)
                await asyncio.sleep(wait_time)
                continue
            
            response.raise_for_status()
            return response
        
        # If all retries failed, raise the last error
        raise Exception("Max retries exceeded for PubMed API")
    
    async def search(self, query: str, max_results: int = 10) -> List[str]:
        """Search PubMed and return list of PMIDs"""
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance"
        }
        
        response = await self._request_with_retry(PUBMED_ESEARCH, params)
        data = response.json()
        
        return data.get("esearchresult", {}).get("idlist", [])
    
    async def fetch_article(self, pmid: str) -> Optional[ArticleInfo]:
        """Fetch detailed article information by PMID"""
        params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "xml",
            "rettype": "abstract"
        }
        
        response = await self._request_with_retry(PUBMED_EFETCH, params)
        
        return self._parse_article_xml(response.text, pmid)
    
    def _parse_article_xml(self, xml_text: str, pmid: str) -> Optional[ArticleInfo]:
        """Parse PubMed XML response into ArticleInfo"""
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(xml_text)
            article = root.find(".//PubmedArticle")
            if article is None:
                return None
            
            # Extract title
            title_elem = article.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None and title_elem.text else "No title"
            
            # Extract authors
            authors = []
            for author in article.findall(".//Author"):
                last_name = author.find("LastName")
                fore_name = author.find("ForeName")
                if last_name is not None and last_name.text:
                    name = last_name.text
                    if fore_name is not None and fore_name.text:
                        name = f"{fore_name.text} {name}"
                    authors.append(name)
            
            # Extract journal
            journal_elem = article.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None and journal_elem.text else "Unknown"
            
            # Extract publication date
            pub_date_elem = article.find(".//PubDate")
            pub_date = ""
            if pub_date_elem is not None:
                year = pub_date_elem.find("Year")
                month = pub_date_elem.find("Month")
                if year is not None and year.text:
                    pub_date = year.text
                    if month is not None and month.text:
                        pub_date = f"{month.text} {pub_date}"
            
            # Extract abstract
            abstract_parts = []
            for abstract_text in article.findall(".//AbstractText"):
                label = abstract_text.get("Label", "")
                text = abstract_text.text or ""
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            abstract = " ".join(abstract_parts) if abstract_parts else "No abstract available"
            
            # Extract DOI and PMC ID
            doi = None
            pmc_id = None
            for article_id in article.findall(".//ArticleId"):
                id_type = article_id.get("IdType")
                if id_type == "doi" and article_id.text:
                    doi = article_id.text
                elif id_type == "pmc" and article_id.text:
                    pmc_id = article_id.text
            
            # Extract publication types
            pub_types = []
            for pub_type in article.findall(".//PublicationType"):
                if pub_type.text:
                    pub_types.append(pub_type.text)
            
            # Extract MeSH terms
            mesh_terms = []
            for mesh in article.findall(".//MeshHeading/DescriptorName"):
                if mesh.text:
                    mesh_terms.append(mesh.text)
            
            return ArticleInfo(
                pmid=pmid,
                title=title,
                authors=authors[:5],
                journal=journal,
                pub_date=pub_date,
                abstract=abstract,
                doi=doi,
                pub_types=pub_types,
                mesh_terms=mesh_terms[:10],
                pmc_id=pmc_id
            )
        except ET.ParseError:
            return None
    
    async def close(self):
        await self.client.aclose()


def generate_full_text_links(article: ArticleInfo) -> FullTextLinks:
    """
    Generate full-text access links for an article (v2.4.0).
    
    Creates clickable URLs for:
    - PubMed page
    - DOI resolver (publisher page)
    - PMC full text (if available)
    - PMC PDF (if available)
    """
    pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{article.pmid}/"
    
    doi_url = None
    if article.doi:
        doi_url = f"https://doi.org/{article.doi}"
    
    pmc_url = None
    pmc_pdf_url = None
    open_access = False
    
    if article.pmc_id:
        # PMC articles are open access
        open_access = True
        pmc_id_clean = article.pmc_id.replace("PMC", "")
        pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id_clean}/"
        pmc_pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id_clean}/pdf/"
    
    return FullTextLinks(
        pubmed_url=pubmed_url,
        doi_url=doi_url,
        pmc_url=pmc_url,
        pmc_pdf_url=pmc_pdf_url,
        open_access=open_access
    )


class PICOExtractor:
    """
    Enhanced PICO extractor with 3-tier complexity detection.
    
    Level 1 (Casual): General public questions like "Is coffee bad for you?"
    Level 2 (Clinical): Healthcare professional questions like "Does yoga help anxiety?"
    Level 3 (Research): PhD-level questions with specific biomarkers, populations, outcomes
    """
    
    # ========== MEDICAL DOMAIN KEYWORDS ==========
    MEDICAL_DOMAINS = {
        "geriatric": [
            "elderly", "older adult", "aging", "geriatric", "senior", "frail",
            "aged", "nursing home", "dementia", "alzheimer", "fall prevention",
            "sarcopenia", "osteoporosis", "polypharmacy", "65+", "over 65"
        ],
        "orthopedics": [
            "bone", "joint", "fracture", "arthritis", "osteoarthritis", "spine",
            "back pain", "knee", "hip", "shoulder", "musculoskeletal", "orthopedic",
            "tendon", "ligament", "cartilage", "disc", "vertebra"
        ],
        "neurology": [
            "brain", "neural", "neurological", "stroke", "parkinson", "multiple sclerosis",
            "epilepsy", "seizure", "neuropathy", "cognitive", "dementia", "headache",
            "migraine", "tremor", "spinal cord", "nerve", "neuroinflammation"
        ],
        "rehabilitation": [
            "rehabilitation", "physiotherapy", "physical therapy", "occupational therapy",
            "exercise", "mobility", "walking", "gait", "balance", "strength",
            "functional", "recovery", "motor", "disability", "impairment"
        ],
        "cardiology": [
            "heart", "cardiac", "cardiovascular", "hypertension", "blood pressure",
            "arrhythmia", "coronary", "myocardial", "atrial", "ventricular",
            "cholesterol", "lipid", "atherosclerosis"
        ],
        "pulmonology": [
            "lung", "respiratory", "pulmonary", "copd", "asthma", "breathing",
            "oxygen", "ventilation", "bronchitis", "pneumonia", "dyspnea"
        ],
        "psychiatry": [
            "depression", "anxiety", "mental health", "psychiatric", "mood",
            "bipolar", "schizophrenia", "ptsd", "stress", "psychological",
            "antidepressant", "ssri", "psychotherapy"
        ],
        "oncology": [
            "cancer", "tumor", "oncology", "chemotherapy", "radiation",
            "carcinoma", "malignant", "metastasis", "neoplasm", "survival"
        ],
        "pediatrics": [
            "child", "pediatric", "infant", "neonatal", "adolescent", "youth",
            "developmental", "growth", "newborn", "toddler", "school-age"
        ],
        "endocrinology": [
            "diabetes", "thyroid", "hormone", "insulin", "metabolic", "glucose",
            "hba1c", "endocrine", "obesity", "weight", "bmi"
        ]
    }
    
    # ========== POPULATION PATTERNS ==========
    POPULATION_PATTERNS = {
        # Condition-based populations
        "conditions": {
            "copd": "Patients with chronic obstructive pulmonary disease (COPD)",
            "diabetes": "Patients with diabetes mellitus",
            "hypertension": "Patients with hypertension",
            "heart disease": "Patients with cardiovascular disease",
            "stroke": "Post-stroke patients",
            "depression": "Patients with major depressive disorder",
            "anxiety": "Patients with anxiety disorders",
            "back pain": "Patients with chronic low back pain",
            "arthritis": "Patients with arthritis",
            "osteoarthritis": "Patients with osteoarthritis",
            "cancer": "Cancer patients",
            "parkinson": "Patients with Parkinson's disease",
            "alzheimer": "Patients with Alzheimer's disease",
            "dementia": "Patients with dementia",
            "obesity": "Patients with obesity",
            "asthma": "Patients with asthma",
            "fibromyalgia": "Patients with fibromyalgia",
            "multiple sclerosis": "Patients with multiple sclerosis",
            "migraine": "Patients with migraine",
            "insomnia": "Patients with insomnia",
        },
        # Age-based populations
        "age_groups": {
            "elderly": "Older adults (≥65 years)",
            "older adult": "Older adults (≥65 years)",
            "geriatric": "Geriatric population (≥65 years)",
            "child": "Pediatric patients",
            "pediatric": "Pediatric patients",
            "infant": "Infants",
            "neonatal": "Neonates",
            "adolescent": "Adolescents",
            "adult": "Adults (18-64 years)",
            "young adult": "Young adults (18-35 years)",
        },
        # Gender-based
        "gender": {
            "women": "Female patients",
            "men": "Male patients",
            "pregnant": "Pregnant women",
            "postmenopausal": "Postmenopausal women",
        }
    }
    
    # ========== INTERVENTION PATTERNS ==========
    INTERVENTION_PATTERNS = {
        # Exercise interventions
        "exercise": {
            "exercise": "Exercise therapy",
            "walking": "Walking programs",
            "aerobic": "Aerobic exercise",
            "resistance training": "Resistance training",
            "strength training": "Strength training",
            "tai chi": "Tai Chi",
            "yoga": "Yoga intervention",
            "pilates": "Pilates",
            "aquatic": "Aquatic exercise",
            "cycling": "Cycling/stationary bike",
        },
        # Therapy interventions
        "therapy": {
            "physical therapy": "Physical therapy",
            "physiotherapy": "Physiotherapy",
            "occupational therapy": "Occupational therapy",
            "cognitive behavioral therapy": "Cognitive behavioral therapy (CBT)",
            "cbt": "Cognitive behavioral therapy (CBT)",
            "psychotherapy": "Psychotherapy",
            "speech therapy": "Speech therapy",
            "massage": "Massage therapy",
            "acupuncture": "Acupuncture",
            "chiropractic": "Chiropractic care",
        },
        # Pharmacological
        "pharmacological": {
            "ssri": "Selective serotonin reuptake inhibitors (SSRIs)",
            "antidepressant": "Antidepressant medications",
            "statin": "Statin therapy",
            "metformin": "Metformin",
            "insulin": "Insulin therapy",
            "ace inhibitor": "ACE inhibitors",
            "beta blocker": "Beta blockers",
            "nsaid": "NSAIDs",
            "opioid": "Opioid analgesics",
        },
        # Supplements
        "supplements": {
            "vitamin d": "Vitamin D supplementation",
            "vitamin": "Vitamin supplementation",
            "omega-3": "Omega-3 fatty acids",
            "fish oil": "Fish oil supplementation",
            "probiotic": "Probiotic supplementation",
            "calcium": "Calcium supplementation",
            "iron": "Iron supplementation",
            "magnesium": "Magnesium supplementation",
        },
        # Other interventions
        "other": {
            "meditation": "Meditation/mindfulness",
            "mindfulness": "Mindfulness-based intervention",
            "breathing": "Breathing exercises",
            "diet": "Dietary intervention",
            "education": "Patient education",
            "telehealth": "Telehealth/telemedicine",
            "surgery": "Surgical intervention",
        }
    }
    
    # ========== OUTCOME PATTERNS ==========
    OUTCOME_PATTERNS = {
        # Functional outcomes
        "functional": {
            "walking": "Walking ability/6-minute walk test",
            "mobility": "Functional mobility",
            "gait": "Gait parameters",
            "balance": "Balance (Berg Balance Scale)",
            "strength": "Muscle strength",
            "function": "Functional capacity",
            "adl": "Activities of daily living (ADL)",
            "independence": "Functional independence",
        },
        # Symptom outcomes
        "symptoms": {
            "pain": "Pain intensity (VAS/NRS)",
            "fatigue": "Fatigue levels",
            "dyspnea": "Dyspnea/breathlessness",
            "sleep": "Sleep quality",
            "symptom": "Symptom severity",
        },
        # Mental health outcomes
        "mental_health": {
            "depression": "Depression symptoms (PHQ-9, BDI)",
            "anxiety": "Anxiety symptoms (GAD-7, STAI)",
            "quality of life": "Health-related quality of life",
            "well-being": "Psychological well-being",
            "stress": "Perceived stress",
            "cognitive": "Cognitive function",
        },
        # Clinical outcomes
        "clinical": {
            "mortality": "All-cause mortality",
            "survival": "Survival rate",
            "hospitalization": "Hospital readmission",
            "exacerbation": "Disease exacerbation",
            "blood pressure": "Blood pressure control",
            "hba1c": "Glycemic control (HbA1c)",
            "bmi": "Body mass index",
            "weight": "Weight change",
        },
        # Research-level outcomes
        "biomarkers": {
            "inflammatory": "Inflammatory markers (CRP, IL-6)",
            "crp": "C-reactive protein",
            "cytokine": "Cytokine levels",
            "cortisol": "Cortisol levels",
            "biomarker": "Biomarker changes",
        }
    }
    
    # ========== COMMON PICO PATTERNS ==========
    # Known query patterns with pre-defined optimal PICO
    COMMON_PATTERNS = {
        # Yoga + anxiety is a common search
        ("yoga", "anxiety"): {
            "population": "Adults with anxiety disorders",
            "intervention": "Yoga practice (various styles)",
            "comparison": "Waitlist control, usual care, or active comparator",
            "outcomes": ["Anxiety symptoms (GAD-7, STAI, HADS-A)", "Depression symptoms", "Quality of life", "Stress levels"],
            "search_terms": ["yoga", "anxiety", "randomized controlled trial"]
        },
        ("exercise", "copd"): {
            "population": "Patients with COPD (GOLD stages I-IV)",
            "intervention": "Exercise training (aerobic, resistance, or combined)",
            "comparison": "Usual care or no exercise",
            "outcomes": ["6-minute walk distance", "Dyspnea (mMRC, Borg)", "Quality of life (SGRQ, CAT)", "Exercise capacity"],
            "search_terms": ["exercise", "COPD", "pulmonary rehabilitation"]
        },
        ("walking", "copd"): {
            "population": "Patients with COPD",
            "intervention": "Walking-based exercise programs",
            "comparison": "Standard care or sedentary control",
            "outcomes": ["6-minute walk test", "Functional capacity", "Dyspnea", "Quality of life"],
            "search_terms": ["walking", "COPD", "exercise", "pulmonary rehabilitation"]
        },
        ("vitamin d", "elderly"): {
            "population": "Older adults (≥65 years)",
            "intervention": "Vitamin D supplementation",
            "comparison": "Placebo or no supplementation",
            "outcomes": ["Bone mineral density", "Fall risk", "Fracture incidence", "Muscle strength"],
            "search_terms": ["vitamin D", "elderly", "supplementation", "bone health"]
        },
        ("meditation", "stress"): {
            "population": "Adults with elevated stress levels",
            "intervention": "Meditation or mindfulness-based interventions",
            "comparison": "Waitlist, attention control, or active comparator",
            "outcomes": ["Perceived stress (PSS)", "Anxiety", "Cortisol levels", "Quality of life"],
            "search_terms": ["meditation", "mindfulness", "stress", "randomized"]
        },
        ("physical therapy", "back pain"): {
            "population": "Adults with chronic low back pain",
            "intervention": "Physical therapy/physiotherapy",
            "comparison": "Usual care, medication, or other interventions",
            "outcomes": ["Pain intensity (VAS/NRS)", "Disability (ODI, RMDQ)", "Function", "Return to work"],
            "search_terms": ["physical therapy", "low back pain", "chronic", "randomized"]
        }
    }
    
    # ========== COMPLEXITY INDICATORS ==========
    RESEARCH_INDICATORS = [
        # Biomarker terms
        "biomarker", "cytokine", "interleukin", "inflammatory marker", "crp",
        "hpa-axis", "cortisol", "epigenetic", "methylation", "transcriptomic",
        "proteomic", "metabolomic", "microbiome", "gut-brain", "neuroinflammation",
        # Research methodology terms
        "randomized controlled", "systematic review", "meta-analysis", "cohort",
        "prospective", "longitudinal", "dose-response", "mechanism", "pathway",
        # Specific clinical terms
        "treatment-resistant", "refractory", "phenotype", "genotype", "polymorphism",
        "pharmacogenomic", "precision medicine", "targeted therapy"
    ]
    
    CLINICAL_INDICATORS = [
        # Professional terms
        "patient", "treatment", "therapy", "clinical", "diagnosis", "prognosis",
        "guideline", "protocol", "efficacy", "effectiveness", "safety",
        # Specific conditions
        "chronic", "acute", "moderate", "severe", "mild", "stage",
        # Outcome measures
        "mortality", "morbidity", "hospitalization", "readmission"
    ]
    
    def __init__(self):
        """Initialize the PICO extractor"""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency"""
        # Patterns for extracting specific phrases
        self.population_regex = re.compile(
            r"(?:in|for|among|with)\s+([^,?.]+?)(?:\s+(?:does|do|is|are|can|could|should|what|how)|\s*[,?.]|$)",
            re.IGNORECASE
        )
        self.intervention_regex = re.compile(
            r"(?:does|do|is|are|can|could|effect of|effects of|impact of)\s+([^,?.]+?)(?:\s+(?:help|improve|reduce|prevent|treat|on|for|in)|\s*[,?.]|$)",
            re.IGNORECASE
        )
        self.outcome_regex = re.compile(
            r"(?:improve|reduce|prevent|treat|help with|effect on|impact on)\s+([^,?.]+?)(?:\s+(?:in|for|among)|\s*[,?.]|$)",
            re.IGNORECASE
        )
    
    def detect_complexity(self, query: str) -> Tuple[int, str]:
        """
        Detect the complexity level of the query.
        
        Returns:
            Tuple of (level, label) where:
            - Level 1: Casual (general public)
            - Level 2: Clinical (healthcare professionals/students)
            - Level 3: Research (PhD-level researchers)
        """
        query_lower = query.lower()
        
        # Count research indicators
        research_count = sum(1 for ind in self.RESEARCH_INDICATORS if ind in query_lower)
        clinical_count = sum(1 for ind in self.CLINICAL_INDICATORS if ind in query_lower)
        
        # Check for research-level complexity
        if research_count >= 2 or any(term in query_lower for term in 
            ["mechanism", "pathway", "biomarker", "epigenetic", "microbiome", "transcriptomic"]):
            return (3, "Research")
        
        # Check for clinical-level complexity
        if clinical_count >= 2 or any(term in query_lower for term in 
            ["patient", "treatment", "therapy", "clinical"]):
            return (2, "Clinical")
        
        # Check for medical conditions - these make a query clinical even with casual phrasing
        clinical_conditions = [
            "anxiety", "depression", "diabetes", "hypertension", "copd", "asthma",
            "arthritis", "cancer", "stroke", "dementia", "parkinson", "alzheimer",
            "heart disease", "obesity", "fibromyalgia", "migraine", "insomnia",
            "chronic pain", "back pain", "osteoporosis", "multiple sclerosis"
        ]
        if any(condition in query_lower for condition in clinical_conditions):
            return (2, "Clinical")
        
        # Check for clinical interventions
        clinical_interventions = [
            "yoga", "exercise", "meditation", "physical therapy", "physiotherapy",
            "acupuncture", "massage therapy", "cognitive behavioral", "vitamin",
            "supplement", "medication", "drug", "surgery"
        ]
        if any(intervention in query_lower for intervention in clinical_interventions):
            # If combined with a health-related question, it's clinical
            if any(term in query_lower for term in ["help", "improve", "reduce", "treat", "prevent"]):
                return (2, "Clinical")
        
        # Check query structure - simple questions WITHOUT medical terms are casual
        casual_patterns = [
            r"^is\s+\w+\s+(good|bad|safe|healthy)",
            r"^what\s+(helps|is\s+good|works)\s+",
            r"^does\s+\w+\s+(help|work)",
            r"^can\s+\w+\s+help",
            r"^should\s+i\s+",
        ]
        for pattern in casual_patterns:
            if re.search(pattern, query_lower):
                return (1, "Casual")
        
        # Default to clinical if unclear but has some medical terms
        if any(domain_terms for domain_terms in self.MEDICAL_DOMAINS.values() 
               if any(term in query_lower for term in domain_terms)):
            return (2, "Clinical")
        
        return (1, "Casual")
    
    def detect_domain(self, query: str) -> str:
        """Detect the primary medical domain of the query"""
        query_lower = query.lower()
        domain_scores = {}
        
        for domain, keywords in self.MEDICAL_DOMAINS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            return max(domain_scores, key=lambda d: domain_scores[d])
        return "general"
    
    def _find_common_pattern(self, query: str) -> Optional[Dict[str, Any]]:
        """Check if query matches a known common pattern"""
        query_lower = query.lower()
        
        for (key1, key2), pattern_data in self.COMMON_PATTERNS.items():
            if key1 in query_lower and key2 in query_lower:
                return pattern_data
        return None
    
    def _extract_population(self, query: str, complexity: int) -> str:
        """Extract population from query based on complexity level"""
        query_lower = query.lower()
        
        # First check condition-based populations
        for condition, population in self.POPULATION_PATTERNS["conditions"].items():
            if condition in query_lower:
                return population
        
        # Check age groups
        for age_term, population in self.POPULATION_PATTERNS["age_groups"].items():
            if age_term in query_lower:
                return population
        
        # Check gender
        for gender_term, population in self.POPULATION_PATTERNS["gender"].items():
            if gender_term in query_lower:
                return population
        
        # Try regex extraction
        match = self.population_regex.search(query)
        if match:
            extracted = match.group(1).strip()
            # Clean up common words
            extracted = re.sub(r"^(the|a|an)\s+", "", extracted)
            if len(extracted) > 5 and len(extracted) < 100:
                return f"Patients/individuals with {extracted}"
        
        # Default based on complexity
        if complexity == 1:
            return "General population"
        elif complexity == 2:
            return "Adult patients"
        else:
            return "Target population (specify patient characteristics)"
    
    def _extract_intervention(self, query: str, complexity: int) -> str:
        """Extract intervention from query"""
        query_lower = query.lower()
        
        # Check all intervention categories
        for category, interventions in self.INTERVENTION_PATTERNS.items():
            for keyword, intervention in interventions.items():
                if keyword in query_lower:
                    return intervention
        
        # Try regex extraction
        match = self.intervention_regex.search(query)
        if match:
            extracted = match.group(1).strip()
            if len(extracted) > 3 and len(extracted) < 80:
                return extracted.title()
        
        # Default based on complexity
        if complexity == 1:
            return "Intervention of interest"
        elif complexity == 2:
            return "Treatment/therapy intervention"
        else:
            return "Specific intervention (define parameters, dosage, duration)"
    
    def _extract_comparison(self, query: str) -> str:
        """Extract comparison from query"""
        query_lower = query.lower()
        
        comparison_patterns = [
            (r"compared to\s+([^,?.]+)", r"\1"),
            (r"versus\s+([^,?.]+)", r"\1"),
            (r"vs\.?\s+([^,?.]+)", r"\1"),
            (r"or\s+([^,?.]+?)(?:\s+for|\s+in|\s*[,?.])", r"\1"),
        ]
        
        for pattern, _ in comparison_patterns:
            match = re.search(pattern, query_lower)
            if match:
                comparison = match.group(1).strip()
                if len(comparison) > 2 and len(comparison) < 50:
                    return comparison.title()
        
        # Check for implicit comparisons
        if "placebo" in query_lower:
            return "Placebo"
        if "control" in query_lower:
            return "Control group"
        if "standard care" in query_lower or "usual care" in query_lower:
            return "Standard/usual care"
        
        return "Standard care, placebo, or no intervention"
    
    def _extract_outcome(self, query: str, complexity: int, domain: str) -> str:
        """Extract outcome from query based on complexity and domain"""
        query_lower = query.lower()
        
        # Check all outcome categories
        for category, outcomes in self.OUTCOME_PATTERNS.items():
            for keyword, outcome in outcomes.items():
                if keyword in query_lower:
                    return outcome
        
        # Try regex extraction
        match = self.outcome_regex.search(query)
        if match:
            extracted = match.group(1).strip()
            if len(extracted) > 3 and len(extracted) < 80:
                return extracted.title()
        
        # Domain-specific default outcomes
        domain_outcomes = {
            "geriatric": "Functional status, falls, quality of life",
            "orthopedics": "Pain, function, range of motion",
            "neurology": "Cognitive function, motor function, symptom severity",
            "rehabilitation": "Functional capacity, mobility, independence",
            "cardiology": "Cardiovascular events, blood pressure, exercise capacity",
            "pulmonology": "Respiratory function, dyspnea, exercise tolerance",
            "psychiatry": "Symptom severity, quality of life, functioning",
            "oncology": "Survival, tumor response, quality of life",
            "pediatrics": "Growth, development, symptom control",
            "endocrinology": "Metabolic control, weight, complications",
        }
        
        if domain in domain_outcomes:
            return domain_outcomes[domain]
        
        # Default based on complexity
        if complexity == 1:
            return "Health improvement"
        elif complexity == 2:
            return "Clinical outcomes and symptom improvement"
        else:
            return "Primary and secondary endpoints (specify measures)"
    
    def _generate_suggestions(self, query: str, complexity: int, 
                             population: str, intervention: str, 
                             comparison: str, outcome: str) -> List[str]:
        """Generate suggestions to improve the PICO query"""
        suggestions = []
        query_lower = query.lower()
        
        # Population suggestions
        if "general population" in population.lower() or "adult" in population.lower():
            suggestions.append("Specify the population: age range, condition severity, comorbidities")
        
        # Intervention suggestions
        if "intervention" in intervention.lower():
            suggestions.append("Specify the intervention: type, dosage, frequency, duration")
        
        # Comparison suggestions
        if "standard care" in comparison.lower() and "vs" not in query_lower and "versus" not in query_lower:
            suggestions.append("Consider adding a comparison group: placebo, usual care, or alternative treatment")
        
        # Outcome suggestions
        if complexity >= 2 and "clinical outcomes" in outcome.lower():
            suggestions.append("Specify measurable outcomes: validated scales, biomarkers, time points")
        
        # Domain-specific suggestions
        if "copd" in query_lower and "6-minute walk" not in query_lower:
            suggestions.append("Consider including 6-minute walk test as an outcome measure")
        if "anxiety" in query_lower and ("gad" not in query_lower and "stai" not in query_lower):
            suggestions.append("Consider validated anxiety measures: GAD-7, STAI, HADS-A")
        if "depression" in query_lower and ("phq" not in query_lower and "bdi" not in query_lower):
            suggestions.append("Consider validated depression measures: PHQ-9, BDI, HADS-D")
        
        return suggestions[:4]  # Limit to 4 suggestions
    
    def _generate_search_terms(self, population: str, intervention: str, 
                               outcome: str, domain: str) -> List[str]:
        """Generate optimized PubMed search terms"""
        terms = []
        
        # Extract key words from each component
        def extract_key_words(text: str) -> List[str]:
            # Remove common words
            stopwords = {"patients", "with", "the", "a", "an", "of", "in", "for", "and", "or"}
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
            return [w for w in words if w not in stopwords][:3]
        
        terms.extend(extract_key_words(population))
        terms.extend(extract_key_words(intervention))
        terms.extend(extract_key_words(outcome))
        
        # Add study design terms for better results
        terms.append("randomized controlled trial OR systematic review")
        
        return list(dict.fromkeys(terms))  # Remove duplicates while preserving order
    
    def _calculate_confidence(self, population: str, intervention: str, 
                             outcome: str, common_pattern: bool) -> int:
        """Calculate confidence score for the extraction"""
        score = 50  # Base score
        
        if common_pattern:
            score += 30
        
        # Higher confidence if specific terms found
        if "general" not in population.lower():
            score += 10
        if "intervention of interest" not in intervention.lower():
            score += 10
        if "clinical outcomes" not in outcome.lower():
            score += 10
        
        return min(100, score)
    
    def extract(self, query: str) -> PICOAnalysis:
        """
        Extract PICO components from a clinical question.
        Returns basic PICOAnalysis for backward compatibility.
        Use extract_enhanced() for full features.
        """
        enhanced = self.extract_enhanced(query)
        return PICOAnalysis(
            population=enhanced.population,
            intervention=enhanced.intervention,
            comparison=enhanced.comparison,
            outcome=enhanced.outcome,
            clinical_question=enhanced.clinical_question
        )
    
    def extract_enhanced(self, query: str) -> EnhancedPICOAnalysis:
        """
        Extract PICO components with full enhanced features.
        
        Returns EnhancedPICOAnalysis with:
        - Complexity level detection
        - Domain identification
        - Improvement suggestions
        - Confidence score
        - Optimized search terms
        """
        # Detect complexity and domain
        complexity_level, complexity_label = self.detect_complexity(query)
        domain = self.detect_domain(query)
        
        # Check for common patterns first
        common_pattern = self._find_common_pattern(query)
        
        if common_pattern:
            # Use pre-defined pattern
            population = common_pattern["population"]
            intervention = common_pattern["intervention"]
            comparison = common_pattern["comparison"]
            outcome = common_pattern["outcomes"][0] if common_pattern["outcomes"] else "Clinical outcomes"
            search_terms = common_pattern["search_terms"]
        else:
            # Extract components
            population = self._extract_population(query, complexity_level)
            intervention = self._extract_intervention(query, complexity_level)
            comparison = self._extract_comparison(query)
            outcome = self._extract_outcome(query, complexity_level, domain)
            search_terms = self._generate_search_terms(population, intervention, outcome, domain)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(
            query, complexity_level, population, intervention, comparison, outcome
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            population, intervention, outcome, common_pattern is not None
        )
        
        # Generate clinical question
        clinical_question = self._generate_clinical_question(
            population, intervention, comparison, outcome
        )
        
        return EnhancedPICOAnalysis(
            population=population,
            intervention=intervention,
            comparison=comparison,
            outcome=outcome,
            clinical_question=clinical_question,
            complexity_level=complexity_level,
            complexity_label=complexity_label,
            domain=domain.title() if domain != "general" else "General Medicine",
            suggestions=suggestions,
            confidence_score=confidence,
            search_terms=search_terms
        )
    
    def _generate_clinical_question(
        self, population: str, intervention: str, 
        comparison: str, outcome: str
    ) -> str:
        """Generate a well-formed clinical question"""
        # Clean up components
        pop = population.lower() if population else "adults"
        interv = intervention.lower() if intervention else "the intervention"
        comp = comparison.lower() if comparison else "standard care"
        out = outcome.lower() if outcome else "clinical outcomes"
        
        return f"In {pop}, does {interv} compared to {comp} improve {out}?"


class TrustAnalyzer:
    """Analyze article trustworthiness and evidence quality"""
    
    HIGH_IMPACT_JOURNALS = [
        "lancet", "nejm", "new england", "jama", "bmj", "nature", "science",
        "annals of internal medicine", "cochrane", "plos medicine"
    ]
    
    MEDIUM_IMPACT_JOURNALS = [
        "journal of", "american journal", "british journal", "european journal",
        "international journal", "clinical", "archives of"
    ]
    
    def analyze(self, article: ArticleInfo) -> TrustScore:
        study_design = self._classify_study_design(article)
        methodology_score = self._calculate_methodology_score(article, study_design)
        sample_size_score = self._estimate_sample_size_score(article.abstract)
        recency_score = self._calculate_recency_score(article.pub_date)
        journal_score = self._calculate_journal_score(article.journal)
        
        base_score = STUDY_DESIGN_SCORES.get(study_design, 30)
        overall_score = int(
            base_score * 0.35 +
            methodology_score * 0.25 +
            sample_size_score * 0.15 +
            recency_score * 0.10 +
            journal_score * 0.15
        )
        overall_score = min(100, max(0, overall_score))
        
        evidence_grade = "D"
        for (low, high), grade in EVIDENCE_GRADES.items():
            if low <= overall_score <= high:
                evidence_grade = grade
                break
        
        strengths, limitations = self._identify_strengths_limitations(
            article, study_design, overall_score
        )
        
        return TrustScore(
            overall_score=overall_score,
            evidence_grade=evidence_grade,
            study_design=study_design.replace("_", " ").title(),
            methodology_score=methodology_score,
            sample_size_score=sample_size_score,
            recency_score=recency_score,
            journal_score=journal_score,
            strengths=strengths,
            limitations=limitations
        )
    
    def _classify_study_design(self, article: ArticleInfo) -> str:
        text = " ".join([
            article.title.lower(),
            article.abstract.lower(),
            " ".join(article.pub_types).lower()
        ])
        
        for design, patterns in STUDY_DESIGN_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return design
        return "unknown"
    
    def _calculate_methodology_score(self, article: ArticleInfo, study_design: str) -> int:
        abstract_lower = article.abstract.lower()
        score = 50
        
        positive_indicators = [
            ("blind", 10), ("randomiz", 10), ("placebo", 8),
            ("control group", 8), ("statistical", 5), ("p-value", 5),
            ("confidence interval", 5), ("intention to treat", 8),
            ("power analysis", 5), ("validated", 5), ("standardized", 5)
        ]
        
        for indicator, points in positive_indicators:
            if indicator in abstract_lower:
                score += points
        
        if study_design == "systematic_review":
            score += 15
        elif study_design == "rct":
            score += 10
        
        return min(100, score)
    
    def _estimate_sample_size_score(self, abstract: str) -> int:
        patterns = [
            r"n\s*=\s*(\d+)",
            r"(\d+)\s*patients",
            r"(\d+)\s*participants",
            r"(\d+)\s*subjects",
            r"sample size.*?(\d+)"
        ]
        
        max_n = 0
        for pattern in patterns:
            matches = re.findall(pattern, abstract.lower())
            for match in matches:
                try:
                    n = int(match)
                    max_n = max(max_n, n)
                except ValueError:
                    continue
        
        if max_n >= 1000:
            return 95
        elif max_n >= 500:
            return 85
        elif max_n >= 200:
            return 75
        elif max_n >= 100:
            return 65
        elif max_n >= 50:
            return 55
        elif max_n > 0:
            return 45
        else:
            return 50
    
    def _calculate_recency_score(self, pub_date: str) -> int:
        try:
            year_match = re.search(r"(\d{4})", pub_date)
            if year_match:
                year = int(year_match.group(1))
                current_year = datetime.now().year
                age = current_year - year
                
                if age <= 2:
                    return 100
                elif age <= 5:
                    return 85
                elif age <= 10:
                    return 70
                elif age <= 15:
                    return 55
                else:
                    return 40
        except:
            pass
        return 50
    
    def _calculate_journal_score(self, journal: str) -> int:
        journal_lower = journal.lower()
        
        for high_impact in self.HIGH_IMPACT_JOURNALS:
            if high_impact in journal_lower:
                return 95
        
        for medium_impact in self.MEDIUM_IMPACT_JOURNALS:
            if medium_impact in journal_lower:
                return 70
        
        return 50
    
    def _identify_strengths_limitations(
        self, article: ArticleInfo, study_design: str, score: int
    ) -> Tuple[List[str], List[str]]:
        strengths = []
        limitations = []
        abstract_lower = article.abstract.lower()
        
        if study_design == "systematic_review":
            strengths.append("Systematic review provides highest level of evidence")
        elif study_design == "rct":
            strengths.append("Randomized controlled trial design reduces bias")
        elif study_design in ["cohort", "case_control"]:
            limitations.append("Observational design limits causal inference")
        
        if "double-blind" in abstract_lower:
            strengths.append("Double-blinding reduces observer bias")
        if "placebo" in abstract_lower:
            strengths.append("Placebo-controlled design")
        if "intention to treat" in abstract_lower:
            strengths.append("Intention-to-treat analysis preserves randomization")
        
        if "small sample" in abstract_lower or "limited sample" in abstract_lower:
            limitations.append("Small sample size may limit generalizability")
        if "single center" in abstract_lower or "single-center" in abstract_lower:
            limitations.append("Single-center study may limit external validity")
        if "retrospective" in abstract_lower:
            limitations.append("Retrospective design prone to recall bias")
        
        if not limitations:
            limitations.append("Individual study - consider in context of broader evidence")
        
        return strengths[:4], limitations[:4]


# ============================================================================
# Citation Export (v2.3.0)
# ============================================================================

class CitationExporter:
    """
    Export PubMed articles to standard citation formats.
    
    Supports:
    - BibTeX (.bib) - For LaTeX documents
    - RIS (.ris) - Universal format for Zotero, Mendeley, EndNote
    - EndNote Tagged (.enw) - For EndNote desktop
    """
    
    SUPPORTED_FORMATS = ["bibtex", "ris", "endnote"]
    
    def __init__(self):
        # Month name to number mapping
        self.month_map = {
            "jan": "01", "january": "01",
            "feb": "02", "february": "02",
            "mar": "03", "march": "03",
            "apr": "04", "april": "04",
            "may": "05",
            "jun": "06", "june": "06",
            "jul": "07", "july": "07",
            "aug": "08", "august": "08",
            "sep": "09", "september": "09",
            "oct": "10", "october": "10",
            "nov": "11", "november": "11",
            "dec": "12", "december": "12"
        }
    
    def _parse_pub_date(self, pub_date: str) -> Tuple[str, str]:
        """Parse publication date into (year, month) tuple."""
        year = ""
        month = ""
        
        # Extract year
        year_match = re.search(r"(\d{4})", pub_date)
        if year_match:
            year = year_match.group(1)
        
        # Extract month
        for month_name, month_num in self.month_map.items():
            if month_name in pub_date.lower():
                month = month_num
                break
        
        return year, month
    
    def _escape_bibtex(self, text: str) -> str:
        """Escape special BibTeX characters."""
        if not text:
            return ""
        # Replace special characters
        replacements = [
            ("&", r"\&"),
            ("%", r"\%"),
            ("$", r"\$"),
            ("#", r"\#"),
            ("_", r"\_"),
            ("{", r"\{"),
            ("}", r"\}"),
            ("~", r"\textasciitilde{}"),
            ("^", r"\textasciicircum{}"),
        ]
        result = text
        for old, new in replacements:
            result = result.replace(old, new)
        return result
    
    def _format_bibtex_author(self, authors: List[str]) -> str:
        """Format author list for BibTeX (Last, First and Last, First)."""
        if not authors:
            return ""
        
        formatted = []
        for author in authors:
            # Split "First Last" into "Last, First"
            parts = author.strip().split()
            if len(parts) >= 2:
                formatted.append(f"{parts[-1]}, {' '.join(parts[:-1])}")
            else:
                formatted.append(author)
        
        return " and ".join(formatted)
    
    def to_bibtex(self, article: ArticleInfo) -> str:
        """
        Convert article to BibTeX format.
        
        Example output:
        @article{pmid12345678,
          author = {Smith, John and Doe, Jane},
          title = {Title of the Article},
          journal = {Journal Name},
          year = {2024},
          month = {jan},
          pmid = {12345678},
          doi = {10.1000/example}
        }
        """
        year, month = self._parse_pub_date(article.pub_date)
        
        lines = [f"@article{{pmid{article.pmid},"]
        
        # Author
        if article.authors:
            author_str = self._format_bibtex_author(article.authors)
            lines.append(f"  author = {{{self._escape_bibtex(author_str)}}},")
        
        # Title
        lines.append(f"  title = {{{self._escape_bibtex(article.title)}}},")
        
        # Journal
        lines.append(f"  journal = {{{self._escape_bibtex(article.journal)}}},")
        
        # Year
        if year:
            lines.append(f"  year = {{{year}}},")
        
        # Month (use abbreviated form)
        if month:
            month_abbr = {
                "01": "jan", "02": "feb", "03": "mar", "04": "apr",
                "05": "may", "06": "jun", "07": "jul", "08": "aug",
                "09": "sep", "10": "oct", "11": "nov", "12": "dec"
            }
            lines.append(f"  month = {{{month_abbr.get(month, '')}}},")
        
        # PMID
        lines.append(f"  pmid = {{{article.pmid}}},")
        
        # DOI
        if article.doi:
            lines.append(f"  doi = {{{article.doi}}},")
        
        # URL
        lines.append(f"  url = {{https://pubmed.ncbi.nlm.nih.gov/{article.pmid}/}}")
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def to_ris(self, article: ArticleInfo) -> str:
        """
        Convert article to RIS format.
        
        RIS is widely supported by Zotero, Mendeley, EndNote, etc.
        
        Example output:
        TY  - JOUR
        AU  - Smith, John
        AU  - Doe, Jane
        TI  - Title of the Article
        JO  - Journal Name
        PY  - 2024
        AN  - 12345678
        DO  - 10.1000/example
        UR  - https://pubmed.ncbi.nlm.nih.gov/12345678/
        ER  - 
        """
        year, month = self._parse_pub_date(article.pub_date)
        
        lines = ["TY  - JOUR"]
        
        # Authors (one per line)
        for author in article.authors:
            lines.append(f"AU  - {author}")
        
        # Title
        lines.append(f"TI  - {article.title}")
        
        # Journal
        lines.append(f"JO  - {article.journal}")
        
        # Publication date
        if year:
            date_str = year
            if month:
                date_str = f"{year}/{month}"
            lines.append(f"PY  - {date_str}")
        
        # Database accession number (PMID)
        lines.append(f"AN  - {article.pmid}")
        
        # DOI
        if article.doi:
            lines.append(f"DO  - {article.doi}")
        
        # URL
        lines.append(f"UR  - https://pubmed.ncbi.nlm.nih.gov/{article.pmid}/")
        
        # Abstract (optional, can be long)
        if article.abstract and article.abstract != "No abstract available":
            # RIS allows multi-line abstracts with AB tag
            lines.append(f"AB  - {article.abstract}")
        
        # Keywords (MeSH terms)
        for term in article.mesh_terms[:10]:
            lines.append(f"KW  - {term}")
        
        # End of record
        lines.append("ER  - ")
        
        return "\n".join(lines)
    
    def to_endnote(self, article: ArticleInfo) -> str:
        """
        Convert article to EndNote Tagged format (.enw).
        
        Example output:
        %0 Journal Article
        %A Smith, John
        %A Doe, Jane
        %T Title of the Article
        %J Journal Name
        %D 2024
        %M 12345678
        %R 10.1000/example
        %U https://pubmed.ncbi.nlm.nih.gov/12345678/
        """
        year, _ = self._parse_pub_date(article.pub_date)
        
        lines = ["%0 Journal Article"]
        
        # Authors (one per line)
        for author in article.authors:
            lines.append(f"%A {author}")
        
        # Title
        lines.append(f"%T {article.title}")
        
        # Journal
        lines.append(f"%J {article.journal}")
        
        # Year
        if year:
            lines.append(f"%D {year}")
        
        # Accession Number (PMID)
        lines.append(f"%M {article.pmid}")
        
        # DOI
        if article.doi:
            lines.append(f"%R {article.doi}")
        
        # URL
        lines.append(f"%U https://pubmed.ncbi.nlm.nih.gov/{article.pmid}/")
        
        # Abstract
        if article.abstract and article.abstract != "No abstract available":
            lines.append(f"%X {article.abstract}")
        
        # Keywords (MeSH terms)
        for term in article.mesh_terms[:10]:
            lines.append(f"%K {term}")
        
        # End with blank line
        lines.append("")
        
        return "\n".join(lines)
    
    def export(self, article: ArticleInfo, format: str) -> str:
        """Export a single article to the specified format."""
        format_lower = format.lower().strip()
        
        if format_lower == "bibtex" or format_lower == "bib":
            return self.to_bibtex(article)
        elif format_lower == "ris":
            return self.to_ris(article)
        elif format_lower == "endnote" or format_lower == "enw":
            return self.to_endnote(article)
        else:
            raise ValueError(f"Unsupported format: {format}. Supported: {self.SUPPORTED_FORMATS}")
    
    def export_multiple(self, articles: List[ArticleInfo], format: str) -> str:
        """Export multiple articles to the specified format."""
        format_lower = format.lower().strip()
        
        if not articles:
            return ""
        
        exports = []
        for article in articles:
            exports.append(self.export(article, format_lower))
        
        # Different formats have different separators
        if format_lower == "bibtex" or format_lower == "bib":
            return "\n\n".join(exports)
        elif format_lower == "ris":
            return "\n".join(exports)
        elif format_lower == "endnote" or format_lower == "enw":
            return "\n".join(exports)
        else:
            return "\n\n".join(exports)


@dataclass
class RecencyTrendResult:
    """Result from recency and trend analysis"""
    trend_direction: str  # "strengthening", "weakening", "stable", "insufficient_data"
    trend_description: str
    recent_support_percent: int  # Support % in studies from last 5 years
    older_support_percent: int  # Support % in studies older than 5 years
    recent_study_count: int
    older_study_count: int
    year_range: Tuple[int, int]  # (oldest_year, newest_year)
    research_activity: str  # "active", "moderate", "limited"


@dataclass
class EvidenceCompassResult:
    """Result from Evidence Compass analysis"""
    verdict: str  # "Strong Support", "Moderate Support", "Mixed", "Moderate Against", "Strong Against"
    verdict_score: int  # -100 to +100 (negative = against, positive = support)
    raw_support_percent: int  # Simple % of studies supporting
    weighted_support_percent: int  # Weighted by study quality
    confidence_level: str  # "High", "Medium", "Low"
    confidence_reasons: List[str]
    total_studies: int
    supporting_studies: int
    opposing_studies: int
    neutral_studies: int
    grade_breakdown: Dict[str, Dict[str, int]]  # {"A": {"support": 2, "against": 0}, ...}
    clinical_bottom_line: str
    # v2.2.0: New fields for recency/trend analysis
    recency_trend: Optional[RecencyTrendResult] = None
    sample_size_weighted_percent: Optional[int] = None  # Support % weighted by sample size


class EvidenceCompass:
    """
    Evidence Compass - A weighted evidence analysis system.
    
    Unlike simple "consensus meters" that treat all studies equally,
    Evidence Compass weights studies by:
    - Evidence grade (A > B > C > D)
    - Study design quality
    - Sample size
    - Recency
    
    Provides:
    - Weighted verdict score
    - Confidence level with reasons
    - Breakdown by evidence grade
    - Clinical bottom line summary
    """
    
    # Weight multipliers for evidence grades
    GRADE_WEIGHTS = {
        "A": 4.0,  # Systematic reviews, meta-analyses
        "B": 2.5,  # RCTs
        "C": 1.5,  # Observational studies
        "D": 0.5   # Case reports, low quality
    }
    
    # Keywords indicating SUPPORT for the intervention/outcome
    SUPPORT_KEYWORDS = [
        # Positive outcomes
        "effective", "efficacy", "beneficial", "benefit", "benefits",
        "improved", "improvement", "improves", "improving",
        "reduced", "reduction", "reduces", "reducing", "decrease", "decreased",
        "significant improvement", "significantly improved",
        "positive effect", "positive effects", "positive outcome",
        "superior", "better than", "more effective",
        "recommended", "supports", "supported", "favorable",
        "successful", "success", "promising", "therapeutic effect",
        "statistically significant", "clinically significant",
        "safe and effective", "well-tolerated",
        # For symptom reduction
        "alleviate", "alleviates", "alleviated", "relief",
        "remission", "resolved", "resolution"
    ]
    
    # Keywords indicating OPPOSITION/no effect
    OPPOSE_KEYWORDS = [
        # Negative outcomes
        "no effect", "no significant", "not effective", "ineffective",
        "no difference", "no significant difference", "no benefit",
        "did not improve", "failed to", "no improvement",
        "not recommended", "insufficient evidence", "inconclusive",
        "no association", "not associated", "negative", 
        "harmful", "adverse", "worse", "worsened", "worsening",
        "no change", "unchanged", "similar to placebo",
        "not superior", "not better", "equivalent to placebo",
        "lack of efficacy", "lack of effect",
        # Caution words
        "limited evidence", "weak evidence", "poor quality",
        "high risk of bias", "conflicting results"
    ]
    
    # Keywords indicating NEUTRAL/unclear
    NEUTRAL_KEYWORDS = [
        "mixed results", "mixed findings", "unclear", "uncertain",
        "further research needed", "more studies needed",
        "preliminary", "pilot study", "feasibility",
        "comparable", "similar", "no superiority",
        "modest effect", "small effect", "marginal"
    ]
    
    def __init__(self, query: str):
        """Initialize with the research query for context"""
        self.query = query.lower()
        self._extract_query_context()
    
    def _extract_query_context(self):
        """Extract intervention and outcome from query for better sentiment matching"""
        # Common intervention words to track
        interventions = [
            "yoga", "exercise", "meditation", "therapy", "treatment",
            "vitamin", "supplement", "drug", "medication", "surgery",
            "training", "program", "intervention", "diet"
        ]
        
        # Find intervention in query
        self.intervention = None
        for interv in interventions:
            if interv in self.query:
                self.intervention = interv
                break
        
        # Common outcomes/conditions to track
        conditions = [
            "anxiety", "depression", "pain", "stress", "sleep",
            "walking", "mobility", "function", "quality of life",
            "symptoms", "blood pressure", "glucose", "weight"
        ]
        
        self.condition = None
        for cond in conditions:
            if cond in self.query:
                self.condition = cond
                break
    
    def _classify_article_stance(self, article: ArticleInfo, trust_score: TrustScore) -> str:
        """
        Classify an article's stance as 'support', 'against', or 'neutral'.
        
        Uses abstract text analysis with context from the query.
        """
        abstract_lower = article.abstract.lower()
        title_lower = article.title.lower()
        text = f"{title_lower} {abstract_lower}"
        
        # Count support and oppose signals
        support_count = 0
        oppose_count = 0
        neutral_count = 0
        
        for keyword in self.SUPPORT_KEYWORDS:
            if keyword in text:
                support_count += 1
                # Extra weight for keywords near our intervention/condition
                if self.intervention and self.intervention in text:
                    # Check if keyword is near intervention (within 100 chars)
                    interv_pos = text.find(self.intervention)
                    keyword_pos = text.find(keyword)
                    if abs(interv_pos - keyword_pos) < 100:
                        support_count += 1
        
        for keyword in self.OPPOSE_KEYWORDS:
            if keyword in text:
                oppose_count += 1
        
        for keyword in self.NEUTRAL_KEYWORDS:
            if keyword in text:
                neutral_count += 1
        
        # Check for conclusion patterns
        conclusion_patterns = [
            (r"conclusion[s]?:?\s*(.{50,200})", 2.0),  # Conclusions are weighted more
            (r"in conclusion,?\s*(.{50,200})", 2.0),
            (r"results:?\s*(.{50,200})", 1.5),
            (r"findings:?\s*(.{50,200})", 1.5),
        ]
        
        for pattern, weight in conclusion_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                conclusion_text = match.group(1)
                for kw in self.SUPPORT_KEYWORDS[:10]:  # Top support keywords
                    if kw in conclusion_text:
                        support_count += weight
                for kw in self.OPPOSE_KEYWORDS[:10]:
                    if kw in conclusion_text:
                        oppose_count += weight
        
        # Determine stance
        total = support_count + oppose_count + neutral_count
        if total == 0:
            return "neutral"
        
        support_ratio = support_count / max(1, support_count + oppose_count)
        
        if support_ratio >= 0.65:
            return "support"
        elif support_ratio <= 0.35:
            return "against"
        else:
            return "neutral"
    
    def _calculate_weighted_score(
        self, 
        articles: List[ArticleInfo], 
        trust_scores: List[TrustScore],
        stances: List[str]
    ) -> Tuple[int, int]:
        """
        Calculate both raw and weighted support percentages.
        
        Returns: (raw_percent, weighted_percent)
        """
        if not articles:
            return (0, 0)
        
        # Raw count
        support_count = stances.count("support")
        against_count = stances.count("against")
        total_with_stance = support_count + against_count
        
        raw_percent = int(100 * support_count / max(1, total_with_stance))
        
        # Weighted calculation
        weighted_support = 0.0
        weighted_total = 0.0
        
        for trust, stance in zip(trust_scores, stances):
            grade = trust.evidence_grade
            weight = self.GRADE_WEIGHTS.get(grade, 1.0)
            
            # Also factor in the actual trust score
            weight *= (trust.overall_score / 100.0)
            
            if stance == "support":
                weighted_support += weight
                weighted_total += weight
            elif stance == "against":
                weighted_total += weight
            # Neutral doesn't count toward total
        
        weighted_percent = int(100 * weighted_support / max(0.1, weighted_total))
        
        return (raw_percent, weighted_percent)
    
    def _calculate_confidence(
        self,
        articles: List[ArticleInfo],
        trust_scores: List[TrustScore],
        stances: List[str]
    ) -> Tuple[str, List[str]]:
        """
        Calculate confidence level with reasons.
        
        Returns: (level, [reasons])
        """
        reasons = []
        score = 0  # 0-100 confidence score
        
        # Factor 1: Number of studies (more = higher confidence)
        n = len(articles)
        if n >= 10:
            score += 30
            reasons.append(f"{n} studies analyzed (sufficient volume)")
        elif n >= 5:
            score += 20
            reasons.append(f"{n} studies analyzed (moderate volume)")
        else:
            score += 5
            reasons.append(f"Only {n} studies (limited volume)")
        
        # Factor 2: Grade A/B studies
        high_grade_count = sum(1 for t in trust_scores if t.evidence_grade in ["A", "B"])
        if high_grade_count >= 3:
            score += 30
            reasons.append(f"{high_grade_count} high-quality studies (Grade A/B)")
        elif high_grade_count >= 1:
            score += 15
            reasons.append(f"{high_grade_count} high-quality study (Grade A/B)")
        else:
            reasons.append("No high-quality studies (Grade A/B)")
        
        # Factor 3: Agreement among high-quality studies
        high_grade_stances = [s for t, s in zip(trust_scores, stances) 
                             if t.evidence_grade in ["A", "B"]]
        if high_grade_stances:
            support_in_high = high_grade_stances.count("support")
            against_in_high = high_grade_stances.count("against")
            if support_in_high > 0 and against_in_high == 0:
                score += 25
                reasons.append("High-quality studies agree (all support)")
            elif against_in_high > 0 and support_in_high == 0:
                score += 25
                reasons.append("High-quality studies agree (all against)")
            elif support_in_high > against_in_high:
                score += 15
                reasons.append("Majority of high-quality studies support")
            elif against_in_high > support_in_high:
                score += 15
                reasons.append("Majority of high-quality studies oppose")
            else:
                score += 5
                reasons.append("High-quality studies show mixed results")
        
        # Factor 4: Consistency across all studies
        support_count = stances.count("support")
        against_count = stances.count("against")
        total = support_count + against_count
        if total > 0:
            consistency = max(support_count, against_count) / total
            if consistency >= 0.8:
                score += 15
                reasons.append("Strong consistency across studies (>80% agree)")
            elif consistency >= 0.6:
                score += 10
                reasons.append("Moderate consistency across studies")
            else:
                reasons.append("Low consistency (studies disagree)")
        
        # Determine level
        if score >= 70:
            level = "High"
        elif score >= 40:
            level = "Medium"
        else:
            level = "Low"
        
        return (level, reasons[:4])
    
    def _get_grade_breakdown(
        self,
        trust_scores: List[TrustScore],
        stances: List[str]
    ) -> Dict[str, Dict[str, int]]:
        """Get breakdown of support/against by evidence grade."""
        breakdown = {
            "A": {"support": 0, "against": 0, "neutral": 0},
            "B": {"support": 0, "against": 0, "neutral": 0},
            "C": {"support": 0, "against": 0, "neutral": 0},
            "D": {"support": 0, "against": 0, "neutral": 0}
        }
        
        for trust, stance in zip(trust_scores, stances):
            grade = trust.evidence_grade
            if grade in breakdown:
                breakdown[grade][stance] += 1
        
        return breakdown
    
    def _determine_verdict(self, weighted_percent: int, confidence: str) -> Tuple[str, int]:
        """
        Determine the verdict label and score.
        
        Returns: (verdict_label, verdict_score)
        """
        # Verdict score: -100 (strong against) to +100 (strong support)
        # Map weighted_percent (0-100) to (-100 to +100)
        verdict_score = (weighted_percent * 2) - 100
        
        # Adjust based on confidence
        if confidence == "Low":
            verdict_score = int(verdict_score * 0.7)  # Reduce certainty
        
        # Determine label
        if verdict_score >= 60:
            verdict = "Strong Support"
        elif verdict_score >= 20:
            verdict = "Moderate Support"
        elif verdict_score >= -20:
            verdict = "Mixed Evidence"
        elif verdict_score >= -60:
            verdict = "Moderate Against"
        else:
            verdict = "Strong Against"
        
        return (verdict, verdict_score)
    
    def _generate_bottom_line(
        self,
        verdict: str,
        confidence: str,
        grade_breakdown: Dict[str, Dict[str, int]],
        weighted_percent: int
    ) -> str:
        """Generate a clinical bottom line summary."""
        
        # Count high-quality supporting studies
        a_support = grade_breakdown["A"]["support"]
        b_support = grade_breakdown["B"]["support"]
        total_support = sum(g["support"] for g in grade_breakdown.values())
        total_against = sum(g["against"] for g in grade_breakdown.values())
        
        if verdict == "Strong Support":
            if a_support > 0:
                return f"Strong evidence supports this intervention. {a_support} systematic review(s)/meta-analysis confirm benefit. Consider for clinical practice."
            else:
                return f"Good evidence supports this intervention. {total_support} studies show benefit. Consider for clinical practice with monitoring."
        
        elif verdict == "Moderate Support":
            return f"Moderate evidence suggests benefit. {total_support} studies support vs {total_against} against. Consider patient preferences and individual factors."
        
        elif verdict == "Mixed Evidence":
            return f"Evidence is mixed. Studies show conflicting results ({total_support} support, {total_against} against). Individual assessment recommended."
        
        elif verdict == "Moderate Against":
            return f"Evidence suggests limited or no benefit. {total_against} studies found no effect. Consider alternative interventions."
        
        else:  # Strong Against
            return f"Evidence does not support this intervention. {total_against} studies found no benefit or potential harm. Not recommended."
    
    def _extract_year(self, pub_date: str) -> Optional[int]:
        """Extract year from publication date string."""
        import re
        # Try common formats: "2023", "Jan 2023", "2023 Jan 15", "2023-01-15"
        year_match = re.search(r'\b(19|20)\d{2}\b', pub_date)
        if year_match:
            return int(year_match.group(0))
        return None
    
    def _analyze_recency_trend(
        self,
        articles: List[ArticleInfo],
        trust_scores: List[TrustScore],
        stances: List[str]
    ) -> RecencyTrendResult:
        """
        Analyze how evidence trends over time.
        
        Compares recent studies (last 5 years) vs older studies to see
        if support is strengthening or weakening over time.
        """
        from datetime import datetime
        current_year = datetime.now().year
        cutoff_year = current_year - 5
        
        # Extract years and pair with stances
        study_data = []
        for article, stance in zip(articles, stances):
            year = self._extract_year(article.pub_date)
            if year:
                study_data.append((year, stance))
        
        if len(study_data) < 2:
            return RecencyTrendResult(
                trend_direction="insufficient_data",
                trend_description="Not enough dated studies to analyze trends",
                recent_support_percent=0,
                older_support_percent=0,
                recent_study_count=0,
                older_study_count=0,
                year_range=(0, 0),
                research_activity="limited"
            )
        
        years = [y for y, _ in study_data]
        year_range = (min(years), max(years))
        
        # Split into recent and older
        recent = [(y, s) for y, s in study_data if y >= cutoff_year]
        older = [(y, s) for y, s in study_data if y < cutoff_year]
        
        def calc_support_percent(data):
            if not data:
                return 0
            support = sum(1 for _, s in data if s == "support")
            against = sum(1 for _, s in data if s == "against")
            total = support + against
            return int(100 * support / max(1, total))
        
        recent_support = calc_support_percent(recent)
        older_support = calc_support_percent(older)
        
        # Determine research activity
        recent_count = len(recent)
        if recent_count >= 5:
            research_activity = "active"
        elif recent_count >= 2:
            research_activity = "moderate"
        else:
            research_activity = "limited"
        
        # Determine trend direction
        diff = recent_support - older_support
        
        if len(older) == 0:
            # All studies are recent
            trend_direction = "stable"
            trend_description = f"All {len(recent)} studies are from the past 5 years"
        elif len(recent) == 0:
            trend_direction = "insufficient_data"
            trend_description = "No recent studies (past 5 years) available"
        elif diff >= 20:
            trend_direction = "strengthening"
            trend_description = f"Support increasing: {older_support}% (before {cutoff_year}) → {recent_support}% (recent)"
        elif diff <= -20:
            trend_direction = "weakening"
            trend_description = f"Support decreasing: {older_support}% (before {cutoff_year}) → {recent_support}% (recent)"
        else:
            trend_direction = "stable"
            trend_description = f"Consistent evidence: {older_support}% (older) vs {recent_support}% (recent)"
        
        return RecencyTrendResult(
            trend_direction=trend_direction,
            trend_description=trend_description,
            recent_support_percent=recent_support,
            older_support_percent=older_support,
            recent_study_count=len(recent),
            older_study_count=len(older),
            year_range=year_range,
            research_activity=research_activity
        )
    
    def _calculate_sample_size_weighted_score(
        self,
        trust_scores: List[TrustScore],
        stances: List[str]
    ) -> int:
        """
        Calculate support percentage weighted by sample size.
        
        Studies with larger sample sizes get more weight in the calculation.
        """
        if not trust_scores:
            return 0
        
        weighted_support = 0.0
        weighted_total = 0.0
        
        for trust, stance in zip(trust_scores, stances):
            # Sample size score is 0-100, use it as a weight multiplier
            # Add minimum weight of 0.5 so all studies count somewhat
            weight = 0.5 + (trust.sample_size_score / 100.0)
            
            if stance == "support":
                weighted_support += weight
                weighted_total += weight
            elif stance == "against":
                weighted_total += weight
            # Neutral studies don't count toward total
        
        if weighted_total < 0.1:
            return 0
        
        return int(100 * weighted_support / weighted_total)
    
    def analyze(
        self,
        articles: List[ArticleInfo],
        trust_scores: List[TrustScore]
    ) -> EvidenceCompassResult:
        """
        Analyze articles and produce Evidence Compass result.
        
        Args:
            articles: List of fetched articles
            trust_scores: Corresponding trust scores
            
        Returns:
            EvidenceCompassResult with full analysis
        """
        if not articles:
            return EvidenceCompassResult(
                verdict="Insufficient Evidence",
                verdict_score=0,
                raw_support_percent=0,
                weighted_support_percent=0,
                confidence_level="Low",
                confidence_reasons=["No studies found"],
                total_studies=0,
                supporting_studies=0,
                opposing_studies=0,
                neutral_studies=0,
                grade_breakdown={},
                clinical_bottom_line="No evidence available. Try broadening your search."
            )
        
        # Classify each article's stance
        stances = [self._classify_article_stance(article, trust) 
                   for article, trust in zip(articles, trust_scores)]
        
        # Calculate percentages
        raw_percent, weighted_percent = self._calculate_weighted_score(
            articles, trust_scores, stances
        )
        
        # Calculate confidence
        confidence_level, confidence_reasons = self._calculate_confidence(
            articles, trust_scores, stances
        )
        
        # Get grade breakdown
        grade_breakdown = self._get_grade_breakdown(trust_scores, stances)
        
        # Determine verdict
        verdict, verdict_score = self._determine_verdict(weighted_percent, confidence_level)
        
        # Generate bottom line
        clinical_bottom_line = self._generate_bottom_line(
            verdict, confidence_level, grade_breakdown, weighted_percent
        )
        
        # v2.2.0: Analyze recency trend
        recency_trend = self._analyze_recency_trend(articles, trust_scores, stances)
        
        # v2.2.0: Calculate sample size weighted score
        sample_size_weighted = self._calculate_sample_size_weighted_score(trust_scores, stances)
        
        return EvidenceCompassResult(
            verdict=verdict,
            verdict_score=verdict_score,
            raw_support_percent=raw_percent,
            weighted_support_percent=weighted_percent,
            confidence_level=confidence_level,
            confidence_reasons=confidence_reasons,
            total_studies=len(articles),
            supporting_studies=stances.count("support"),
            opposing_studies=stances.count("against"),
            neutral_studies=stances.count("neutral"),
            grade_breakdown=grade_breakdown,
            clinical_bottom_line=clinical_bottom_line,
            recency_trend=recency_trend,
            sample_size_weighted_percent=sample_size_weighted
        )
    
    def format_ascii_display(self, result: EvidenceCompassResult) -> str:
        """Format the result as a clean, readable display for Gemini CLI."""
        
        # Create simple text progress bar using basic ASCII
        def make_bar(percent: int, width: int = 20) -> str:
            filled = int(width * percent / 100)
            return "[" + "#" * filled + "-" * (width - filled) + "]"
        
        support_bar = make_bar(result.weighted_support_percent)
        against_bar = make_bar(100 - result.weighted_support_percent)
        
        # Trend arrow using simple ASCII
        trend_arrows = {"strengthening": "^", "weakening": "v", "stable": "="}
        
        # Build clean markdown-style output
        lines = [
            "",
            "=" * 60,
            "EVIDENCE COMPASS",
            "=" * 60,
            "",
            f"VERDICT: {result.verdict}",
            "",
            f"  Support: {support_bar} {result.weighted_support_percent}%",
            f"  Against: {against_bar} {100 - result.weighted_support_percent}%",
            "",
            f"  Studies: {result.supporting_studies} support | {result.opposing_studies} against | {result.neutral_studies} neutral",
            "",
            "-" * 40,
            "EVIDENCE BY GRADE:",
        ]
        
        for grade in ["A", "B", "C", "D"]:
            if grade in result.grade_breakdown:
                b = result.grade_breakdown[grade]
                total = b["support"] + b["against"] + b["neutral"]
                if total > 0:
                    lines.append(f"  Grade {grade}: {b['support']} support, {b['against']} against")
        
        lines.extend([
            "",
            "-" * 40,
            f"CONFIDENCE: {result.confidence_level}",
        ])
        
        for reason in result.confidence_reasons[:3]:
            lines.append(f"  - {reason}")
        
        # v2.2.0: Add trend analysis
        if result.recency_trend and result.recency_trend.trend_direction != "insufficient_data":
            trend = result.recency_trend
            arrow = trend_arrows.get(trend.trend_direction, "?")
            lines.extend([
                "",
                "-" * 40,
                f"EVIDENCE TREND: {arrow} {trend.trend_direction.upper()}",
                f"  {trend.trend_description}",
                f"  Recent studies: {trend.recent_study_count} | Older studies: {trend.older_study_count}",
                f"  Year range: {trend.year_range[0]}-{trend.year_range[1]}",
                f"  Research activity: {trend.research_activity}",
            ])
        
        # v2.2.0: Sample size weighted if different
        if result.sample_size_weighted_percent is not None:
            diff = abs(result.sample_size_weighted_percent - result.weighted_support_percent)
            if diff >= 5:
                lines.extend([
                    "",
                    f"  Sample-size weighted support: {result.sample_size_weighted_percent}%",
                ])
        
        lines.extend([
            "",
            "-" * 40,
            "CLINICAL BOTTOM LINE:",
            f"  {result.clinical_bottom_line}",
            "",
            "=" * 60,
        ])
        
        return "\n".join(lines)


class ResearchSynthesizer:
    """Generate comprehensive research summaries"""
    
    def __init__(self, client: PubMedClient, analyzer: TrustAnalyzer):
        self.client = client
        self.analyzer = analyzer
        self.snapshot_generator = StudySnapshotGenerator()
        # v2.5.0: Key findings and contradiction analysis
        self.key_findings_extractor = KeyFindingsExtractor()
        self.contradiction_explainer = ContradictionExplainer()
    
    async def synthesize(self, query: str, max_articles: int = 10) -> Dict[str, Any]:
        pmids = await self.client.search(query, max_articles)
        
        if not pmids:
            return {
                "query": query,
                "articles_found": 0,
                "synthesis": "No articles found for this query. Try broadening your search terms.",
                "recommendations": []
            }
        
        articles = []
        trust_scores = []
        
        for pmid in pmids:
            article = await self.client.fetch_article(pmid)
            if article:
                trust = self.analyzer.analyze(article)
                articles.append(article)
                trust_scores.append(trust)
        
        if not articles:
            return {
                "query": query,
                "articles_found": 0,
                "synthesis": "Failed to retrieve article details.",
                "recommendations": []
            }
        
        synthesis = self._generate_synthesis(articles, trust_scores)
        evidence_summary = self._generate_evidence_summary(trust_scores)
        recommendations = self._generate_recommendations(trust_scores)
        research_gaps = self._identify_research_gaps(trust_scores)
        
        # Generate Evidence Compass analysis
        compass = EvidenceCompass(query)
        compass_result = compass.analyze(articles, trust_scores)
        
        return {
            "query": query,
            "articles_analyzed": len(articles),
            "evidence_compass": {
                "verdict": compass_result.verdict,
                "verdict_score": compass_result.verdict_score,
                "raw_support_percent": compass_result.raw_support_percent,
                "weighted_support_percent": compass_result.weighted_support_percent,
                "sample_size_weighted_percent": compass_result.sample_size_weighted_percent,
                "confidence_level": compass_result.confidence_level,
                "confidence_reasons": compass_result.confidence_reasons,
                "supporting_studies": compass_result.supporting_studies,
                "opposing_studies": compass_result.opposing_studies,
                "neutral_studies": compass_result.neutral_studies,
                "grade_breakdown": compass_result.grade_breakdown,
                "clinical_bottom_line": compass_result.clinical_bottom_line,
                # v2.2.0: Recency trend analysis
                "recency_trend": {
                    "direction": compass_result.recency_trend.trend_direction if compass_result.recency_trend else None,
                    "description": compass_result.recency_trend.trend_description if compass_result.recency_trend else None,
                    "recent_support_percent": compass_result.recency_trend.recent_support_percent if compass_result.recency_trend else None,
                    "older_support_percent": compass_result.recency_trend.older_support_percent if compass_result.recency_trend else None,
                    "recent_study_count": compass_result.recency_trend.recent_study_count if compass_result.recency_trend else None,
                    "older_study_count": compass_result.recency_trend.older_study_count if compass_result.recency_trend else None,
                    "year_range": list(compass_result.recency_trend.year_range) if compass_result.recency_trend else None,
                    "research_activity": compass_result.recency_trend.research_activity if compass_result.recency_trend else None
                } if compass_result.recency_trend else None
            },
            "evidence_summary": evidence_summary,
            "synthesis": synthesis,
            "top_articles": [
                {
                    "pmid": a.pmid,
                    "title": a.title,
                    "journal": a.journal,
                    "pub_date": a.pub_date,
                    "trust_score": t.overall_score,
                    "evidence_grade": t.evidence_grade,
                    "study_design": t.study_design,
                    # v2.4.0: Study snapshot
                    "snapshot": self.snapshot_generator.generate(a).summary,
                    "finding_direction": self.snapshot_generator.generate(a).key_finding,
                    # v2.5.0: Key finding with statistical details
                    "key_finding": {
                        "statement": (kf := self.key_findings_extractor.extract(a)).statement,
                        "direction": kf.direction,
                        "effect_size": kf.effect_size,
                        "p_value": kf.p_value,
                        "confidence_interval": kf.confidence_interval,
                        "practical_significance": kf.practical_significance
                    },
                    # v2.4.0: Clickable full-text links
                    "links": generate_full_text_links(a).to_dict()
                }
                for a, t in sorted(
                    zip(articles, trust_scores),
                    key=lambda x: x[1].overall_score,
                    reverse=True
                )[:5]
            ],
            # v2.5.0: Contradiction analysis
            "contradiction_analysis": self._generate_contradiction_analysis(query, articles, trust_scores, compass),
            "clinical_recommendations": recommendations,
            "research_gaps": research_gaps
        }
    
    def _generate_synthesis(self, articles: List[ArticleInfo], trust_scores: List[TrustScore]) -> str:
        study_types: Dict[str, int] = {}
        for ts in trust_scores:
            design = ts.study_design
            study_types[design] = study_types.get(design, 0) + 1
        
        avg_score = sum(ts.overall_score for ts in trust_scores) / len(trust_scores)
        
        synthesis_parts = []
        synthesis_parts.append(f"This synthesis analyzed {len(articles)} articles from PubMed. ")
        
        type_desc = ", ".join(
            f"{count} {design.lower()}" + ("s" if count > 1 else "")
            for design, count in sorted(study_types.items(), key=lambda x: -x[1])
        )
        synthesis_parts.append(f"Study types included: {type_desc}. ")
        
        if avg_score >= 75:
            synthesis_parts.append("The overall evidence quality is HIGH. ")
        elif avg_score >= 60:
            synthesis_parts.append("The overall evidence quality is MODERATE. ")
        else:
            synthesis_parts.append("The overall evidence quality is LIMITED. ")
        
        return "".join(synthesis_parts)
    
    def _generate_evidence_summary(self, trust_scores: List[TrustScore]) -> Dict[str, Any]:
        scores = [ts.overall_score for ts in trust_scores]
        grades = {"A": 0, "B": 0, "C": 0, "D": 0}
        for ts in trust_scores:
            grades[ts.evidence_grade] += 1
        
        return {
            "total_articles": len(trust_scores),
            "average_trust_score": round(sum(scores) / len(scores), 1),
            "score_range": f"{min(scores)}-{max(scores)}",
            "grade_distribution": grades,
            "high_quality_count": sum(1 for s in scores if s >= 70)
        }
    
    def _generate_recommendations(self, trust_scores: List[TrustScore]) -> List[str]:
        recommendations = []
        high_quality = [t for t in trust_scores if t.overall_score >= 75]
        moderate = [t for t in trust_scores if 60 <= t.overall_score < 75]
        
        if high_quality:
            recommendations.append("Strong evidence supports consideration in clinical practice")
        elif moderate:
            recommendations.append("Moderate evidence - consider patient preferences")
        else:
            recommendations.append("Limited evidence - individualize clinical decisions")
        
        return recommendations[:4]
    
    def _identify_research_gaps(self, trust_scores: List[TrustScore]) -> List[str]:
        gaps = []
        
        if not any(t.overall_score >= 80 for t in trust_scores):
            gaps.append("No Grade A evidence - high-quality RCTs needed")
        
        if not any("Systematic Review" in t.study_design for t in trust_scores):
            gaps.append("No systematic review found")
        
        if not gaps:
            gaps.append("Consider long-term follow-up studies")
        
        return gaps[:4]
    
    def _generate_contradiction_analysis(
        self,
        query: str,
        articles: List[ArticleInfo],
        trust_scores: List[TrustScore],
        compass: EvidenceCompass
    ) -> Optional[Dict[str, Any]]:
        """
        Generate contradiction analysis using the ContradictionExplainer (v2.5.0).
        
        Returns None if no contradiction is detected.
        """
        # Get stances from EvidenceCompass
        stances = [compass._classify_article_stance(a, t) for a, t in zip(articles, trust_scores)]
        
        # Run contradiction analysis
        contradiction = self.contradiction_explainer.explain(query, articles, stances)
        
        if not contradiction.has_contradiction:
            return None
        
        return {
            "has_contradiction": contradiction.has_contradiction,
            "summary": contradiction.summary,
            "supporting_count": contradiction.supporting_count,
            "opposing_count": contradiction.opposing_count,
            "factors": contradiction.factors,
            "synthesis": contradiction.synthesis
        }


# MCP Protocol Implementation
class MCPServer:
    """Standalone MCP server using JSON-RPC over stdio"""
    
    def __init__(self):
        self.pubmed_client = PubMedClient()
        self.pico_extractor = PICOExtractor()
        self.trust_analyzer = TrustAnalyzer()
        self.synthesizer = ResearchSynthesizer(self.pubmed_client, self.trust_analyzer)
        self.citation_exporter = CitationExporter()
        self.snapshot_generator = StudySnapshotGenerator()
        # v2.5.0: Key findings and contradiction analysis
        self.key_findings_extractor = KeyFindingsExtractor()
        self.contradiction_explainer = ContradictionExplainer()
        
        self.tools = {
            "enhanced_pubmed_search": self._handle_enhanced_search,
            "analyze_article_trustworthiness": self._handle_analyze_trustworthiness,
            "generate_research_summary": self._handle_research_summary,
            "export_citations": self._handle_export_citations,
        }
    
    def get_tools_list(self) -> List[Dict[str, Any]]:
        """Return list of available tools"""
        return [
            {
                "name": "enhanced_pubmed_search",
                "description": (
                    "Perform advanced PubMed searches with PICO analysis, query optimization, "
                    "and trustworthiness assessment. Use for clinical questions requiring "
                    "systematic evidence review."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Clinical question (e.g., 'Does exercise help chronic back pain?')"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Number of results (default: 10, max: 20)",
                            "default": 10
                        },
                        "include_pico": {
                            "type": "boolean",
                            "description": "Include PICO analysis",
                            "default": True
                        },
                        "include_trust_scores": {
                            "type": "boolean",
                            "description": "Include quality assessment",
                            "default": True
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "analyze_article_trustworthiness",
                "description": (
                    "Analyze the methodological quality and evidence strength of a specific "
                    "PubMed article. Use for critical appraisal and evidence grading."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pmid": {
                            "type": "string",
                            "description": "PubMed ID (e.g., '34580864')"
                        }
                    },
                    "required": ["pmid"]
                }
            },
            {
                "name": "generate_research_summary",
                "description": (
                    "Create comprehensive AI-powered research synthesis with PhD-level analysis. "
                    "Includes evidence synthesis, clinical recommendations, and research gap identification."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Clinical research question"
                        },
                        "max_articles": {
                            "type": "integer",
                            "description": "Articles to analyze (default: 10, max: 15)",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "export_citations",
                "description": (
                    "Export PubMed articles to standard citation formats for reference managers. "
                    "Supports BibTeX (LaTeX), RIS (Zotero/Mendeley), and EndNote formats. "
                    "Provide either PMIDs or a search query."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pmids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of PubMed IDs to export (e.g., ['12345678', '87654321'])"
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query to find articles to export (alternative to pmids)"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["bibtex", "ris", "endnote"],
                            "description": "Citation format: 'bibtex' for LaTeX, 'ris' for Zotero/Mendeley, 'endnote' for EndNote",
                            "default": "bibtex"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Max articles to export when using query (default: 10, max: 50)",
                            "default": 10
                        }
                    },
                    "required": ["format"]
                }
            }
        ]
    
    async def _handle_enhanced_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle enhanced PubMed search with tiered PICO analysis"""
        query = args.get("query", "")
        max_results = min(args.get("max_results", 10), 20)
        include_pico = args.get("include_pico", True)
        include_trust = args.get("include_trust_scores", True)
        
        # Use enhanced PICO extraction
        enhanced_pico = self.pico_extractor.extract_enhanced(query) if include_pico else None
        pmids = await self.pubmed_client.search(query, max_results)
        
        if not pmids:
            return {
                "query": query,
                "pico_analysis": asdict(enhanced_pico) if enhanced_pico else None,
                "results": [],
                "total_found": 0,
                "message": "No articles found. Try broader search terms.",
                "suggestions": enhanced_pico.suggestions if enhanced_pico else []
            }
        
        results = []
        articles_for_compass = []
        trust_scores_for_compass = []
        
        for pmid in pmids:
            article = await self.pubmed_client.fetch_article(pmid)
            if article:
                # Generate full-text links (v2.4.0)
                links = generate_full_text_links(article)
                
                # Generate study snapshot (v2.4.0)
                snapshot = self.snapshot_generator.generate(article)
                
                # v2.5.0: Extract key finding with effect sizes
                key_finding = self.key_findings_extractor.extract(article)
                
                result = {
                    "pmid": article.pmid,
                    "title": article.title,
                    "authors": article.authors,
                    "journal": article.journal,
                    "pub_date": article.pub_date,
                    "abstract": article.abstract[:500] + "..." if len(article.abstract) > 500 else article.abstract,
                    # v2.4.0: Study snapshot - 2 sentence summary
                    "snapshot": snapshot.summary,
                    "finding_direction": snapshot.key_finding,
                    "sample_size": snapshot.sample_size,
                    # v2.5.0: Key finding with statistical details
                    "key_finding": {
                        "statement": key_finding.statement,
                        "direction": key_finding.direction,
                        "effect_size": key_finding.effect_size,
                        "p_value": key_finding.p_value,
                        "confidence_interval": key_finding.confidence_interval,
                        "practical_significance": key_finding.practical_significance
                    },
                    # v2.4.0: Full-text links (clickable URLs)
                    "links": links.to_dict(),
                }
                
                if include_trust:
                    trust = self.trust_analyzer.analyze(article)
                    result["trust_score"] = trust.overall_score
                    result["evidence_grade"] = trust.evidence_grade
                    result["study_design"] = trust.study_design
                    articles_for_compass.append(article)
                    trust_scores_for_compass.append(trust)
                
                results.append(result)
        
        response = {
            "query": query,
            "optimized_question": enhanced_pico.clinical_question if enhanced_pico else query,
            "pico_analysis": asdict(enhanced_pico) if enhanced_pico else None,
            "total_found": len(results),
            "results": results
        }
        
        # Add enhanced PICO features to response
        if enhanced_pico:
            response["complexity_level"] = enhanced_pico.complexity_label
            response["medical_domain"] = enhanced_pico.domain
            response["confidence_score"] = enhanced_pico.confidence_score
            response["suggestions"] = enhanced_pico.suggestions
            response["optimized_search_terms"] = enhanced_pico.search_terms
        
        # Add Evidence Compass if we have trust scores
        if include_trust and articles_for_compass:
            compass = EvidenceCompass(query)
            compass_result = compass.analyze(articles_for_compass, trust_scores_for_compass)
            ascii_display = compass.format_ascii_display(compass_result)
            response["evidence_compass"] = {
                "verdict": compass_result.verdict,
                "weighted_support_percent": compass_result.weighted_support_percent,
                "confidence_level": compass_result.confidence_level,
                "supporting_studies": compass_result.supporting_studies,
                "opposing_studies": compass_result.opposing_studies,
                "clinical_bottom_line": compass_result.clinical_bottom_line,
                "display": ascii_display
            }
        
        return response
    
    async def _handle_analyze_trustworthiness(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle article trustworthiness analysis"""
        pmid = args.get("pmid", "").strip()
        
        if not pmid:
            return {"error": "PMID is required"}
        
        article = await self.pubmed_client.fetch_article(pmid)
        
        if not article:
            return {"error": f"Article with PMID {pmid} not found"}
        
        trust = self.trust_analyzer.analyze(article)
        
        grade_descriptions = {
            "A": "Excellent evidence - High-quality systematic reviews or multiple RCTs",
            "B": "Good evidence - Well-designed RCTs or high-quality cohort studies",
            "C": "Fair evidence - Observational studies with moderate risk of bias",
            "D": "Limited evidence - Case reports, expert opinion, or high risk of bias"
        }
        
        return {
            "pmid": pmid,
            "title": article.title,
            "authors": article.authors,
            "journal": article.journal,
            "pub_date": article.pub_date,
            "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "trust_analysis": {
                "overall_score": trust.overall_score,
                "evidence_grade": trust.evidence_grade,
                "grade_description": grade_descriptions.get(trust.evidence_grade, "Unknown"),
                "study_design": trust.study_design,
                "component_scores": {
                    "methodology": trust.methodology_score,
                    "sample_size": trust.sample_size_score,
                    "recency": trust.recency_score,
                    "journal_quality": trust.journal_score
                },
                "strengths": trust.strengths,
                "limitations": trust.limitations
            },
            "abstract": article.abstract,
            "mesh_terms": article.mesh_terms
        }
    
    async def _handle_research_summary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research summary generation"""
        query = args.get("query", "")
        max_articles = min(args.get("max_articles", 10), 15)
        
        if not query:
            return {"error": "Query is required"}
        
        pico = self.pico_extractor.extract(query)
        synthesis = await self.synthesizer.synthesize(query, max_articles)
        synthesis["pico_analysis"] = asdict(pico)
        
        return synthesis
    
    async def _handle_export_citations(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle citation export to BibTeX, RIS, or EndNote format."""
        pmids = args.get("pmids", [])
        query = args.get("query", "")
        format_type = args.get("format", "bibtex").lower()
        max_results = min(args.get("max_results", 10), 50)
        
        # Validate format
        if format_type not in CitationExporter.SUPPORTED_FORMATS and format_type not in ["bib", "enw"]:
            return {
                "error": f"Unsupported format: {format_type}",
                "supported_formats": CitationExporter.SUPPORTED_FORMATS,
                "hint": "Use 'bibtex' for LaTeX, 'ris' for Zotero/Mendeley, 'endnote' for EndNote"
            }
        
        # Need either PMIDs or a query
        if not pmids and not query:
            return {
                "error": "Either 'pmids' or 'query' is required",
                "example_pmids": ["12345678", "87654321"],
                "example_query": "yoga anxiety randomized controlled trial"
            }
        
        # If query provided, search for PMIDs first
        if query and not pmids:
            pmids = await self.pubmed_client.search(query, max_results)
            if not pmids:
                return {
                    "error": f"No articles found for query: {query}",
                    "suggestion": "Try broader search terms or check spelling"
                }
        
        # Fetch articles
        articles = []
        failed_pmids = []
        
        for pmid in pmids:
            pmid_str = str(pmid).strip()
            article = await self.pubmed_client.fetch_article(pmid_str)
            if article:
                articles.append(article)
            else:
                failed_pmids.append(pmid_str)
        
        if not articles:
            return {
                "error": "Could not fetch any articles",
                "failed_pmids": failed_pmids
            }
        
        # Export to requested format
        try:
            exported = self.citation_exporter.export_multiple(articles, format_type)
        except ValueError as e:
            return {"error": str(e)}
        
        # Format-specific file extension hints
        extensions = {
            "bibtex": ".bib",
            "bib": ".bib",
            "ris": ".ris",
            "endnote": ".enw",
            "enw": ".enw"
        }
        
        return {
            "format": format_type,
            "file_extension": extensions.get(format_type, ".txt"),
            "articles_exported": len(articles),
            "failed_pmids": failed_pmids if failed_pmids else None,
            "query": query if query else None,
            "exported_pmids": [a.pmid for a in articles],
            "citations": exported,
            "usage_hint": f"Copy the 'citations' content and save to a file with {extensions.get(format_type, '.txt')} extension"
        }
    
    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming JSON-RPC request"""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "pubmed-research-mcp",
                        "version": "2.6.0"
                    }
                }
            elif method == "notifications/initialized":
                return None  # No response for notifications
            elif method == "tools/list":
                result = {"tools": self.get_tools_list()}
            elif method == "tools/call":
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})
                
                if tool_name in self.tools:
                    tool_result = await self.tools[tool_name](tool_args)
                    result = {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(tool_result, indent=2)
                            }
                        ]
                    }
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown tool: {tool_name}"
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
    
    async def run(self):
        """Run the MCP server over stdio"""
        print("PubMed MCP Server started", file=sys.stderr)
        
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        
        writer_transport, writer_protocol = await loop.connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, loop)
        
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                
                try:
                    request = json.loads(line.decode('utf-8'))
                    response = await self.handle_request(request)
                    
                    if response is not None:
                        response_bytes = json.dumps(response).encode('utf-8') + b'\n'
                        writer.write(response_bytes)
                        await writer.drain()
                        
                except json.JSONDecodeError as e:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": f"Parse error: {str(e)}"
                        }
                    }
                    writer.write(json.dumps(error_response).encode('utf-8') + b'\n')
                    await writer.drain()
                    
        except Exception as e:
            print(f"Server error: {e}", file=sys.stderr)
        finally:
            await self.pubmed_client.close()


async def main():
    server = MCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
