#!/usr/bin/env python3
"""Test script for Enhanced PICO Extraction System"""

import asyncio
import sys
sys.path.insert(0, '.')

from pubmed_mcp import PubMedClient, PICOExtractor, TrustAnalyzer, ResearchSynthesizer

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


if __name__ == "__main__":
    # First run PICO extraction tests (fast, no API calls)
    passed, failed = test_pico_extraction()
    
    # Then run full search test if extraction tests pass
    if failed == 0:
        print("\nAll PICO extraction tests passed! Running full search test...\n")
        asyncio.run(test_full_search())
    else:
        print(f"\n{failed} PICO extraction tests failed. Fix issues before running full search.\n")
