"""
PDF Parser Service — PyMuPDF Text Extraction
===============================================
Extracts raw text from PDF files page-by-page for AI processing.
"""

import fitz  # PyMuPDF
from typing import List, Dict


def extract_text_from_pdf(pdf_path: str) -> List[Dict]:
    """Extract text from every page of a PDF file."""
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
    doc = fitz.open(pdf_path)
    count = len(doc)
    doc.close()
    return count
