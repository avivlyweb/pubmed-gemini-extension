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
            
            # Extract DOI
            doi = None
            for article_id in article.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi":
                    doi = article_id.text
                    break
            
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
                mesh_terms=mesh_terms[:10]
            )
        except ET.ParseError:
            return None
    
    async def close(self):
        await self.client.aclose()


class PICOExtractor:
    """Extract PICO components from clinical questions"""
    
    POPULATION_KEYWORDS = [
        "patient", "adult", "child", "elderly", "women", "men", "people with",
        "individuals", "subjects", "participants", "diagnosed with"
    ]
    
    INTERVENTION_KEYWORDS = [
        "treatment", "therapy", "intervention", "drug", "medication", "surgery",
        "exercise", "diet", "supplement", "program", "training"
    ]
    
    COMPARISON_KEYWORDS = [
        "compared to", "versus", "vs", "or", "placebo", "control", "standard care",
        "usual care", "alternative", "compared with"
    ]
    
    OUTCOME_KEYWORDS = [
        "effect", "outcome", "improve", "reduce", "increase", "decrease",
        "mortality", "survival", "quality of life", "symptom", "pain", "function"
    ]
    
    def extract(self, query: str) -> PICOAnalysis:
        """Extract PICO components from a clinical question"""
        query_lower = query.lower()
        
        population = self._extract_component(query_lower, self.POPULATION_KEYWORDS)
        if not population:
            population = self._infer_population(query_lower)
        
        intervention = self._extract_component(query_lower, self.INTERVENTION_KEYWORDS)
        if not intervention:
            intervention = self._infer_intervention(query_lower)
        
        comparison = self._extract_comparison(query_lower)
        
        outcome = self._extract_component(query_lower, self.OUTCOME_KEYWORDS)
        if not outcome:
            outcome = self._infer_outcome(query_lower)
        
        clinical_question = self._generate_clinical_question(
            population, intervention, comparison, outcome
        )
        
        return PICOAnalysis(
            population=population or "General population",
            intervention=intervention or "Intervention of interest",
            comparison=comparison or "Standard care or placebo",
            outcome=outcome or "Clinical outcomes",
            clinical_question=clinical_question
        )
    
    def _extract_component(self, query: str, keywords: List[str]) -> Optional[str]:
        for keyword in keywords:
            if keyword in query:
                idx = query.find(keyword)
                start = max(0, idx - 30)
                end = min(len(query), idx + len(keyword) + 50)
                context = query[start:end].strip()
                return context
        return None
    
    def _extract_comparison(self, query: str) -> Optional[str]:
        comparison_patterns = [
            r"compared to\s+(\w+(?:\s+\w+)*)",
            r"versus\s+(\w+(?:\s+\w+)*)",
            r"vs\.?\s+(\w+(?:\s+\w+)*)",
        ]
        
        for pattern in comparison_patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(1)[:50]
        return None
    
    def _infer_population(self, query: str) -> str:
        conditions = [
            "diabetes", "hypertension", "cancer", "depression", "anxiety",
            "arthritis", "asthma", "copd", "heart disease", "stroke",
            "obesity", "back pain", "migraine", "insomnia"
        ]
        for condition in conditions:
            if condition in query:
                return f"Patients with {condition}"
        return "Adults"
    
    def _infer_intervention(self, query: str) -> str:
        interventions = [
            ("exercise", "Exercise therapy"),
            ("yoga", "Yoga practice"),
            ("meditation", "Meditation/mindfulness"),
            ("vitamin", "Vitamin supplementation"),
            ("surgery", "Surgical intervention"),
            ("physical therapy", "Physical therapy"),
            ("cognitive", "Cognitive behavioral therapy"),
            ("acupuncture", "Acupuncture"),
            ("massage", "Massage therapy")
        ]
        for keyword, intervention in interventions:
            if keyword in query:
                return intervention
        return "Treatment intervention"
    
    def _infer_outcome(self, query: str) -> str:
        if any(word in query for word in ["help", "effective", "work", "benefit"]):
            return "Clinical improvement and symptom reduction"
        if "prevent" in query:
            return "Prevention of disease/condition"
        if "safe" in query:
            return "Safety and adverse events"
        return "Clinical outcomes"
    
    def _generate_clinical_question(
        self, population: Optional[str], intervention: Optional[str], 
        comparison: Optional[str], outcome: Optional[str]
    ) -> str:
        parts = []
        if population:
            parts.append(f"In {population.lower()}")
        if intervention:
            parts.append(f"does {intervention.lower()}")
        if comparison:
            parts.append(f"compared to {comparison.lower()}")
        if outcome:
            parts.append(f"improve {outcome.lower()}")
        
        return ", ".join(parts) + "?" if parts else "Clinical question"


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


class ResearchSynthesizer:
    """Generate comprehensive research summaries"""
    
    def __init__(self, client: PubMedClient, analyzer: TrustAnalyzer):
        self.client = client
        self.analyzer = analyzer
    
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
        
        return {
            "query": query,
            "articles_analyzed": len(articles),
            "evidence_summary": evidence_summary,
            "synthesis": synthesis,
            "top_articles": [
                {
                    "pmid": a.pmid,
                    "title": a.title,
                    "journal": a.journal,
                    "trust_score": t.overall_score,
                    "evidence_grade": t.evidence_grade,
                    "study_design": t.study_design
                }
                for a, t in sorted(
                    zip(articles, trust_scores),
                    key=lambda x: x[1].overall_score,
                    reverse=True
                )[:5]
            ],
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


# MCP Protocol Implementation
class MCPServer:
    """Standalone MCP server using JSON-RPC over stdio"""
    
    def __init__(self):
        self.pubmed_client = PubMedClient()
        self.pico_extractor = PICOExtractor()
        self.trust_analyzer = TrustAnalyzer()
        self.synthesizer = ResearchSynthesizer(self.pubmed_client, self.trust_analyzer)
        
        self.tools = {
            "enhanced_pubmed_search": self._handle_enhanced_search,
            "analyze_article_trustworthiness": self._handle_analyze_trustworthiness,
            "generate_research_summary": self._handle_research_summary,
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
            }
        ]
    
    async def _handle_enhanced_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle enhanced PubMed search"""
        query = args.get("query", "")
        max_results = min(args.get("max_results", 10), 20)
        include_pico = args.get("include_pico", True)
        include_trust = args.get("include_trust_scores", True)
        
        pico = self.pico_extractor.extract(query) if include_pico else None
        pmids = await self.pubmed_client.search(query, max_results)
        
        if not pmids:
            return {
                "query": query,
                "pico_analysis": asdict(pico) if pico else None,
                "results": [],
                "total_found": 0,
                "message": "No articles found. Try broader search terms."
            }
        
        results = []
        for pmid in pmids:
            article = await self.pubmed_client.fetch_article(pmid)
            if article:
                result = {
                    "pmid": article.pmid,
                    "title": article.title,
                    "authors": article.authors,
                    "journal": article.journal,
                    "pub_date": article.pub_date,
                    "abstract": article.abstract[:500] + "..." if len(article.abstract) > 500 else article.abstract,
                    "doi": article.doi,
                    "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{article.pmid}/"
                }
                
                if include_trust:
                    trust = self.trust_analyzer.analyze(article)
                    result["trust_score"] = trust.overall_score
                    result["evidence_grade"] = trust.evidence_grade
                    result["study_design"] = trust.study_design
                
                results.append(result)
        
        return {
            "query": query,
            "optimized_question": pico.clinical_question if pico else query,
            "pico_analysis": asdict(pico) if pico else None,
            "total_found": len(results),
            "results": results
        }
    
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
                        "name": "pubmed-mcp",
                        "version": "1.0.0"
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
