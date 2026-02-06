# Learning Log

Where we capture what works, what doesn't, and why.

---

## What Works
- **Title Fallback:** Searching by title resolves >50% of "Suspicious" flags caused by PDF layout issues.
- **Year Tolerance:** Accepting a +/- 1 year difference resolves almost all "Online First" false positives.

## What Doesn't Work
- **Strict Matching:** The tool's default strictness flags valid papers as "Suspicious" due to `\n` or `-` characters.
- **Non-Journal Verification:** The tool consistently fails on Books (McArdle), Software (SPSS), and Guidelines (PRISMA).
- **DOI Reliance:** Old DOIs often break ("DOI Rot"). Do not assume a broken DOI = Fake citation if the title exists.

## Patterns to Remember
- **The "PDF Layout" Pattern:**
    - **Symptom:** 90%+ Failure Rate in a document.
    - **Cause:** Column breaks and hyphenation.
- **The "Page Footer Contamination" Pattern (2026-02-04):**
    - **Symptom:** "Downloaded from..." or "Vol 59..." lines treated as citations.
    - **Fix:** Agent must ignore these lines during text cleaning.
- **The "Grey Literature" Pattern:**
    - **Symptom:** "Not Found" for WHO, AHRQ, or "Association" citations.
    - **Verdict:** Valid but Non-Indexed.
- **The "Frankenstein" Pattern:**
    - **Symptom:** DOI resolves to a *totally different* paper.
    - **Verdict:** FAKE.
- **The "False Frankenstein" Pattern (2026-02-06):**
    - **Symptom:** "Definite Fake" flag on a valid reference.
    - **Cause:** PDF parsing "squishes" two citations together, associating DOI A with Title B.
    - **Fix:** Apply "Reverse Lookup" - Search the title to confirm the DOI is actually correct.

## Known Tool Quirks
- **Parsing:** Merged citations (`1. Author... 2. Author...`) break the parser.
- **Scope:** Physics/CS/Math journals often appear as "Not Found."