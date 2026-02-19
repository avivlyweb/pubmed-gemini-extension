#!/usr/bin/env python3
"""
Quick test script for the Nagomi forensic server
"""

import asyncio
import sys
sys.path.insert(0, '.')

from pubmed_mcp import PubMedClient, PICOExtractor, TrustAnalyzer, ResearchSynthesizer

async def test_search():
    print("Testing Nagomi forensic server Components...")
    print("=" * 50)
    
    client = PubMedClient()
    pico = PICOExtractor()
    analyzer = TrustAnalyzer()
    
    try:
        # Test PICO extraction
        print("\n1. Testing PICO Extraction...")
        query = "does yoga help anxiety"
        pico_result = pico.extract(query)
        print(f"   Query: {query}")
        print(f"   Population: {pico_result.population}")
        print(f"   Intervention: {pico_result.intervention}")
        print(f"   Comparison: {pico_result.comparison}")
        print(f"   Outcome: {pico_result.outcome}")
        print(f"   Clinical Question: {pico_result.clinical_question}")
        
        # Test PubMed search
        print("\n2. Testing PubMed Search...")
        pmids = await client.search(query, max_results=3)
        print(f"   Found {len(pmids)} articles: {pmids}")
        
        if pmids:
            # Test article fetch
            print("\n3. Testing Article Fetch...")
            article = await client.fetch_article(pmids[0])
            if article:
                print(f"   Title: {article.title[:80]}...")
                print(f"   Journal: {article.journal}")
                print(f"   Authors: {', '.join(article.authors[:3])}...")
                
                # Test trust analysis
                print("\n4. Testing Trust Analysis...")
                trust = analyzer.analyze(article)
                print(f"   Overall Score: {trust.overall_score}/100")
                print(f"   Evidence Grade: {trust.evidence_grade}")
                print(f"   Study Design: {trust.study_design}")
                print(f"   Strengths: {trust.strengths}")
                print(f"   Limitations: {trust.limitations}")
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_search())
