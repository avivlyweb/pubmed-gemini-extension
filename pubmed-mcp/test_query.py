#!/usr/bin/env python3
"""Test script for Enhanced PICO Extraction System"""

import asyncio
import sys
sys.path.insert(0, '.')

from pubmed_mcp import PubMedClient, PICOExtractor, TrustAnalyzer, ResearchSynthesizer, CitationExporter, ArticleInfo

# Test queries organized by complexity level
TEST_QUERIES = [
    # Level 1: Casual (General public - no specific medical conditions)
    ("Is coffee bad for you?", 1, "Casual"),
    ("What foods are healthy?", 1, "Casual"),
    
    # Level 2: Clinical (Healthcare professionals/students - has medical conditions or interventions)
    ("What helps with back pain?", 2, "Clinical"),  # back pain = medical condition
    ("Does yoga help anxiety?", 2, "Clinical"),
    ("Best exercises for COPD patients", 2, "Clinical"),
    ("Vitamin D for bone health in elderly", 2, "Clinical"),
    ("exercises to improve walking in copd patients", 2, "Clinical"),
    
    # Level 3: Research (PhD-level)
    ("Effect of SSRI on HPA-axis in treatment-resistant depression", 3, "Research"),
    ("Gut microbiome interventions for neonatal neuroinflammation", 3, "Research"),
]


def test_pico_extraction():
    """Test PICO extraction for all query types"""
    pico_extractor = PICOExtractor()
    
    print("\n" + "=" * 80)
    print("ENHANCED PICO EXTRACTION TEST")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for query, expected_level, expected_label in TEST_QUERIES:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"Expected: Level {expected_level} ({expected_label})")
        print("-" * 80)
        
        # Extract enhanced PICO
        pico = pico_extractor.extract_enhanced(query)
        
        # Check if complexity detection is correct
        level_match = pico.complexity_level == expected_level
        
        print(f"\nDetected Complexity: Level {pico.complexity_level} ({pico.complexity_label})")
        print(f"Medical Domain: {pico.domain}")
        print(f"Confidence Score: {pico.confidence_score}/100")
        
        print(f"\nPICO Components:")
        print(f"  Population:   {pico.population}")
        print(f"  Intervention: {pico.intervention}")
        print(f"  Comparison:   {pico.comparison}")
        print(f"  Outcome:      {pico.outcome}")
        
        print(f"\nClinical Question:")
        print(f"  {pico.clinical_question}")
        
        print(f"\nOptimized Search Terms:")
        print(f"  {pico.search_terms}")
        
        if pico.suggestions:
            print(f"\nSuggestions to Improve Query:")
            for i, suggestion in enumerate(pico.suggestions, 1):
                print(f"  {i}. {suggestion}")
        
        # Validate results
        status = "PASS" if level_match else "FAIL"
        if level_match:
            passed += 1
        else:
            failed += 1
        
        print(f"\nStatus: [{status}] - Complexity detection {'correct' if level_match else 'INCORRECT'}")
        
        # Additional validation for known patterns
        query_lower = query.lower()
        if "copd" in query_lower:
            if "copd" in pico.population.lower() or "pulmonary" in pico.population.lower():
                print("  [OK] COPD correctly identified in population")
            else:
                print("  [WARN] COPD should be in population")
        
        if "yoga" in query_lower:
            if "yoga" in pico.intervention.lower():
                print("  [OK] Yoga correctly identified as intervention")
            else:
                print("  [WARN] Yoga should be in intervention")
        
        if "anxiety" in query_lower:
            if "anxiety" in pico.population.lower() or "anxiety" in pico.outcome.lower():
                print("  [OK] Anxiety correctly identified")
            else:
                print("  [WARN] Anxiety should be in population or outcome")
    
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY: {passed} passed, {failed} failed out of {len(TEST_QUERIES)} tests")
    print(f"{'='*80}\n")
    
    return passed, failed


async def test_full_search():
    """Test full search with one example query"""
    query = "exercises to improve walking in copd patients"
    
    print(f"\n{'='*80}")
    print(f"FULL SEARCH TEST")
    print(f"{'='*80}")
    print(f"\nQuery: {query}\n")
    
    # Initialize components
    pubmed_client = PubMedClient()
    pico_extractor = PICOExtractor()
    trust_analyzer = TrustAnalyzer()
    synthesizer = ResearchSynthesizer(pubmed_client, trust_analyzer)
    
    # Extract enhanced PICO
    print("ENHANCED PICO ANALYSIS")
    print("-" * 40)
    pico = pico_extractor.extract_enhanced(query)
    print(f"  Complexity:   Level {pico.complexity_level} ({pico.complexity_label})")
    print(f"  Domain:       {pico.domain}")
    print(f"  Confidence:   {pico.confidence_score}/100")
    print(f"  Population:   {pico.population}")
    print(f"  Intervention: {pico.intervention}")
    print(f"  Comparison:   {pico.comparison}")
    print(f"  Outcome:      {pico.outcome}")
    print(f"  Clinical Q:   {pico.clinical_question}")
    
    if pico.suggestions:
        print(f"\n  Suggestions:")
        for s in pico.suggestions:
            print(f"    - {s}")
    
    # Search PubMed
    print(f"\n{'='*80}")
    print("SEARCHING PUBMED...")
    print("-" * 40)
    
    pmids = await pubmed_client.search(query, max_results=5)
    print(f"Found {len(pmids)} articles: {pmids}")
    
    if not pmids:
        print("No results found!")
        await pubmed_client.close()
        return
    
    # Fetch and analyze articles
    print(f"\n{'='*80}")
    print("ARTICLE ANALYSIS")
    print("-" * 40)
    
    for i, pmid in enumerate(pmids[:5], 1):
        article = await pubmed_client.fetch_article(pmid)
        if article:
            trust = trust_analyzer.analyze(article)
            print(f"\n{i}. PMID: {article.pmid}")
            print(f"   Title: {article.title[:80]}...")
            print(f"   Journal: {article.journal}")
            print(f"   Date: {article.pub_date}")
            print(f"   Trust Score: {trust.overall_score}/100")
            print(f"   Evidence Grade: {trust.evidence_grade}")
            print(f"   Study Design: {trust.study_design}")
            print(f"   URL: https://pubmed.ncbi.nlm.nih.gov/{article.pmid}/")
    
    # Generate synthesis
    print(f"\n{'='*80}")
    print("RESEARCH SYNTHESIS")
    print("-" * 40)
    
    synthesis = await synthesizer.synthesize(query, max_articles=5)
    print(f"Query: {synthesis['query']}")
    print(f"Articles Analyzed: {synthesis['articles_analyzed']}")
    
    # Display Evidence Compass
    compass = synthesis.get('evidence_compass', {})
    if compass:
        print(f"\n{'='*80}")
        print("EVIDENCE COMPASS")
        print("-" * 40)
        
        # Create visual bar
        weighted = compass.get('weighted_support_percent', 0)
        bar_filled = int(20 * weighted / 100)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        
        print(f"\n  VERDICT: {compass.get('verdict', 'N/A')}")
        print(f"\n  Support {bar} {weighted}% (weighted)")
        print(f"  Against {'█' * (20-bar_filled) + '░' * bar_filled} {100-weighted}%")
        print(f"\n  Raw agreement: {compass.get('raw_support_percent', 0)}% | Weighted: {weighted}%")
        print(f"\n  Studies: {compass.get('supporting_studies', 0)} support, {compass.get('opposing_studies', 0)} against, {compass.get('neutral_studies', 0)} neutral")
        
        print(f"\n  EVIDENCE BREAKDOWN BY GRADE:")
        breakdown = compass.get('grade_breakdown', {})
        for grade in ['A', 'B', 'C', 'D']:
            if grade in breakdown:
                b = breakdown[grade]
                total = b.get('support', 0) + b.get('against', 0) + b.get('neutral', 0)
                if total > 0:
                    print(f"    Grade {grade}: {b.get('support', 0)} support, {b.get('against', 0)} against")
        
        print(f"\n  CONFIDENCE: {compass.get('confidence_level', 'N/A')}")
        for reason in compass.get('confidence_reasons', []):
            print(f"    • {reason}")
        
        print(f"\n  CLINICAL BOTTOM LINE:")
        print(f"    {compass.get('clinical_bottom_line', 'N/A')}")
    
    evidence = synthesis.get('evidence_summary', {})
    print(f"\n{'='*80}")
    print("EVIDENCE SUMMARY")
    print("-" * 40)
    print(f"Average Trust Score: {evidence.get('average_trust_score', 'N/A')}")
    print(f"Score Range: {evidence.get('score_range', 'N/A')}")
    print(f"Grade Distribution: {evidence.get('grade_distribution', {})}")
    
    print(f"\nSynthesis:")
    print(f"  {synthesis.get('synthesis', 'N/A')}")
    
    print(f"\nClinical Recommendations:")
    for rec in synthesis.get('clinical_recommendations', []):
        print(f"  - {rec}")
    
    print(f"\nResearch Gaps:")
    for gap in synthesis.get('research_gaps', []):
        print(f"  - {gap}")
    
    await pubmed_client.close()
    
    print(f"\n{'='*80}")
    print("FULL SEARCH TEST COMPLETED SUCCESSFULLY")
    print(f"{'='*80}\n")


def test_citation_export():
    """Test citation export to all formats"""
    print(f"\n{'='*80}")
    print("CITATION EXPORT TEST")
    print(f"{'='*80}")
    
    exporter = CitationExporter()
    
    # Create a mock article for testing
    mock_article = ArticleInfo(
        pmid="12345678",
        title="Effects of Yoga on Anxiety: A Randomized Controlled Trial",
        authors=["John Smith", "Jane Doe", "Robert Johnson"],
        journal="Journal of Clinical Medicine",
        pub_date="Jan 2024",
        abstract="Background: Anxiety disorders are common. Methods: We randomized 100 participants. Results: Yoga reduced anxiety significantly (p<0.001). Conclusion: Yoga is effective for anxiety.",
        doi="10.1234/jcm.2024.0001",
        pub_types=["Randomized Controlled Trial"],
        mesh_terms=["Anxiety", "Yoga", "Adult", "Treatment Outcome"]
    )
    
    print("\n" + "-"*40)
    print("TEST 1: BibTeX Export")
    print("-"*40)
    bibtex = exporter.to_bibtex(mock_article)
    print(bibtex)
    
    # Validate BibTeX
    assert "@article{pmid12345678," in bibtex, "BibTeX should have correct entry type"
    assert "author = {Smith, John and Doe, Jane and Johnson, Robert}" in bibtex, "Authors should be formatted correctly"
    assert "year = {2024}" in bibtex, "Year should be extracted"
    assert "doi = {10.1234/jcm.2024.0001}" in bibtex, "DOI should be included"
    print("\n[PASS] BibTeX export valid")
    
    print("\n" + "-"*40)
    print("TEST 2: RIS Export")
    print("-"*40)
    ris = exporter.to_ris(mock_article)
    print(ris)
    
    # Validate RIS
    assert "TY  - JOUR" in ris, "RIS should have journal type"
    assert "AU  - John Smith" in ris, "Authors should be on separate lines"
    assert "TI  - Effects of Yoga on Anxiety" in ris, "Title should be included"
    assert "DO  - 10.1234/jcm.2024.0001" in ris, "DOI should be included"
    assert "ER  - " in ris, "RIS should have end marker"
    print("\n[PASS] RIS export valid")
    
    print("\n" + "-"*40)
    print("TEST 3: EndNote Export")
    print("-"*40)
    endnote = exporter.to_endnote(mock_article)
    print(endnote)
    
    # Validate EndNote
    assert "%0 Journal Article" in endnote, "EndNote should have article type"
    assert "%A John Smith" in endnote, "Authors should use %A tag"
    assert "%T Effects of Yoga on Anxiety" in endnote, "Title should use %T tag"
    assert "%R 10.1234/jcm.2024.0001" in endnote, "DOI should use %R tag"
    print("\n[PASS] EndNote export valid")
    
    print("\n" + "-"*40)
    print("TEST 4: Multiple Articles Export")
    print("-"*40)
    
    # Create second mock article
    mock_article2 = ArticleInfo(
        pmid="87654321",
        title="Exercise for Depression in Older Adults",
        authors=["Sarah Wilson"],
        journal="Geriatric Medicine Journal",
        pub_date="Mar 2023",
        abstract="Exercise improves depression in elderly patients.",
        doi="10.5678/gmj.2023.002",
        pub_types=["Systematic Review"],
        mesh_terms=["Depression", "Exercise", "Aged"]
    )
    
    # Test multi-export
    multi_bibtex = exporter.export_multiple([mock_article, mock_article2], "bibtex")
    assert "@article{pmid12345678," in multi_bibtex, "First article should be in export"
    assert "@article{pmid87654321," in multi_bibtex, "Second article should be in export"
    print(f"BibTeX multi-export: {len(multi_bibtex)} characters")
    print("[PASS] Multiple BibTeX export valid")
    
    multi_ris = exporter.export_multiple([mock_article, mock_article2], "ris")
    assert multi_ris.count("TY  - JOUR") == 2, "Should have two RIS entries"
    print(f"RIS multi-export: {len(multi_ris)} characters")
    print("[PASS] Multiple RIS export valid")
    
    print(f"\n{'='*80}")
    print("ALL CITATION EXPORT TESTS PASSED")
    print(f"{'='*80}\n")
    
    return True


async def test_citation_export_live():
    """Test citation export with real PubMed articles"""
    print(f"\n{'='*80}")
    print("LIVE CITATION EXPORT TEST")
    print(f"{'='*80}")
    
    pubmed_client = PubMedClient()
    exporter = CitationExporter()
    
    # Search for real articles
    print("\nSearching PubMed for 'yoga anxiety'...")
    pmids = await pubmed_client.search("yoga anxiety randomized", max_results=3)
    print(f"Found {len(pmids)} articles: {pmids}")
    
    if not pmids:
        print("No articles found, skipping live test")
        await pubmed_client.close()
        return
    
    # Fetch and export
    articles = []
    for pmid in pmids:
        article = await pubmed_client.fetch_article(pmid)
        if article:
            articles.append(article)
    
    print(f"\nFetched {len(articles)} articles")
    
    # Export to each format
    for format_name in ["bibtex", "ris", "endnote"]:
        print(f"\n{'-'*40}")
        print(f"{format_name.upper()} Export:")
        print(f"{'-'*40}")
        exported = exporter.export_multiple(articles, format_name)
        # Show first 500 chars
        preview = exported[:500] + "..." if len(exported) > 500 else exported
        print(preview)
    
    await pubmed_client.close()
    
    print(f"\n{'='*80}")
    print("LIVE CITATION EXPORT TEST COMPLETED")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    # First run PICO extraction tests (fast, no API calls)
    passed, failed = test_pico_extraction()
    
    # Run citation export tests (no API calls)
    test_citation_export()
    
    # Then run full search test if extraction tests pass
    if failed == 0:
        print("\nAll PICO extraction tests passed! Running full search test...\n")
        asyncio.run(test_full_search())
        
        # Run live citation export test
        print("\nRunning live citation export test...")
        asyncio.run(test_citation_export_live())
    else:
        print(f"\n{failed} PICO extraction tests failed. Fix issues before running full search.\n")
