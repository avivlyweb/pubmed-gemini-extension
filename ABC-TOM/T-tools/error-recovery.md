# Error Recovery Guide

## 1. File Not Found / Path Errors
**Symptom:** Tool returns "File not found" or "Path does not exist."
**Fix:**
1. Run `ls -R` or `glob` to find the actual file location.
2. Construct the **Absolute Path**.
3. Retry the tool with the corrected path.

## 2. Tool NameError / Namespace Issues
**Symptom:** `NameError: name 'search_pubmed' is not defined`.
**Fix:**
1. Check the currently available tools via `help` or internal context.
2. If `ext.pubmed.search` fails, try `enhanced_pubmed_search` (or vice versa).
3. **Fallback:** If tool fails completely, use `google_web_search` to approximate the result and explain the limitation.

## 3. "0 Results Found" (Discovery Failure)
**Symptom:** Search returns empty list.
**Fix:**
1. **Broaden:** Remove specific terms (e.g., specific drug dosage) and keep the core concepts.
2. **Semantic:** Use synonyms (e.g., "Heart Failure" -> "Cardiac Failure").
3. **Split:** Break one complex query into two simple queries.

## 4. API Rate Limits
**Symptom:** "Too many requests" or "429 Error."
**Fix:**
1. **Pause:** Wait 2-3 seconds.
2. **Simplify:** Request fewer results (`max_results=5` instead of `20`).
3. **Notify:** Tell the user: "I am hitting rate limits. Slowing down slightly to ensure accuracy."
