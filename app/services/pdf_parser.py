"""
PDF Parser Service — Optional PyMuPDF
=======================================
Extracts raw text from PDFs. Disabled gracefully when pymupdf not installed.
"""

from typing import List, Dict

try:
    import fitz  # PyMuPDF
    _fitz_available = True
except ImportError:
    fitz = None
    _fitz_available = False


def extract_text_from_pdf(pdf_path: str) -> List[Dict]:
    """Extract text from every page of a PDF file."""
    if not _fitz_available:
        return []
    doc = fitz.open(pdf_path)
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        pages.append({
            "page_number": page_num + 1,
            "text": text.strip(),
            "char_count": len(text),
        })
    doc.close()
    return pages


def extract_single_page(pdf_path: str, page_number: int) -> str:
    """Extract text from a specific page."""
    if not _fitz_available:
        return ""
    doc = fitz.open(pdf_path)
    if page_number < 1 or page_number > len(doc):
        doc.close()
        return ""
    page = doc[page_number - 1]
    text = page.get_text("text")
    doc.close()
    return text.strip()


def get_total_pages(pdf_path: str) -> int:
    """Get the total number of pages in a PDF."""
    if not _fitz_available:
        return 0
    doc = fitz.open(pdf_path)
    count = len(doc)
    doc.close()
    return count
