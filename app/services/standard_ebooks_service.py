# ============================================================
# app/services/standard_ebooks_service.py
# Midnight Scholar — Standard Ebooks API Integration
# Best for High-Quality Public Domain Fiction
# ============================================================

from app.core.http_client import async_http_client
import logging
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict
import time

logger = logging.getLogger(__name__)

SE_OPDS_URL = "https://standardebooks.org/opds/all"
SE_BASE_URL = "https://standardebooks.org"

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

# Namespaces for OPDS (Atom)
NS = {
    'atom': 'http://www.w3.org/2005/Atom',
    'dc': 'http://purl.org/dc/terms/'
}

def parse_se_entry(entry: ET.Element) -> dict:
    """Parses a Standard Ebooks OPDS entry."""
    
    id_url = entry.find('atom:id', NS).text
    identifier = id_url.split('/')[-1]
    
    title = entry.find('atom:title', NS).text
    
    # Author
    author_el = entry.find('atom:author', NS)
    author = author_el.find('atom:name', NS).text if author_el is not None else "Unknown"
    
    # Description
    description = entry.find('atom:content', NS).text if entry.find('atom:content', NS) is not None else ""
    
    # Links
    cover_url = ""
    pdf_url = ""
    epub_url = ""
    
    for link in entry.findall('atom:link', NS):
        rel = link.get('rel')
        type = link.get('type')
        href = link.get('href')
        
        if "image" in type and "thumbnail" not in rel:
            cover_url = f"{SE_BASE_URL}{href}" if href.startswith("/") else href
        elif "pdf" in type:
            pdf_url = f"{SE_BASE_URL}{href}" if href.startswith("/") else href
        elif "epub" in type:
            epub_url = f"{SE_BASE_URL}{href}" if href.startswith("/") else href

    # Categories
    categories = [c.get('term') for c in entry.findall('atom:category', NS)]
    category = categories[0] if categories else "Fiction"

    return {
        "id": f"se-{identifier}",
        "se_id": identifier,
        "title": title,
        "author": author,
        "authors": [author],
        "description": description,
        "category": category,
        "subjects": categories[:5],
        "cover_url": cover_url,
        "pdf_url": pdf_url,
        "epub_url": epub_url,
        "is_free": True,
        "is_premium": False,
        "source": "Standard Ebooks",
        "difficulty": "Intermediate",
    }

async def get_latest_standard_ebooks(limit: int = 12) -> dict:
    """Fetches the latest ebooks from Standard Ebooks."""
    cache_key = f"se_latest:{limit}"
    cached = get_from_cache(cache_key)
    if cached: return cached

    try:
        client = await async_http_client.get_client()
        response = await client.get(SE_OPDS_URL)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        entries = root.findall('atom:entry', NS)
        
        books = [parse_se_entry(entry) for entry in entries[:limit]]
        
        result = {
            "results": books,
            "count": len(books),
            "source": "Standard Ebooks"
        }
        set_to_cache(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"Standard Ebooks OPDS Error: {e}")
        return {"results": [], "count": 0, "error": str(e)}

async def search_standard_ebooks(query: str, limit: int = 12) -> dict:
    """
    Standard Ebooks doesn't have a public search API, 
    but we can filter the OPDS feed (limited to what's in the feed).
    """
    cache_key = f"se_search:{query}:{limit}"
    cached = get_from_cache(cache_key)
    if cached: return cached

    try:
        client = await async_http_client.get_client()
        response = await client.get(SE_OPDS_URL)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        entries = root.findall('atom:entry', NS)
        
        query_lower = query.lower()
        matches = []
        for entry in entries:
            title = entry.find('atom:title', NS).text.lower()
            if query_lower in title:
                matches.append(parse_se_entry(entry))
                if len(matches) >= limit: break
        
        result = {
            "results": matches,
            "count": len(matches),
            "source": "Standard Ebooks"
        }
        set_to_cache(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"Standard Ebooks Search Error: {e}")
        return {"results": [], "count": 0}
