# ============================================================
# app/services/arxiv_service.py
# Midnight Scholar — arXiv API Integration
# Best for Science & Technology | Real Academic PDFs
# ============================================================

from app.core.http_client import async_http_client
import logging
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict
import time

logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"

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

# Namespaces for XML parsing
NS = {
    'atom': 'http://www.w3.org/2005/Atom',
    'arxiv': 'http://arxiv.org/schemas/atom'
}

def parse_arxiv_entry(entry: ET.Element) -> dict:
    """Parses an arXiv Atom entry into a Midnight Scholar book."""
    
    # Identifier (URL)
    id_url = entry.find('atom:id', NS).text
    identifier = id_url.split('/')[-1]
    
    # Title
    title = entry.find('atom:title', NS).text.strip().replace('\n', ' ')
    
    # Authors
    authors = [a.find('atom:name', NS).text for a in entry.findall('atom:author', NS)]
    author = ", ".join(authors[:2])
    
    # Summary/Description
    description = entry.find('atom:summary', NS).text.strip().replace('\n', ' ')
    
    # PDF Link
    pdf_url = ""
    for link in entry.findall('atom:link', NS):
        if link.get('title') == 'pdf':
            pdf_url = link.get('href')
        elif link.get('type') == 'application/pdf':
            pdf_url = link.get('href')

    # Categories
    categories = [c.get('term') for c in entry.findall('atom:category', NS)]
    primary_cat = entry.find('arxiv:primary_category', NS)
    category = primary_cat.get('term') if primary_cat is not None else (categories[0] if categories else "Science")

    # Map arXiv categories to human names
    cat_map = {
        "cs.AI": "Artificial Intelligence",
        "cs.LG": "Machine Learning",
        "cs.CV": "Computer Vision",
        "cs.CL": "Computation and Language",
        "cs.NE": "Neural Computing",
        "stat.ML": "Machine Learning",
        "physics.gen-ph": "General Physics",
        "math.AG": "Algebraic Geometry",
    }
    human_category = cat_map.get(category, category)

    return {
        "id": f"arxiv-{identifier}",
        "arxiv_id": identifier,
        "title": title,
        "author": author,
        "authors": authors,
        "description": description,
        "category": human_category,
        "subjects": categories,
        "cover_url": None, # arXiv has no covers, frontend handles fallback
        "cover_url_small": None,
        "pdf_url": pdf_url,
        "is_free": True,
        "is_premium": False,
        "source": "arXiv Academic",
        "published_year": entry.find('atom:published', NS).text[:4] if entry.find('atom:published', NS) is not None else None,
        "difficulty": "Advanced",
    }

async def search_arxiv_books(query: str, limit: int = 12, start: int = 0) -> dict:
    """Search arXiv for academic books and papers."""
    cache_key = f"arxiv_search:{query}:{limit}:{start}"
    cached = get_from_cache(cache_key)
    if cached: return cached

    # Clean query for arXiv (it prefers specific prefixes)
    # If no prefix, default to 'all'
    if ':' not in query:
        search_query = f"all:{query}"
    else:
        search_query = query

    params = {
        "search_query": search_query,
        "start": start,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending"
    }

    try:
        client = await async_http_client.get_client()
        response = await client.get(ARXIV_API_URL, params=params)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        entries = root.findall('atom:entry', NS)
        
        books = [parse_arxiv_entry(entry) for entry in entries]
        total_results_el = root.find('arxiv:totalResults', NS)
        total = int(total_results_el.text) if total_results_el is not None else len(books)

        result = {
            "results": books,
            "count": len(books),
            "total": total,
            "query": query,
            "source": "arXiv Academic"
        }
        set_to_cache(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"arXiv Search Error: {e}")
        return {"results": [], "count": 0, "total": 0, "error": str(e)}

async def get_arxiv_detail(identifier: str) -> dict:
    """Gets detailed info for a single arXiv item."""
    cache_key = f"arxiv_detail:{identifier}"
    cached = get_from_cache(cache_key)
    if cached: return cached

    params = {
        "id_list": identifier,
        "max_results": 1
    }
    
    client = await async_http_client.get_client()
    response = await client.get(ARXIV_API_URL, params=params)
    response.raise_for_status()
    
    root = ET.fromstring(response.text)
    entry = root.find('atom:entry', NS)
    
    if entry is None:
        raise Exception(f"arXiv item not found: {identifier}")
        
    result = parse_arxiv_entry(entry)
    set_to_cache(cache_key, result)
    return result
