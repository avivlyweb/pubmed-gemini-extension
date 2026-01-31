"""
Document Parser - Extract text from PDF, DOCX, and plain text files.

Supports:
- PDF extraction using PyMuPDF (fitz)
- DOCX extraction using python-docx
- Plain text (.txt) files

This module extracts the references section and splits into individual entries.
"""

import re
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from pathlib import Path


@dataclass
class DocumentContent:
    """Extracted content from a document."""
    file_path: str
    file_type: str  # "pdf", "docx", "txt"
    full_text: str
    references_section: str
    reference_entries: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)  # title, author if extractable
    extraction_warnings: List[str] = field(default_factory=list)


class DocumentParser:
    """
    Extract text from PDF, DOCX, or plain text files.
    Focuses on locating and parsing the references section.
    """
    
    # Headers that indicate the start of references section
    REFERENCE_HEADERS = [
        r"(?:^|\n)\s*references?\s*(?:\n|$)",
        r"(?:^|\n)\s*bibliography\s*(?:\n|$)",
        r"(?:^|\n)\s*works?\s+cited\s*(?:\n|$)",
        r"(?:^|\n)\s*literature\s+cited\s*(?:\n|$)",
        r"(?:^|\n)\s*cited\s+literature\s*(?:\n|$)",
        r"(?:^|\n)\s*sources?\s*(?:\n|$)",
    ]
    
    # Headers that indicate end of references (appendix, etc.)
    END_HEADERS = [
        r"(?:^|\n)\s*appendix",
        r"(?:^|\n)\s*appendices",
        r"(?:^|\n)\s*supplementary",
        r"(?:^|\n)\s*acknowledgements?",
        r"(?:^|\n)\s*author\s+contributions?",
        r"(?:^|\n)\s*conflict\s+of\s+interest",
        r"(?:^|\n)\s*funding",
        r"(?:^|\n)\s*ethics\s+statement",
    ]
    
    def __init__(self):
        self._fitz_available = None
        self._docx_available = None
    
    def _check_dependencies(self, file_type: str) -> Tuple[bool, str]:
        """Check if required dependencies are available."""
        if file_type == "pdf":
            if self._fitz_available is None:
                try:
                    import fitz
                    self._fitz_available = True
                except ImportError:
                    self._fitz_available = False
            if not self._fitz_available:
                return False, "PyMuPDF not installed. Run: pip install PyMuPDF"
            return True, ""
        
        elif file_type == "docx":
            if self._docx_available is None:
                try:
                    import docx
                    self._docx_available = True
                except ImportError:
                    self._docx_available = False
            if not self._docx_available:
                return False, "python-docx not installed. Run: pip install python-docx"
            return True, ""
        
        return True, ""
    
    def parse(self, file_path: str) -> DocumentContent:
        """
        Parse a document and extract references.
        
        Args:
            file_path: Path to PDF, DOCX, or TXT file
            
        Returns:
            DocumentContent with extracted text and references
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Determine file type
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            file_type = "pdf"
        elif suffix in [".docx", ".doc"]:
            file_type = "docx"
        elif suffix in [".txt", ".text", ".md"]:
            file_type = "txt"
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
        
        # Check dependencies
        available, error_msg = self._check_dependencies(file_type)
        if not available:
            raise ImportError(error_msg)
        
        # Extract text based on file type
        if file_type == "pdf":
            full_text, metadata = self._extract_pdf(file_path)
        elif file_type == "docx":
            full_text, metadata = self._extract_docx(file_path)
        else:
            full_text, metadata = self._extract_txt(file_path)
        
        # Find references section
        references_section, warnings = self._find_references_section(full_text)
        
        # Split into individual entries
        reference_entries = self._split_references(references_section)
        
        return DocumentContent(
            file_path=str(path.absolute()),
            file_type=file_type,
            full_text=full_text,
            references_section=references_section,
            reference_entries=reference_entries,
            metadata=metadata,
            extraction_warnings=warnings
        )
    
    def _extract_pdf(self, file_path: str) -> Tuple[str, dict]:
        """Extract text from PDF using PyMuPDF."""
        import fitz  # PyMuPDF
        
        metadata = {}
        text_parts = []
        
        doc = fitz.open(file_path)
        
        # Extract metadata
        pdf_metadata = doc.metadata
        if pdf_metadata:
            if pdf_metadata.get("title"):
                metadata["title"] = pdf_metadata["title"]
            if pdf_metadata.get("author"):
                metadata["author"] = pdf_metadata["author"]
        
        # Extract text from all pages
        for page in doc:
            text = page.get_text()
            text_parts.append(text)
        
        doc.close()
        
        full_text = "\n".join(text_parts)
        return full_text, metadata
    
    def _extract_docx(self, file_path: str) -> Tuple[str, dict]:
        """Extract text from DOCX using python-docx."""
        from docx import Document
        
        metadata = {}
        text_parts = []
        
        doc = Document(file_path)
        
        # Extract core properties as metadata
        try:
            core_props = doc.core_properties
            if core_props.title:
                metadata["title"] = core_props.title
            if core_props.author:
                metadata["author"] = core_props.author
        except Exception:
            pass  # Metadata extraction is optional
        
        # Extract text from paragraphs
        for para in doc.paragraphs:
            text_parts.append(para.text)
        
        # Also extract from tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text_parts.append(cell.text)
        
        full_text = "\n".join(text_parts)
        return full_text, metadata
    
    def _extract_txt(self, file_path: str) -> Tuple[str, dict]:
        """Extract text from plain text file."""
        metadata = {}
        
        # Try different encodings
        for encoding in ["utf-8", "utf-16", "latin-1", "cp1252"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    full_text = f.read()
                return full_text, metadata
            except UnicodeDecodeError:
                continue
        
        # Fallback with error handling
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            full_text = f.read()
        
        return full_text, metadata
    
    def _find_references_section(self, text: str) -> Tuple[str, List[str]]:
        """
        Find the references section in the document.
        
        Returns:
            Tuple of (references_text, warnings)
        """
        warnings = []
        text_lower = text.lower()
        
        # Find start of references section
        start_pos = -1
        for pattern in self.REFERENCE_HEADERS:
            match = re.search(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
            if match:
                # Use the position in original text
                start_pos = match.end()
                break
        
        if start_pos == -1:
            warnings.append("Could not locate References section header")
            # Try to find numbered references pattern as fallback
            numbered_match = re.search(r"\n\s*\[1\]|\n\s*1\.\s+[A-Z]", text)
            if numbered_match:
                start_pos = numbered_match.start()
                warnings.append("Using numbered reference pattern as fallback")
            else:
                # Return empty if we can't find references
                return "", warnings
        
        # Find end of references section
        end_pos = len(text)
        remaining_text = text[start_pos:].lower()
        
        for pattern in self.END_HEADERS:
            match = re.search(pattern, remaining_text, re.IGNORECASE | re.MULTILINE)
            if match:
                end_pos = start_pos + match.start()
                break
        
        references_section = text[start_pos:end_pos].strip()
        
        if not references_section:
            warnings.append("References section appears to be empty")
        
        return references_section, warnings
    
    def _split_references(self, refs_text: str) -> List[str]:
        """
        Split references section into individual entries.
        
        Handles:
        - Numbered references: [1], 1., (1)
        - APA style (author-date)
        - Hanging indent style
        """
        if not refs_text:
            return []
        
        entries = []
        
        # Try numbered patterns first: [1], [2], etc.
        numbered_bracket = re.split(r"\n\s*\[\d+\]\s*", refs_text)
        if len(numbered_bracket) > 2:
            entries = [e.strip() for e in numbered_bracket if e.strip()]
            return entries
        
        # Try numbered with period: 1., 2., etc.
        numbered_period = re.split(r"\n\s*\d+\.\s+", refs_text)
        if len(numbered_period) > 2:
            entries = [e.strip() for e in numbered_period if e.strip()]
            return entries
        
        # Try numbered in parentheses: (1), (2), etc.
        numbered_paren = re.split(r"\n\s*\(\d+\)\s*", refs_text)
        if len(numbered_paren) > 2:
            entries = [e.strip() for e in numbered_paren if e.strip()]
            return entries
        
        # Try splitting by blank lines (common in APA)
        blank_line_split = re.split(r"\n\s*\n", refs_text)
        if len(blank_line_split) > 1:
            entries = [e.strip() for e in blank_line_split if e.strip()]
            return entries
        
        # Try detecting APA author-year pattern at start of lines
        # Pattern: Author, A. A. (Year). or Author, A. A., & Author, B. B. (Year).
        apa_pattern = r"\n(?=[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?,\s+[A-Z]\.)"
        apa_split = re.split(apa_pattern, refs_text)
        if len(apa_split) > 1:
            entries = [e.strip() for e in apa_split if e.strip()]
            return entries
        
        # Fallback: split by lines that look like they start a new reference
        # (start with author name pattern)
        lines = refs_text.split("\n")
        current_entry = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_entry:
                    entries.append(" ".join(current_entry))
                    current_entry = []
            elif re.match(r"^[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?,", line):
                # Looks like start of new APA reference
                if current_entry:
                    entries.append(" ".join(current_entry))
                current_entry = [line]
            else:
                current_entry.append(line)
        
        if current_entry:
            entries.append(" ".join(current_entry))
        
        return entries
    
    def parse_batch(self, directory: str, pattern: str = "*.pdf") -> List[DocumentContent]:
        """
        Parse multiple documents from a directory.
        
        Args:
            directory: Directory path
            pattern: Glob pattern for files (default: "*.pdf")
            
        Returns:
            List of DocumentContent objects
        """
        from pathlib import Path
        
        dir_path = Path(directory)
        if not dir_path.is_dir():
            raise ValueError(f"Not a directory: {directory}")
        
        results = []
        for file_path in dir_path.glob(pattern):
            try:
                content = self.parse(str(file_path))
                results.append(content)
            except Exception as e:
                # Create a failed result
                results.append(DocumentContent(
                    file_path=str(file_path),
                    file_type=file_path.suffix.lstrip("."),
                    full_text="",
                    references_section="",
                    reference_entries=[],
                    extraction_warnings=[f"Failed to parse: {str(e)}"]
                ))
        
        return results
