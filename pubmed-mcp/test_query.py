#!/usr/bin/env python3
"""Test script for PubMed MCP server query"""

import asyncio
import sys
sys.path.insert(0, '.')

from pubmed_mcp import PubMedClient, PICOExtractor, TrustAnalyzer, ResearchSynthesizer

async def test_yoga_anxiety_query():
    """Test the yoga/anxiety query"""
    query = "In patients with anxiety, does yoga practice, improve clinical improvement and symptom reduction"
    
    print(f"\n{'='*60}")
    print(f"PUBMED RESEARCH QUERY TEST")
    print(f"{'='*60}")
    print(f"\nQuery: {query}\n")
    
    # Initialize components
    pubmed_client = PubMedClient()
    pico_extractor = PICOExtractor()
    trust_analyzer = TrustAnalyzer()
    synthesizer = ResearchSynthesizer(pubmed_client, trust_analyzer)
    
    # Extract PICO
    print("PICO ANALYSIS")
    print("-" * 40)
    pico = pico_extractor.extract(query)
    print(f"  Population:   {pico.population}")
    print(f"  Intervention: {pico.intervention}")
    print(f"  Comparison:   {pico.comparison}")
    print(f"  Outcome:      {pico.outcome}")
    print(f"  Clinical Q:   {pico.clinical_question}")
    
    # Search PubMed
    print(f"\n{'='*60}")
    print("SEARCHING PUBMED...")
    print("-" * 40)
    
    pmids = await pubmed_client.search(query, max_results=5)
    print(f"Found {len(pmids)} articles: {pmids}")
    
    if not pmids:
        print("No results found!")
        return
    
    # Fetch and analyze articles
    print(f"\n{'='*60}")
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
    print(f"\n{'='*60}")
    print("RESEARCH SYNTHESIS")
    print("-" * 40)
    
    synthesis = await synthesizer.synthesize(query, max_articles=5)
    print(f"Query: {synthesis['query']}")
    print(f"Articles Analyzed: {synthesis['articles_analyzed']}")
    
    evidence = synthesis.get('evidence_summary', {})
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
    
    print(f"\n{'='*60}")
    print("TEST COMPLETED SUCCESSFULLY")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    asyncio.run(test_yoga_anxiety_query())
