# Reference Verification Protocol

## 1. Input Validation
- **File Paths:** Check existence and use absolute paths.
- **Text Cleaning:**
    - Fix split words (`-\n`).
    - **Remove Noise:** Delete lines starting with "Downloaded from", "Available at", "Vol.", or "Copyright".

## 2. The Verification Cascade
When a reference is flagged as **NOT FOUND** or **SUSPICIOUS**:

1.  **Level 1: Source Type Filter (The "Grey Lit" Check)**
    - **Is it Grey Literature?** Check for keywords: "Agency", "Association", "Department", "Council", "WHO", "Guideline", "Report".
    - **Is it a Book/Software?** (e.g., "SPSS", "Handbook").
    - **Action:** Mark as **"Manual Check Required (Non-Indexed Source)"**.

2.  **Level 2: Title Search (The "Layout Fix")**
    - If raw text has formatting noise, search PubMed for the *Title* only.
    - *Success Criteria:* >80% Title Match = **VERIFIED**.

3.  **Level 3: Web Resolution**
    - For recent papers (< 18 months), check `doi.org`.

4.  **Level 4: The Reverse Lookup Safety Valve (CRITICAL)**
    - **Trigger:** System detects a "DOI Mismatch" (Frankenstein).
    - **Action:** Search the *Cited Title* in Google Scholar/PubMed.
    - **Check 1 (Title):** Does the search result return the *Cited DOI*?
        - **Yes:** Proceed to Check 2.
        - **No:** The citation is **FAKE** (Title/DOI mismatch confirmed).
    - **Check 2 (Authors):** Do the authors in the search result match the *Cited Authors*?
        - **Yes:** The citation is **VALID** (Parsing error cleared).
        - **No:** The citation is **FAKE** (AI "dreamed" the wrong authors for a real paper).

## 5. Bulk Text Handling Strategy (v3.3)
- **Symptom:** Input contains multiple references (e.g., 20 lines), but the tool reports `Total References: 1` (The "Blob Failure").
- **Cause:** Tool failed to recognize newline delimiters, treating the entire block as one long title.
- **Action:** **Split & Verify**.
    1.  Manually separate the references into smaller batches (or single items).
    2.  Run `verify_references` on the cleaned, separated chunks.
    3.  **Never** accept a "Not Found" verdict if the input text was a massive block.

## 3. Advanced Detection (v3.0)
- **"Frankenstein" Reference Check:**
    - Compare DOI metadata vs. Citation Text. Mismatch = **FAKE**.
- **"DOI Rot" Handling:**
    - If DOI fails but Title search succeeds (High Confidence): Report as **"Verified (DOI Broken/Migrated)"**.
    - Common in older journals where DOIs were restructured.

## 4. Reporting Standards
- **Distinguish Errors:** Separate "Technical/Parsing Failures" from "Content Hallucinations."
- **Verdict:**
    - High Parsing Failure Rate + Real Authors = **Likely Valid (Layout Issue)**.
    - 0 Matches + Unknown Authors = **Likely Fake**.