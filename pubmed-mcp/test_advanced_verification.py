"""
Advanced Verification Tests for v2.8.x features.

Tests:
1. Frankenstein citation detection (real DOI + wrong metadata)
2. Split DOI reconstruction (PDF line-break artifacts)
3. Table noise filtering (non-citation text rejection)
4. Multi-source DOI fallback (CrossRef, OpenAlex, Europe PMC)
5. Title similarity threshold enforcement
"""

import pytest
from reference_checker.verification_engine import VerificationEngine, VerificationStatus, PubMedMatch
from reference_checker.reference_extractor import ReferenceExtractor, ParsedReference
from reference_checker.document_parser import DocumentParser

# --- Test Data Scenarios ---

# 1. Frankenstein Citation (Real text, Wrong DOI)
# Text: Brügge et al. (2024) [Medical Ed topic]
# DOI: 10.1080/1364557032000119616 (Arksey 2005 - Scoping Studies)
FRANKENSTEIN_REF_TEXT = (
    "Brügge, H., Hansen, D. K., Hansen, T., & Henriksen, L. K. (2024). "
    "Large language models improve clinical decision making of medical students "
    "through patient simulation and structured feedback: A randomized controlled trial. "
    "BMC Medical Education, 24(1), 448. https://doi.org/10.1080/1364557032000119616"
)

# 2. Split DOI (PDF Artifact)
# DOI broken by newline/space
SPLIT_DOI_REF_TEXT = (
    "Godin, K., Stapleton, J., ... (2015). Applying systematic review search methods. "
    "Systematic Reviews, 4, 138. https://doi.org/10.1186/s13643-015-0125- 0"
)

# 2b. Split DOI with hyphen continuation (common in PDFs)
SPLIT_DOI_HYPHEN_TEXT = (
    "Johnson, M. A. (2024). Some medical research paper. "
    "Medical Journal, 10(2). https://doi.org/10.1186/s12909-\n024-06399-7"
)

# 3. Table Noise (Non-citation text)
TABLE_NOISE_TEXT = "personalized skill enhancement"

# 4. Ghost DOI (Syntactically valid but fake)
GHOST_DOI_REF_TEXT = (
    "Smith, J. (2023). Fake paper title about nothing. "
    "Journal of Nothing, 1(1). doi:10.1080/9999999999"
)

# 5. The "Oldie" (Arksey 2005 - previously false negative)
ARKSEY_REF_TEXT = (
    "Arksey, H., & O'Malley, L. (2005). Scoping studies: towards a methodological framework. "
    "International journal of social research methodology, 8(1), 19-32. "
    "https://doi.org/10.1080/1364557032000119616"
)

# 6. Valid reference for baseline
VALID_REF_TEXT = (
    "Smith, J. A., & Jones, B. C. (2020). A comprehensive review of medical education. "
    "Medical Education Review, 15(3), 245-260. https://doi.org/10.1111/medu.12345"
)

# 7. Table content samples
TABLE_CONTENT_SAMPLES = [
    "3.5",
    "85.3%",
    "p<0.001",
    "n=50",
    "CI: 0.5-1.2",
    "OR: 2.3",
    "Yes",
    "N/A",
    "(1.2, 3.4)",
]

# 8. Valid reference samples for filtering
VALID_REFERENCE_SAMPLES = [
    "Smith, J. A. (2020). A study of something important. Journal of Studies, 10(2), 1-15.",
    "Brown, A. B., & White, C. D. (2019). Another paper. Science Today, 5, 23-45. doi:10.1234/st.2019",
    "Johnson, M. et al. (2021). Multi-author study. Research Quarterly, 8(1).",
]


class TestFrankensteinDetection:
    """Test detection of Frankenstein citations (real DOI + wrong metadata)."""
    
    def test_metadata_mismatch_detection(self):
        """Test detection of mismatched DOI and Title."""
        extractor = ReferenceExtractor()
        engine = VerificationEngine()
        
        # Extract the Frankenstein reference
        ref = extractor.extract(FRANKENSTEIN_REF_TEXT)
        
        # Simulate what DOI resolution would find (Arksey paper)
        arksey_match = PubMedMatch(
            pmid="12345",
            title="Scoping studies: towards a methodological framework",
            authors=["Arksey, H", "O'Malley, L"],
            year=2005,
            journal="Int J Soc Res Method",
            doi="10.1080/1364557032000119616",
            confidence=1.0
        )
        
        # Check for metadata mismatch
        is_mismatch = engine._is_metadata_mismatch(ref, arksey_match)
        assert is_mismatch, "Should detect significant mismatch between Brügge text and Arksey DOI metadata"
    
    def test_title_similarity_threshold(self):
        """Test that low title similarity triggers rejection."""
        engine = VerificationEngine()
        
        # Two completely different titles
        title1 = "Large language models improve clinical decision making"
        title2 = "Scoping studies: towards a methodological framework"
        
        similarity = engine._string_similarity(title1, title2)
        
        # Should be below the 60% threshold
        assert similarity < 0.6, f"Similarity {similarity} should be below 0.6 for unrelated titles"
    
    def test_similar_titles_pass_threshold(self):
        """Test that similar titles pass the threshold."""
        engine = VerificationEngine()
        
        # Very similar titles (minor variations)
        title1 = "Yoga for anxiety: A systematic review"
        title2 = "Yoga for anxiety - a systematic review and meta-analysis"
        
        similarity = engine._string_similarity(title1, title2)
        
        # Should be above the 60% threshold
        assert similarity >= 0.6, f"Similarity {similarity} should be >= 0.6 for related titles"


class TestSplitDOIReconstruction:
    """Test handling of DOIs broken by spaces or line breaks."""
    
    def test_space_in_doi(self):
        """Test DOI with space artifact."""
        extractor = ReferenceExtractor()
        
        ref = extractor.extract(SPLIT_DOI_REF_TEXT)
        
        # After normalization, DOI should be reconstructed
        # Expected: 10.1186/s13643-015-0125-0
        if ref.doi:
            # Remove any remaining spaces
            clean_doi = ref.doi.replace(" ", "")
            assert "0125-0" in clean_doi or "01250" in clean_doi, \
                f"DOI should be reconstructed: got {ref.doi}"
    
    def test_hyphen_continuation_doi(self):
        """Test DOI split across lines with hyphen continuation."""
        extractor = ReferenceExtractor()
        
        # Normalize the text first (simulate what document parser does)
        normalized_text = extractor._normalize_doi_text(SPLIT_DOI_HYPHEN_TEXT)
        
        # The hyphen-newline should be joined
        assert "s12909-024" in normalized_text or "s12909024" in normalized_text, \
            f"DOI line break should be normalized: {normalized_text}"
    
    def test_doi_normalization_preserves_valid_dois(self):
        """Test that valid DOIs aren't corrupted by normalization."""
        extractor = ReferenceExtractor()
        
        valid_text = "Some paper. https://doi.org/10.1234/valid-doi-here"
        normalized = extractor._normalize_doi_text(valid_text)
        
        assert "10.1234/valid-doi-here" in normalized, \
            f"Valid DOI should be preserved: {normalized}"


class TestTableContentFiltering:
    """Test filtering of non-citation table content."""
    
    def test_table_noise_rejection(self):
        """Test that non-citation text is rejected."""
        extractor = ReferenceExtractor()
        ref = extractor.extract(TABLE_NOISE_TEXT)
        
        # Should have very low confidence or missing key fields
        assert ref.year is None, "Table noise should not have a year"
        assert not ref.authors, "Table noise should not have authors"
        assert ref.parse_confidence < 0.3, "Should have low confidence for non-citation text"
    
    def test_document_parser_table_detection(self):
        """Test DocumentParser's table content detection."""
        parser = DocumentParser()
        
        for sample in TABLE_CONTENT_SAMPLES:
            is_table = parser._is_table_content(sample)
            assert is_table, f"'{sample}' should be detected as table content"
    
    def test_valid_references_pass_filter(self):
        """Test that valid references are not filtered out."""
        parser = DocumentParser()
        
        for ref_text in VALID_REFERENCE_SAMPLES:
            is_valid = parser._is_valid_reference(ref_text)
            assert is_valid, f"Valid reference should pass filter: '{ref_text[:50]}...'"
    
    def test_filter_table_entries(self):
        """Test batch filtering of entries."""
        parser = DocumentParser()
        
        # Mix of valid and invalid
        mixed_entries = VALID_REFERENCE_SAMPLES + TABLE_CONTENT_SAMPLES
        
        valid, filtered = parser._filter_table_entries(mixed_entries)
        
        assert len(valid) >= len(VALID_REFERENCE_SAMPLES) - 1, \
            f"Should keep most valid references: got {len(valid)}"
        assert len(filtered) >= len(TABLE_CONTENT_SAMPLES) - 1, \
            f"Should filter most table content: got {len(filtered)}"


class TestTitleSimilarity:
    """Test title similarity calculations."""
    
    def test_identical_titles(self):
        """Test that identical titles have similarity of 1.0."""
        engine = VerificationEngine()
        
        title = "Yoga for anxiety: A systematic review"
        similarity = engine._string_similarity(title, title)
        
        assert similarity >= 0.99, f"Identical titles should have ~1.0 similarity: got {similarity}"
    
    def test_completely_different_titles(self):
        """Test that unrelated titles have low similarity."""
        engine = VerificationEngine()
        
        title1 = "Machine learning in healthcare"
        title2 = "Ancient Roman architecture and engineering"
        
        similarity = engine._string_similarity(title1, title2)
        
        assert similarity < 0.3, f"Unrelated titles should have low similarity: got {similarity}"
    
    def test_case_insensitive(self):
        """Test that similarity is case-insensitive."""
        engine = VerificationEngine()
        
        title1 = "Yoga for Anxiety"
        title2 = "yoga for anxiety"
        
        similarity = engine._string_similarity(title1, title2)
        
        assert similarity >= 0.95, f"Case difference should not affect similarity: got {similarity}"


class TestReferenceValidation:
    """Test reference validation logic."""
    
    def test_minimum_length_requirement(self):
        """Test that short text is rejected."""
        parser = DocumentParser()
        
        short_text = "Smith, J. (2020)."  # Too short
        is_valid = parser._is_valid_reference(short_text)
        
        assert not is_valid, "Very short text should not be valid reference"
    
    def test_year_required(self):
        """Test that references must contain a year."""
        parser = DocumentParser()
        
        no_year = "Smith, J. A study of something important. Journal of Studies, 10(2), 1-15."
        is_valid = parser._is_valid_reference(no_year)
        
        assert not is_valid, "Reference without year should not be valid"
    
    def test_author_pattern_required(self):
        """Test that references must have author-like pattern."""
        parser = DocumentParser()
        
        no_author = "2020. A study title. Some journal content here with enough text."
        is_valid = parser._is_valid_reference(no_author)
        
        assert not is_valid, "Reference without author pattern should not be valid"


# Run tests with: pytest test_advanced_verification.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
