"""
Search Service — Full-Text PDF Search
========================================
Searches across extracted PDF text to return page-level matches.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict

from app.services.pdf_parser import extract_text_from_pdf


async def search_in_book(pdf_path: str, query: str) -> List[Dict]:
    """Search for a query string across all pages of a PDF."""
    pages = extract_text_from_pdf(pdf_path)
    results = []
    query_lower = query.lower()

    for page in pages:
        if query_lower in page["text"].lower():
            # Find snippet around the match
            idx = page["text"].lower().index(query_lower)
            start = max(0, idx - 100)
            end = min(len(page["text"]), idx + len(query) + 100)
            snippet = page["text"][start:end]

            results.append({
                "page_number": page["page_number"],
                "snippet": f"...{snippet}...",
                "relevance": page["text"].lower().count(query_lower),
            })

    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results
