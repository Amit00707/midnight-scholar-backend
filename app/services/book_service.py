# ============================================================
# app/services/book_service.py
# Midnight Scholar — Unified Book Discovery Engine
# Aggregates: Open Library, Internet Archive, arXiv, Standard Ebooks
# ============================================================

import logging
import asyncio
import time
from typing import List, Dict, Optional

from app.services.open_library_service import search_books as ol_search, get_book_detail as ol_detail, get_books_by_category as ol_cat
from app.services.internet_archive_service import search_ia_books as ia_search, get_ia_book_detail as ia_detail
from app.services.arxiv_service import search_arxiv_books as arxiv_search, get_arxiv_detail as arxiv_detail
from app.services.standard_ebooks_service import search_standard_ebooks as se_search

logger = logging.getLogger(__name__)

# Cache settings
_cache: Dict[str, dict] = {}
CACHE_TTL = 1800 # 30 mins for mixed results

def get_from_cache(key: str):
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry['timestamp'] < CACHE_TTL:
            return entry['data']
        del _cache[key]
    return None

def set_to_cache(key: str, data: dict):
    _cache[key] = {'timestamp': time.time(), 'data': data}

async def unified_search(query: str, limit: int = 12, page: int = 1) -> dict:
    """
    Parallel search across multiple providers.
    """
    # Categories that trigger specific providers
    tech_keywords = ["python", "javascript", "react", "coding", "programming", "ai", "machine learning", "tech", "computer"]
    science_keywords = ["physics", "biology", "chemistry", "quantum", "astronomy", "research"]
    
    is_tech = any(k in query.lower() for k in tech_keywords)
    is_science = any(k in query.lower() for k in science_keywords)

    tasks = []
    
    # Always include Open Library and IA
    tasks.append(ol_search(query, limit=limit//2, page=page))
    tasks.append(ia_search(query, limit=limit//2, page=page))
    
    # Include arXiv for tech/science
    if is_tech or is_science:
        tasks.append(arxiv_search(query, limit=5))
        
    # Standard Ebooks for fiction/history
    if not is_tech:
        tasks.append(se_search(query, limit=5))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    combined = []
    total = 0
    
    for res in results:
        if isinstance(res, dict) and "results" in res:
            combined.extend(res["results"])
            total += res.get("total", len(res["results"]))
        elif isinstance(res, Exception):
            logger.error(f"Provider failed in unified search: {res}")

    # Deduplicate by title (simple)
    seen = set()
    final_results = []
    for b in combined:
        title_key = b["title"].lower().strip()
        if title_key not in seen:
            seen.add(title_key)
            final_results.append(b)
            if len(final_results) >= limit: break

    return {
        "results": final_results,
        "count": len(final_results),
        "total": total,
        "page": page,
        "query": query
    }

async def unified_get_book_detail(book_id: str) -> dict:
    """Route to correct provider based on ID prefix."""
    if book_id.startswith("ia-"):
        return await ia_detail(book_id.replace("ia-", ""))
    elif book_id.startswith("arxiv-"):
        return await arxiv_detail(book_id.replace("arxiv-", ""))
    elif book_id.startswith("se-"):
        # We don't have a direct SE detail API in our service yet, but we can search for it
        res = await se_search(book_id.replace("se-", ""), limit=1)
        if res["results"]: return res["results"][0]
        raise Exception("Book not found in Standard Ebooks")
    else:
        # Default to Open Library
        return await ol_detail(book_id)

async def unified_books_by_category(category: str, limit: int = 12) -> dict:
    """Smart category routing."""
    cat_lower = category.lower()
    cache_key = f"unified_cat:{cat_lower}:{limit}"
    cached = get_from_cache(cache_key)
    if cached: return cached
    
    if cat_lower == "all":
        # Return a rich mix of various disciplines
        tasks = [
            ol_cat("philosophy", limit=6),
            ol_cat("science", limit=6),
            ol_cat("history", limit=6),
            ol_cat("fiction", limit=6),
            ol_cat("technology", limit=6),
            ol_cat("psychology", limit=6),
            ol_cat("business", limit=6),
            ol_cat("biography", limit=6)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        combined = []
        for res in results:
            if isinstance(res, dict) and "results" in res:
                combined.extend(res["results"])
        
        import random
        random.shuffle(combined)
        
        result = {
            "results": combined[:limit],
            "category": "All",
            "count": len(combined)
        }
        set_to_cache(cache_key, result)
        return result
    
    if cat_lower in ["technology", "computers", "science"]:
        # Mix OL and arXiv
        ol_res = await ol_cat(category, limit=limit//2)
        arxiv_res = await arxiv_search(category, limit=limit//2)
        
        combined = ol_res.get("results", []) + arxiv_res.get("results", [])
        result = {
            "results": combined,
            "category": category,
            "count": len(combined)
        }
        set_to_cache(cache_key, result)
        return result
    elif cat_lower in ["fiction", "history", "philosophy"]:
        # Mix OL and IA
        ol_res = await ol_cat(category, limit=limit//2)
        ia_res = await ia_search(category, limit=limit//2)
        
        combined = ol_res.get("results", []) + ia_res.get("results", [])
        result = {
            "results": combined,
            "category": category,
            "count": len(combined)
        }
        set_to_cache(cache_key, result)
        return result
    else:
        result = await ol_cat(category, limit=limit)
        set_to_cache(cache_key, result)
        return result
