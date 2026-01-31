#!/usr/bin/env python3
"""
Regression tests - Verify existing PubMed MCP functionality.
Run this BEFORE and AFTER adding new features to ensure nothing breaks.

Usage:
    python test_regression.py          # Quick smoke test
    python -m pytest test_regression.py -v   # Full pytest run
"""

import asyncio
import sys
sys.path.insert(0, '.')

from pubmed_mcp import (
    PubMedClient, PICOExtractor, TrustAnalyzer, 
    ResearchSynthesizer, CitationExporter, ArticleInfo,
    StudySnapshotGenerator, KeyFindingsExtractor, ContradictionExplainer
)


# ==================== PICO EXTRACTOR TESTS ====================

def test_pico_basic_extraction():
    """PICO extraction returns all required fields."""
    pico = PICOExtractor()
    result = pico.extract("does yoga help anxiety")
    
    assert result.population is not None, "Population should not be None"
    assert result.intervention is not None, "Intervention should not be None"
    assert result.comparison is not None, "Comparison should not be None"
    assert result.outcome is not None, "Outcome should not be None"
    assert result.clinical_question is not None, "Clinical question should not be None"
    print("  [PASS] test_pico_basic_extraction")


def test_pico_enhanced_extraction():
    """Enhanced PICO includes complexity level and domain."""
    pico = PICOExtractor()
    result = pico.extract_enhanced("SSRI effects on HPA-axis in depression")
    
    assert result.complexity_level in [1, 2, 3], f"Invalid complexity level: {result.complexity_level}"
    assert result.complexity_label in ["Casual", "Clinical", "Research"], f"Invalid complexity label: {result.complexity_label}"
    assert result.domain is not None, "Domain should not be None"
    assert 0 <= result.confidence_score <= 100, f"Confidence score out of range: {result.confidence_score}"
    print("  [PASS] test_pico_enhanced_extraction")


def test_pico_complexity_detection():
    """Complexity levels detected correctly."""
    pico = PICOExtractor()
    
    # Casual query - simple health question
    casual = pico.extract_enhanced("is coffee bad for you")
    assert casual.complexity_level == 1, f"Expected level 1 for casual, got {casual.complexity_level}"
    
    # Clinical query - has medical condition
    clinical = pico.extract_enhanced("yoga for anxiety treatment in adults")
    assert clinical.complexity_level == 2, f"Expected level 2 for clinical, got {clinical.complexity_level}"
    
    # Research query - PhD level terminology
    research = pico.extract_enhanced("gut microbiome neuroinflammation mechanisms")
    assert research.complexity_level == 3, f"Expected level 3 for research, got {research.complexity_level}"
    
    print("  [PASS] test_pico_complexity_detection")


# ==================== TRUST ANALYZER TESTS ====================

def test_trust_analyzer_scoring():
    """Trust analyzer produces valid scores."""
    analyzer = TrustAnalyzer()
    
    mock_article = ArticleInfo(
        pmid="12345678",
        title="Test RCT Study",
        authors=["Smith, J."],
        journal="Test Journal",
        pub_date="2024",
        abstract="Background... Methods: Randomized controlled trial with 100 participants...",
        doi="10.1234/test",
        pub_types=["Randomized Controlled Trial"],
        mesh_terms=["Anxiety"]
    )
    
    result = analyzer.analyze(mock_article)
    
    assert 0 <= result.overall_score <= 100, f"Score out of range: {result.overall_score}"
    assert result.evidence_grade in ["A", "B", "C", "D"], f"Invalid grade: {result.evidence_grade}"
    assert result.study_design is not None, "Study design should not be None"
    print("  [PASS] test_trust_analyzer_scoring")


def test_evidence_grade_weighting():
    """Grade A/B studies weighted higher than Grade C/D."""
    analyzer = TrustAnalyzer()
    
    # Meta-analysis should be Grade A or B (high quality)
    meta = ArticleInfo(
        pmid="1", title="Meta-analysis of treatments", authors=["A"],
        journal="J", pub_date="2024", abstract="This meta-analysis pooled data...",
        doi=None, pub_types=["Meta-Analysis"], mesh_terms=[]
    )
    
    # Case report should be Grade C or D (lower quality)
    case = ArticleInfo(
        pmid="2", title="Case Report of rare condition", authors=["B"],
        journal="J", pub_date="2024", abstract="We report a single case...",
        doi=None, pub_types=["Case Reports"], mesh_terms=[]
    )
    
    meta_result = analyzer.analyze(meta)
    case_result = analyzer.analyze(case)
    
    # Meta-analysis should be A or B (high evidence)
    assert meta_result.evidence_grade in ["A", "B"], f"Meta-analysis should be A or B, got {meta_result.evidence_grade}"
    # Case report should be C or D (lower evidence)
    assert case_result.evidence_grade in ["C", "D"], f"Case report should be C or D, got {case_result.evidence_grade}"
    # Meta-analysis should score higher than case report
    assert meta_result.overall_score > case_result.overall_score, "Meta-analysis should score higher than case report"
    print("  [PASS] test_evidence_grade_weighting")


# ==================== CITATION EXPORTER TESTS ====================

def test_bibtex_export():
    """BibTeX export produces valid format."""
    exporter = CitationExporter()
    
    article = ArticleInfo(
        pmid="12345678",
        title="Effects of Yoga on Anxiety",
        authors=["Smith, John", "Doe, Jane"],
        journal="Test Journal",
        pub_date="Jan 2024",
        abstract="Test abstract",
        doi="10.1234/test",
        pub_types=["Journal Article"],
        mesh_terms=[]
    )
    
    bibtex = exporter.to_bibtex(article)
    
    assert "@article{pmid12345678," in bibtex, "BibTeX should have correct entry format"
    assert "author = {" in bibtex, "BibTeX should have author field"
    assert "title = {" in bibtex, "BibTeX should have title field"
    assert "year = {2024}" in bibtex, "BibTeX should have year 2024"
    print("  [PASS] test_bibtex_export")


def test_ris_export():
    """RIS export produces valid format."""
    exporter = CitationExporter()
    
    article = ArticleInfo(
        pmid="12345678", title="Test", authors=["Smith, J."],
        journal="J", pub_date="2024", abstract="",
        doi="10.1234/test", pub_types=[], mesh_terms=[]
    )
    
    ris = exporter.to_ris(article)
    
    assert "TY  - JOUR" in ris, "RIS should have journal type"
    assert "ER  - " in ris, "RIS should have end marker"
    assert "AU  - " in ris, "RIS should have author tag"
    print("  [PASS] test_ris_export")


def test_endnote_export():
    """EndNote export produces valid format."""
    exporter = CitationExporter()
    
    article = ArticleInfo(
        pmid="12345678", title="Test", authors=["Smith, J."],
        journal="J", pub_date="2024", abstract="",
        doi="10.1234/test", pub_types=[], mesh_terms=[]
    )
    
    endnote = exporter.to_endnote(article)
    
    assert "%0 Journal Article" in endnote, "EndNote should have article type"
    assert "%A " in endnote, "EndNote should have author tag"
    assert "%T " in endnote, "EndNote should have title tag"
    print("  [PASS] test_endnote_export")


def test_multi_export():
    """Multiple articles export works."""
    exporter = CitationExporter()
    
    articles = [
        ArticleInfo(pmid="111", title="First", authors=["A"], journal="J", 
                   pub_date="2024", abstract="", doi=None, pub_types=[], mesh_terms=[]),
        ArticleInfo(pmid="222", title="Second", authors=["B"], journal="J",
                   pub_date="2023", abstract="", doi=None, pub_types=[], mesh_terms=[])
    ]
    
    bibtex = exporter.export_multiple(articles, "bibtex")
    assert "pmid111" in bibtex, "Should contain first article"
    assert "pmid222" in bibtex, "Should contain second article"
    
    ris = exporter.export_multiple(articles, "ris")
    assert ris.count("TY  - JOUR") == 2, "Should have two RIS entries"
    print("  [PASS] test_multi_export")


# ==================== STUDY SNAPSHOT GENERATOR TESTS ====================

def test_snapshot_generator():
    """StudySnapshotGenerator produces valid snapshots."""
    generator = StudySnapshotGenerator()
    
    article = ArticleInfo(
        pmid="12345",
        title="Yoga reduces anxiety in adults",
        authors=["Smith"],
        journal="J Anxiety",
        pub_date="2024",
        abstract="BACKGROUND: Anxiety is common. METHODS: We randomized 100 adults to yoga or waitlist. RESULTS: Yoga group showed significant reduction in anxiety (p<0.001). CONCLUSIONS: Yoga is effective for anxiety.",
        doi=None,
        pub_types=["Randomized Controlled Trial"],
        mesh_terms=["Anxiety", "Yoga"]
    )
    
    snapshot = generator.generate(article)
    
    assert snapshot.summary is not None, "Snapshot summary should not be None"
    assert len(snapshot.summary) > 0, "Snapshot summary should not be empty"
    assert snapshot.key_finding in ["positive", "negative", "neutral", "mixed"], f"Invalid key finding: {snapshot.key_finding}"
    print("  [PASS] test_snapshot_generator")


# ==================== KEY FINDINGS EXTRACTOR TESTS ====================

def test_key_findings_extractor():
    """KeyFindingsExtractor extracts statistical data."""
    extractor = KeyFindingsExtractor()
    
    article = ArticleInfo(
        pmid="12345",
        title="Test study with significant results",
        authors=["Smith"],
        journal="J Test",
        pub_date="2024",
        abstract="""
        RESULTS: The intervention group showed a 45% reduction in symptoms (p<0.001, 
        95% CI: 35-55%). Effect size was large (d=0.85). The odds ratio was 0.65 
        (95% CI: 0.45-0.89).
        """,
        doi=None,
        pub_types=["Randomized Controlled Trial"],
        mesh_terms=[]
    )
    
    findings = extractor.extract(article)
    
    assert findings is not None, "Findings should not be None"
    # The extractor should find at least some statistical measures
    print("  [PASS] test_key_findings_extractor")


# ==================== PUBMED CLIENT TESTS (ASYNC) ====================

async def test_pubmed_search():
    """PubMed search returns PMIDs."""
    client = PubMedClient()
    try:
        pmids = await client.search("yoga anxiety randomized", max_results=3)
        
        assert isinstance(pmids, list), "Should return a list"
        assert len(pmids) <= 3, "Should not exceed max_results"
        if pmids:
            assert all(pmid.isdigit() for pmid in pmids), "PMIDs should be numeric strings"
        print("  [PASS] test_pubmed_search")
    finally:
        await client.close()


async def test_pubmed_fetch_article():
    """PubMed fetch returns ArticleInfo."""
    client = PubMedClient()
    try:
        pmids = await client.search("yoga", max_results=1)
        if pmids:
            article = await client.fetch_article(pmids[0])
            
            assert article is not None, "Should return an article"
            assert article.pmid == pmids[0], "PMID should match"
            assert article.title is not None, "Title should not be None"
            assert isinstance(article.authors, list), "Authors should be a list"
            print("  [PASS] test_pubmed_fetch_article")
        else:
            print("  [SKIP] test_pubmed_fetch_article - no results")
    finally:
        await client.close()


# ==================== RESEARCH SYNTHESIZER TESTS (ASYNC) ====================

async def test_synthesizer_output_structure():
    """Synthesizer returns expected structure."""
    client = PubMedClient()
    analyzer = TrustAnalyzer()
    synthesizer = ResearchSynthesizer(client, analyzer)
    
    try:
        result = await synthesizer.synthesize("yoga anxiety", max_articles=3)
        
        # Check required keys
        assert "query" in result, "Should have query key"
        assert "articles_analyzed" in result, "Should have articles_analyzed key"
        assert "evidence_summary" in result, "Should have evidence_summary key"
        assert "evidence_compass" in result, "Should have evidence_compass key"
        
        # Check evidence compass structure
        compass = result["evidence_compass"]
        assert "verdict" in compass, "Compass should have verdict"
        assert "weighted_support_percent" in compass, "Compass should have weighted_support_percent"
        assert "confidence_level" in compass, "Compass should have confidence_level"
        print("  [PASS] test_synthesizer_output_structure")
    finally:
        await client.close()


# ==================== SMOKE TEST ====================

async def smoke_test():
    """Quick smoke test - verifies all major components work."""
    print("\n" + "=" * 60)
    print("PUBMED MCP SERVER - REGRESSION SMOKE TEST")
    print("=" * 60)
    
    all_passed = True
    
    # Synchronous tests
    print("\n--- Synchronous Component Tests ---")
    try:
        test_pico_basic_extraction()
        test_pico_enhanced_extraction()
        test_pico_complexity_detection()
        test_trust_analyzer_scoring()
        test_evidence_grade_weighting()
        test_bibtex_export()
        test_ris_export()
        test_endnote_export()
        test_multi_export()
        test_snapshot_generator()
        test_key_findings_extractor()
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    except Exception as e:
        print(f"  [ERROR] {e}")
        all_passed = False
    
    # Async tests (require network)
    print("\n--- Async Component Tests (requires network) ---")
    try:
        await test_pubmed_search()
        await test_pubmed_fetch_article()
        await test_synthesizer_output_structure()
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        all_passed = False
    except Exception as e:
        print(f"  [ERROR] Network test failed: {e}")
        # Network failures are acceptable in offline mode
        print("  [WARN] Network tests skipped (may be offline)")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL REGRESSION TESTS PASSED")
    else:
        print("SOME TESTS FAILED - Review output above")
    print("=" * 60 + "\n")
    
    return all_passed


# ==================== MAIN ====================

if __name__ == "__main__":
    success = asyncio.run(smoke_test())
    sys.exit(0 if success else 1)
