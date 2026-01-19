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
            clinical_bottom_line=clinical_bottom_line
        )
    
    def format_ascii_display(self, result: EvidenceCompassResult) -> str:
        """Format the result as an ASCII display for terminal output."""
        
        # Create progress bar
        def make_bar(percent: int, width: int = 20) -> str:
            filled = int(width * percent / 100)
            return "█" * filled + "░" * (width - filled)
        
        support_bar = make_bar(result.weighted_support_percent)
        against_bar = make_bar(100 - result.weighted_support_percent)
        
        # Build output
        lines = [
            "╔══════════════════════════════════════════════════════════════╗",
            "║                     EVIDENCE COMPASS                          ║",
            "╠══════════════════════════════════════════════════════════════╣",
            f"║  Query: {self.query[:52]:<52} ║",
            "║                                                              ║",
            f"║  VERDICT: {result.verdict:<48} ║",
            "║                                                              ║",
            f"║  Support {support_bar} {result.weighted_support_percent:>3}% (weighted)      ║",
            f"║  Against {against_bar} {100-result.weighted_support_percent:>3}%              ║",
            "║                                                              ║",
            f"║  Raw agreement: {result.raw_support_percent}% | Weighted: {result.weighted_support_percent}%                    ║",
            "║                                                              ║",
            "║  EVIDENCE BREAKDOWN                                          ║",
            "║  ────────────────────                                        ║",
        ]
        
        for grade in ["A", "B", "C", "D"]:
            if grade in result.grade_breakdown:
                b = result.grade_breakdown[grade]
                if b["support"] + b["against"] + b["neutral"] > 0:
                    lines.append(f"║    Grade {grade}: {b['support']} support, {b['against']} against, {b['neutral']} neutral          ║")
        
        lines.extend([
            "║                                                              ║",
            f"║  CONFIDENCE: {result.confidence_level:<46} ║",
        ])
        
        for reason in result.confidence_reasons[:3]:
            lines.append(f"║    • {reason:<54} ║")
        
        lines.extend([
            "║                                                              ║",
            "║  CLINICAL BOTTOM LINE:                                       ║",
        ])
        
        # Word wrap the bottom line
        bottom_line = result.clinical_bottom_line
        while len(bottom_line) > 54:
            lines.append(f"║    {bottom_line[:54]} ║")
            bottom_line = bottom_line[54:]
        if bottom_line:
            lines.append(f"║    {bottom_line:<54} ║")
        
        lines.append("╚══════════════════════════════════════════════════════════════╝")
        
        return "\n".join(lines)


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
        
        # Generate Evidence Compass analysis
        compass = EvidenceCompass(query)
        compass_result = compass.analyze(articles, trust_scores)
        ascii_display = compass.format_ascii_display(compass_result)
        
        return {
            "query": query,
            "articles_analyzed": len(articles),
            "evidence_compass": {
                "verdict": compass_result.verdict,
                "verdict_score": compass_result.verdict_score,
                "raw_support_percent": compass_result.raw_support_percent,
                "weighted_support_percent": compass_result.weighted_support_percent,
                "confidence_level": compass_result.confidence_level,
                "confidence_reasons": compass_result.confidence_reasons,
                "supporting_studies": compass_result.supporting_studies,
                "opposing_studies": compass_result.opposing_studies,
                "neutral_studies": compass_result.neutral_studies,
                "grade_breakdown": compass_result.grade_breakdown,
                "clinical_bottom_line": compass_result.clinical_bottom_line,
                "display": ascii_display
            },
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
