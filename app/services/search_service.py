"""
Search Service — Full-Text PDF Search
========================================
Searches across extracted PDF text to return page-level matches.
"""

import httpx
import os
import json
import tempfile
from typing import List, Dict
from app.services.pdf_parser import extract_text_from_pdf

CACHE_DIR = "data/text_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

async def search_in_book(pdf_path_or_url: str, query: str) -> List[Dict]:
    """Search for a query string across all pages of a PDF (handles URLs)."""
    
    # 1. Check Cache
    cache_key = pdf_path_or_url.split("/")[-1].replace(".pdf", ".json")
    cache_path = os.path.join(CACHE_DIR, cache_key)
    
    pages = []
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            pages = json.load(f)
    else:
        # 2. Extract (Download if URL)
        target_path = pdf_path_or_url
        is_temp = False
        
        if pdf_path_or_url.startswith("http"):
            is_temp = True
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(pdf_path_or_url)
                    tmp.write(resp.content)
                    target_path = tmp.name
        
        pages = extract_text_from_pdf(target_path)
        
        # Save to cache
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(pages, f)
            
        if is_temp and os.path.exists(target_path):
            os.remove(target_path)

    # 3. Search in extracted text
    results = []
    query_lower = query.lower()

    for page in pages:
        text = page.get("text", "")
        if query_lower in text.lower():
            idx = text.lower().index(query_lower)
            start = max(0, idx - 80)
            end = min(len(text), idx + len(query) + 80)
            snippet = text[start:end].replace("\n", " ")

            results.append({
                "page_number": page["page_number"],
                "snippet": f"...{snippet}...",
                "relevance": text.lower().count(query_lower),
            })

    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results[:20] # Return top 20 matches
