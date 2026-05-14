# ============================================================
# app/services/internet_archive_service.py
# Midnight Scholar — Internet Archive API Integration
# 100% Free | High Reliability | Direct PDF Access
# ============================================================

from app.core.http_client import async_http_client
from typing import Optional, List, Dict
import time
import logging

logger = logging.getLogger(__name__)

IA_SEARCH_URL = "https://archive.org/advancedsearch.php"
IA_METADATA_URL = "https://archive.org/metadata"
IA_IMAGE_URL = "https://archive.org/services/img"
IA_DOWNLOAD_URL = "https://archive.org/download"

# Cache settings
_cache: Dict[str, dict] = {}
CACHE_TTL = 3600

def get_from_cache(key: str):
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry['timestamp'] < CACHE_TTL:
            return entry['data']
        del _cache[key]
    return None

def set_to_cache(key: str, data: dict):
    _cache[key] = {'timestamp': time.time(), 'data': data}

def get_ia_cover_url(identifier: str) -> str:
    """Returns the cover image URL for an IA identifier."""
    return f"{IA_IMAGE_URL}/{identifier}"

def get_ia_pdf_url(identifier: str) -> str:
    """Constructs a best-guess PDF URL. Metadata check is safer."""
    return f"{IA_DOWNLOAD_URL}/{identifier}/{identifier}.pdf"

def parse_ia_book(item: dict) -> dict:
    """Parses an Internet Archive doc into a Midnight Scholar book."""
    identifier = item.get("identifier")
    creator = item.get("creator")
    if isinstance(creator, list):
        author = ", ".join(creator[:2])
        authors = creator
    else:
        author = creator or "Unknown Author"
        authors = [author]

    # Categories
    subjects = item.get("subject", [])
    if isinstance(subjects, str):
        subjects = [subjects]
    category = subjects[0] if subjects else "General"

    return {
        "id": f"ia-{identifier}",
        "ia_id": identifier,
        "title": item.get("title", "Unknown Title"),
        "author": author,
        "authors": authors,
        "description": item.get("description", ""),
        "category": category,
        "subjects": subjects[:5],
        "cover_url": get_ia_cover_url(identifier),
        "cover_url_small": get_ia_cover_url(identifier),
        "pdf_url": get_ia_pdf_url(identifier),
        "is_free": True,
        "is_premium": False,
        "source": "Internet Archive",
        "published_year": item.get("publicdate", "")[:4] if item.get("publicdate") else None,
        "difficulty": "Intermediate",
    }

async def search_ia_books(query: str, limit: int = 12, page: int = 1) -> dict:
    """Search IA for books with PDFs."""
    cache_key = f"ia_search:{query}:{limit}:{page}"
    cached = get_from_cache(cache_key)
    if cached: return cached

    # Build query: filter for texts and PDFs
    search_query = f"mediatype:texts AND format:pdf AND ({query})"
    
    params = {
        "q": search_query,
        "fl[]": ["identifier", "title", "creator", "description", "subject", "publicdate"],
        "rows": limit,
        "page": page,
        "output": "json"
    }

    try:
        client = await async_http_client.get_client()
        response = await client.get(IA_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        docs = data.get("response", {}).get("docs", [])
        books = [parse_ia_book(doc) for doc in docs]
        total = data.get("response", {}).get("numFound", 0)
        
        result = {
            "results": books,
            "count": len(books),
            "total": total,
            "page": page,
            "total_pages": -(-total // limit) if total else 0,
            "query": query,
            "source": "Internet Archive"
        }
        set_to_cache(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"Internet Archive Search Error: {e}")
        return {"results": [], "count": 0, "total": 0, "error": str(e)}

async def get_ia_book_detail(identifier: str) -> dict:
    """Gets detailed metadata and file list for an IA item."""
    cache_key = f"ia_detail:{identifier}"
    cached = get_from_cache(cache_key)
    if cached: return cached

    url = f"{IA_METADATA_URL}/{identifier}"
    
    try:
        client = await async_http_client.get_client()
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        
        metadata = data.get("metadata", {})
        files = data.get("files", [])
        
        # Find the best PDF file
        pdf_file = None
        for f in files:
            if f.get("format") == "Text PDF" or (f.get("name", "").lower().endswith(".pdf") and "bw.pdf" not in f.get("name", "").lower()):
                pdf_file = f.get("name")
                break
        
        if not pdf_file:
            for f in files:
                if f.get("name", "").lower().endswith(".pdf"):
                    pdf_file = f.get("name")
                    break
        
        pdf_url = f"{IA_DOWNLOAD_URL}/{identifier}/{pdf_file}" if pdf_file else None
        
        # Clean up metadata
        creator = metadata.get("creator")
        if isinstance(creator, list):
            author = ", ".join(creator[:2])
            authors = creator
        else:
            author = creator or "Unknown Author"
            authors = [author]

        subjects = metadata.get("subject", [])
        if isinstance(subjects, str):
            subjects = [subjects]

        result = {
            "id": f"ia-{identifier}",
            "ia_id": identifier,
            "title": metadata.get("title", "Unknown Title"),
            "author": author,
            "authors": authors,
            "description": metadata.get("description", ""),
            "category": subjects[0] if subjects else "General",
            "subjects": subjects[:10],
            "cover_url": get_ia_cover_url(identifier),
            "pdf_url": pdf_url,
            "is_free": True,
            "is_premium": False,
            "source": "Internet Archive",
            "published_date": metadata.get("publicdate"),
            "publisher": metadata.get("publisher"),
        }
        set_to_cache(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"Internet Archive Detail Error: {e}")
        raise e
