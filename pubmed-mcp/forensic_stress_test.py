#!/usr/bin/env python3
"""
Nagomi Clinical Forensic - v3.1.0 Stress Test Suite
Category: Academic Integrity & Hallucination Detection
"""

import asyncio
import sys
import os

# Add the current directory to sys.path to find reference_checker
sys.path.insert(0, os.getcwd())

from reference_checker import ReferenceExtractor, VerificationEngine, VerificationStatus

async def run_forensic_suite():
    extractor = ReferenceExtractor()
    engine = VerificationEngine()
    
    test_results = []

    print("\n" + "█"*60)
    print(" NAGOMI CLINICAL FORENSIC - STRESS TEST v3.1.0")
    print("█"*60)

    # TEST 1: POSITIVE CONTROL (Real 2025 Paper)
    print("\n[Test 1] Positive Control (Real 2025 Paper)")
    raw = "Ferrer-Peña, R., (2025). Feasibility of a RCT... JMIR Formative Research, 9(1), e66126. doi: 10.2196/66126"
    result = await engine.verify(extractor.extract(raw))
    passed = result.status == VerificationStatus.VERIFIED
    test_results.append(("Positive Control", passed))
    print(f"  - Status: {result.status.value} | {'✅ PASSED' if passed else '❌ FAILED'}")

    # TEST 2: VOLUME PARADOX (Impossible Volume)
    print("\n[Test 2] Volume Paradox (Math Logic)")
    raw = "Smith, J. (2025). AI in Biotech. Computational and Structural Biotechnology Journal, 50, 100-110."
    result = await engine.verify(extractor.extract(raw))
    # CSBJ started 2012. 2025 should be Vol ~13. Vol 50 is impossible.
    passed = result.status == VerificationStatus.DEFINITE_FAKE and any("VOLUME PARADOX" in fi for fi in result.fake_indicators)
    test_results.append(("Volume Paradox", passed))
    print(f"  - Indicators: {result.fake_indicators}")
    print(f"  - Result: {'✅ PASSED' if passed else '❌ FAILED'}")

    # TEST 3: SEQUENTIAL ID MISMATCH (Identity Theft)
    print("\n[Test 3] Sequential ID Mismatch (Cureus Stolen ID)")
    raw = "Doe, A. (2025). AI in Physio. Cureus, 17(1), e10532. doi: 10.7759/cureus.10532"
    result = await engine.verify(extractor.extract(raw))
    # ID 10532 is 2020. 2025 is impossible for this ID.
    passed = result.status == VerificationStatus.DEFINITE_FAKE and any("SEQUENTIAL ID MISMATCH" in fi for fi in result.fake_indicators)
    test_results.append(("Sequential ID", passed))
    print(f"  - Indicators: {result.fake_indicators}")
    print(f"  - Result: {'✅ PASSED' if passed else '❌ FAILED'}")

    # TEST 4: FRANKENSTEIN CITATION (Title/DOI Mismatch)
    print("\n[Test 4] Frankenstein Citation (Fake Title + Real DOI)")
    raw = "Yanyan, S. (2025). AI in Physical Therapy. Cureus, 12(9), e10532. doi: 10.7759/cureus.10532"
    result = await engine.verify(extractor.extract(raw))
    passed = result.status == VerificationStatus.DEFINITE_FAKE
    test_results.append(("Frankenstein", passed))
    print(f"  - Status: {result.status.value}")
    print(f"  - Result: {'✅ PASSED' if passed else '❌ FAILED'}")

    # TEST 5: GHOST DOI (Doesn't Resolve)
    print("\n[Test 5] Ghost DOI (Non-existent link)")
    raw = "Ghost, G. (2025). Phantom Science. J. Ed. Tech, 1(1), 1-10. doi: 10.1016/j.jeths.2025.03.005"
    result = await engine.verify(extractor.extract(raw))
    passed = result.status == VerificationStatus.NOT_FOUND
    test_results.append(("Ghost DOI", passed))
    print(f"  - Status: {result.status.value}")
    print(f"  - Result: {'✅ PASSED' if passed else '❌ FAILED'}")

    print("\n" + "█"*60)
    print(" FINAL FORENSIC AUDIT SUMMARY")
    print("█"*60)
    all_passed = True
    for name, success in test_results:
        print(f"{name:.<20} {'✅ OK' if success else '❌ FAIL'}")
        if not success: all_passed = False
    
    print("\nOVERALL SUITE STATUS: " + ("✅ 100% VERIFIED" if all_passed else "❌ SYSTEM ERROR"))
    print("█"*60 + "\n")
    
    await engine.close()
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(run_forensic_suite())
    sys.exit(0 if success else 1)
