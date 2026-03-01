#!/usr/bin/env python3
"""
Test specifically for the new Hallucination Detection features:
- Volume/Year Paradox
- Sequential ID Mismatch (Cureus e-ID)
"""

import asyncio
import sys
import os

# Add the current directory to sys.path to find reference_checker
sys.path.insert(0, os.getcwd())

from reference_checker import ReferenceExtractor, VerificationEngine, VerificationStatus

async def test_hallucinations():
    extractor = ReferenceExtractor()
    engine = VerificationEngine()
    
    print("\n" + "="*60)
    print("TESTING HALLUCINATION DETECTION (ABC-TOM v3.1.0)")
    print("="*60)

    # 1. Test Volume Paradox (Laverde et al. 2025)
    print("\n[Case 1] Laverde et al. (2025) - CSBJ Vol 27")
    raw_laverde = "Laverde, N., (2025). Integrating LLM-based agents. Computational and Structural Biotechnology Journal, 27, 2481–2491."
    ref_laverde = extractor.extract(raw_laverde)
    
    vol_warning = engine._check_volume_plausibility(ref_laverde)
    print(f"  - Extracted: {ref_laverde.journal}, Vol {ref_laverde.volume}, Year {ref_laverde.year}")
    print(f"  - Result: {vol_warning if vol_warning else 'No paradox found'}")
    assert vol_warning and "VOLUME PARADOX" in vol_warning

    # 2. Test Sequential ID Mismatch (Stoco et al. 2025)
    print("\n[Case 2] Stoco et al. (2025) - Cureus ID 10532")
    raw_stoco = "Stoco, A. (2025). Simulating interactions. Cureus, 17(1), e10532. doi: 10.7759/cureus.10532"
    ref_stoco = extractor.extract(raw_stoco)
    
    id_warning = engine._check_sequential_id_plausibility(ref_stoco)
    print(f"  - Extracted: {ref_stoco.journal}, DOI {ref_stoco.doi}, Year {ref_stoco.year}")
    print(f"  - Result: {id_warning if id_warning else 'No ID mismatch found'}")
    assert id_warning and "SEQUENTIAL ID MISMATCH" in id_warning

    # 3. Test Integration in verify()
    print("\n[Case 3] Full Verification Integration")
    result = await engine.verify(ref_stoco)
    print(f"  - Status: {result.status.value}")
    print(f"  - Fake Indicators: {result.fake_indicators}")
    
    # It should be DEFINITE_FAKE because of the ID mismatch
    assert result.status == VerificationStatus.DEFINITE_FAKE
    assert any("SEQUENTIAL ID MISMATCH" in fi for fi in result.fake_indicators)

    print("\n" + "="*60)
    print("ALL HALLUCINATION DETECTION TESTS PASSED")
    print("="*60 + "\n")
    
    await engine.close()

if __name__ == "__main__":
    asyncio.run(test_hallucinations())
