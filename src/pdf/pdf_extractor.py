"""
PDF text extraction and cleaning module.

Extracts text from academic and general PDF files, handles hyphenated line
breaks, strips running headers and page numbers, and prepares the text for
clean TTS narration.
"""

import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Union

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


def parse_page_range(page_spec: Optional[str], total_pages: int) -> List[int]:
    """
    Parse a page range string (1-indexed) into a list of 0-indexed page indices.
    Examples:
        "1" -> [0]
        "1-3" -> [0, 1, 2]
        "1,3,5" -> [0, 2, 4]
        None -> [0, 1, ..., total_pages - 1]
    """
    if not page_spec:
        return list(range(total_pages))

    pages = set()
    parts = page_spec.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start = max(1, int(start_str.strip()))
            end = min(total_pages, int(end_str.strip()))
            for p in range(start, end + 1):
                pages.add(p - 1)
        else:
            p = int(part)
            if 1 <= p <= total_pages:
                pages.add(p - 1)

    return sorted(list(pages))


def clean_pdf_extracted_text(text: str, skip_references: bool = True) -> str:
    """
    Clean raw text extracted from a PDF:
    - Joins words broken across lines by hyphens (e.g., 'substruc-\\nture' -> 'substructure')
    - Removes arXiv headers, journal stamps, and URLs
    - Strips isolated page numbers and headers/footers
    - Unwraps column-wrapped lines into coherent paragraphs
    - Optionally strips bibliography / references sections
    """
    # 1. Optionally strip references/bibliography
    if skip_references:
        ref_match = re.search(
            r'\n\s*(?:(?:[IVXLCDM]+\.?\s+)?(?:REFERENCES|BIBLIOGRAPHY))\s*\n',
            text,
            flags=re.IGNORECASE,
        )
        if ref_match:
            text = text[: ref_match.start()]

    # 2. Strip running arXiv stamp lines (e.g. arXiv:1909.07346v1 [astro-ph.CO] 16 Sep 2019)
    text = re.sub(r'arXiv:\d+\.\d+(?:v\d+)?\s*\[.*?\]\s*\d+\s+[A-Za-z]+\s+\d+', '', text)
    text = re.sub(r'arXiv:\d+\.\d+(?:v\d+)?', '', text)

    # 3. Strip standalone page numbers
    text = re.sub(r'^[ \t]*\d+[ \t]*$', '', text, flags=re.MULTILINE)

    # 4. Rejoin words split by hyphenation at line breaks
    text = re.sub(r'(\b[a-zA-Z]{2,})-\n\s*([a-zA-Z]{2,}\b)', r'\1\2', text)

    # 5. Fix author footnote dagger/star marks often found in paper headers
    text = re.sub(r'[,∗†‡1-9]+\s*(and|,)\s*', r'\1 ', text)

    # 6. Unwrap column line breaks inside paragraphs
    lines = text.split("\n")
    reconstructed_paras = []
    current_para = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_para:
                reconstructed_paras.append(" ".join(current_para))
                current_para = []
        else:
            if re.match(r'^(?:[IVXLCDM]+\.|\d+\.)\s+[A-Z\s]{3,}$', stripped):
                if current_para:
                    reconstructed_paras.append(" ".join(current_para))
                    current_para = []
                reconstructed_paras.append(stripped)
            else:
                current_para.append(stripped)

    if current_para:
        reconstructed_paras.append(" ".join(current_para))

    return "\n\n".join(reconstructed_paras)


def extract_text_from_pdf(
    pdf_path: Union[str, Path],
    page_range: Optional[str] = None,
    skip_references: bool = True,
) -> str:
    """
    Extract text from a PDF file using pdftotext (poppler) if available,
    falling back to pypdf.

    Args:
        pdf_path: Path to the .pdf file.
        page_range: Optional range specification (e.g. "1", "1-3", "2,4").
        skip_references: If True, strips the references section.

    Returns:
        str: Cleaned extracted text.
    """
    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    raw_text = ""

    # Prefer pdftotext if available because poppler has excellent LaTeX ligature font mapping
    has_pdftotext = shutil.which("pdftotext") is not None

    if has_pdftotext:
        cmd = ["pdftotext"]
        if page_range:
            parts = page_range.split("-")
            first = parts[0].strip()
            last = parts[-1].strip()
            if first.isdigit():
                cmd.extend(["-f", first])
            if last.isdigit():
                cmd.extend(["-l", last])
        cmd.extend([str(pdf_path), "-"])
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            raw_text = res.stdout
        except subprocess.SubprocessError:
            raw_text = ""

    # Fallback to pypdf if pdftotext failed or is absent
    if not raw_text and PYPDF_AVAILABLE:
        reader = PdfReader(str(pdf_path))
        total_pages = len(reader.pages)
        pages_to_extract = parse_page_range(page_spec=page_range, total_pages=total_pages)
        page_texts = []
        for p_idx in pages_to_extract:
            page = reader.pages[p_idx]
            page_texts.append(page.extract_text() or "")
        raw_text = "\n\n".join(page_texts)

    cleaned = clean_pdf_extracted_text(raw_text, skip_references=skip_references)
    return cleaned
