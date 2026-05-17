# ============================================================
# app/services/open_library_service.py
# Midnight Scholar — Open Library API Integration
# 100% Free | No API Key | No Card | No Limits
# ============================================================

from app.core.http_client import async_http_client
from typing import Optional, Dict
import time
import logging
import httpx

logger = logging.getLogger(__name__)

OPEN_LIBRARY_BASE    = "https://openlibrary.org"
OPEN_LIBRARY_SEARCH  = "https://openlibrary.org/search.json"
OPEN_LIBRARY_COVERS  = "https://covers.openlibrary.org/b"
GUTENDEX_BASE        = "https://gutendex.com/books"

# Simple In-Memory Cache (TTL: 1 Hour)
_cache: Dict[str, dict] = {}
CACHE_TTL = 3600  # 1 hour

def get_from_cache(key: str):
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry['timestamp'] < CACHE_TTL:
            return entry['data']
        del _cache[key]
    return None

def set_to_cache(key: str, data: dict):
    _cache[key] = {
        'timestamp': time.time(),
        'data': data
    }


# ─────────────────────────────────────────
# HELPER: Build cover image URL
# ─────────────────────────────────────────
def get_cover_url(cover_id: Optional[int] = None,
                  isbn: Optional[str] = None,
                  size: str = "L") -> str:
    """
    Size options: S (small), M (medium), L (large)
    Priority: cover_id first, then isbn
    """
    if cover_id:
        return f"{OPEN_LIBRARY_COVERS}/id/{cover_id}-{size}.jpg"
    if isbn:
        return f"{OPEN_LIBRARY_COVERS}/isbn/{isbn}-{size}.jpg"
    # Return None so frontend can use its own beautiful fallback
    return None


# ─────────────────────────────────────────
# HELPER: Parse raw book item
# ─────────────────────────────────────────
def parse_book(item: dict) -> dict:
    """
    Parses a single Open Library search result item
    into a clean Midnight Scholar book object
    """
    # Get cover
    cover_id  = item.get("cover_i")
    isbn_list = item.get("isbn", [])
    isbn      = isbn_list[0] if isbn_list else None

    # Get author
    authors = item.get("author_name", ["Unknown Author"])
    author  = ", ".join(authors[:2])  # Max 2 authors shown

    # Get category/subject
    subjects  = item.get("subject", [])
    category  = subjects[0].title() if subjects else "General"

    # Estimate difficulty from page count
    page_count = item.get("number_of_pages_median", 0)
    if page_count < 150:
        difficulty = "Beginner"
    elif page_count < 350:
        difficulty = "Intermediate"
    else:
        difficulty = "Advanced"

    # Estimate reading time (avg 2 min per page)
    reading_minutes = page_count * 2
    reading_hours   = round(reading_minutes / 60, 1)

    # Check for Internet Archive ID (for reading)
    ia_ids = item.get("ia", [])
    ia_id  = ia_ids[0] if ia_ids else None
    
    # Check if readable
    has_fulltext = item.get("has_fulltext", False)

    return {
        "id":              item.get("key", "").replace("/works/", ""),
        "open_library_id": item.get("key", ""),
        "title":           item.get("title", "Unknown Title"),
        "author":          author,
        "authors":         authors,
        "description":     item.get("first_sentence", {}).get("value", "")
                           if isinstance(item.get("first_sentence"), dict)
                           else item.get("first_sentence", ""),
        "category":        category,
        "subjects":        subjects[:5],
        "cover_url":       get_cover_url(cover_id, isbn, size="L"),
        "cover_url_small": get_cover_url(cover_id, isbn, size="M"),
        "page_count":      page_count,
        "difficulty":      difficulty,
        "reading_time":    f"{reading_hours}h" if reading_hours >= 1
                           else f"{reading_minutes}min",
        "reading_minutes": reading_minutes,
        "isbn":            isbn,
        "language":        item.get("language", ["eng"])[0]
                           if item.get("language") else "eng",
        "published_year":  item.get("first_publish_year"),
        "publisher":       item.get("publisher", ["Unknown"])[0]
                           if item.get("publisher") else "Unknown",
        "rating":          round(item.get("ratings_average", 0), 1),
        "rating_count":    item.get("ratings_count", 0),
        "ia_id":           ia_id,
        "pdf_url":         f"https://archive.org/download/{ia_id}/{ia_id}.pdf" if ia_id else None,
        "has_fulltext":    has_fulltext or bool(ia_id),
        "is_free":         True,   # Open Library = always free
        "is_premium":      False,
    }


# ─────────────────────────────────────────
# 1. SEARCH BOOKS
# Used by: Smart Search page, Navbar search
# ─────────────────────────────────────────
async def search_books(query: str,
                       limit: int = 12,
                       page: int = 1) -> dict:
    """
    Search by title, author, subject, or ISBN
    GET /api/books/search?q=atomic+habits&limit=12&page=1
    """
    cache_key = f"search:{query}:{limit}:{page}"
    cached = get_from_cache(cache_key)
    if cached: return cached

    offset = (page - 1) * limit
    client = await async_http_client.get_client()
    
    response = await client.get(
        OPEN_LIBRARY_SEARCH,
        params={
            "q":      query,
            "limit":  limit,
            "offset": offset,
            "fields": "key,title,author_name,cover_i,isbn,"
                        "subject,first_publish_year,number_of_pages_median,"
                        "ratings_average,ratings_count,language,publisher,"
                        "first_sentence,ia,has_fulltext",
        }
    )
    data = response.json()

    books      = [parse_book(item) for item in data.get("docs", [])]
    total      = data.get("numFound", 0)
    total_pages = -(-total // limit)  # Ceiling division

    result = {
        "results":     books,
        "count":       len(books),
        "total":       total,
        "page":        page,
        "total_pages": total_pages,
        "query":       query,
    }
    set_to_cache(cache_key, result)
    return result


# ─────────────────────────────────────────
# 2. SEARCH BY AUTHOR
# Used by: Author Profile page
# ─────────────────────────────────────────
async def search_by_author(author_name: str,
                            limit: int = 12) -> dict:
    """
    GET /api/books/author?name=james+clear
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            OPEN_LIBRARY_SEARCH,
            params={
                "author": author_name,
                "limit":  limit,
                "fields": "key,title,author_name,cover_i,isbn,"
                          "subject,first_publish_year,number_of_pages_median,"
                          "ratings_average,ratings_count",
            }
        )
        data = response.json()

    books = [parse_book(item) for item in data.get("docs", [])]
    return {
        "results": books,
        "author":  author_name,
        "count":   len(books),
    }


# ─────────────────────────────────────────
# 3. GET BOOKS BY CATEGORY
# Used by: Dashboard rows, Category pages
# ─────────────────────────────────────────
async def get_books_by_category(category: str, limit: int = 12) -> dict:
    """
    GET /api/books/category/{category}
    Returns books for a specific subject
    """
    cache_key = f"category:{category}:{limit}"
    cached = get_from_cache(cache_key)
    if cached: return cached

    # Map user-friendly category names to Open Library subjects
    category_map = {
        "philosophy": "philosophy",
        "science": "science",
        "history": "history",
        "technology": "computers",
        "business": "business",
        "psychology": "psychology",
        "fantasy": "fantasy",
        "fiction": "fiction",
        "biography": "biography",
        "self-help": "self-help",
        "social media": "communication",
        "education": "education",
        "classroom": "education",
        "academic": "education"
    }

    subject = category_map.get(category.lower(), category)
    client = await async_http_client.get_client()
    
    response = await client.get(
        OPEN_LIBRARY_SEARCH,
        params={
            "q":       f"subject:{subject}",
            "limit":   limit,
            "sort":    "new",
            "fields":  "key,title,author_name,cover_i,isbn,"
                        "subject,first_publish_year,number_of_pages_median,"
                        "ratings_average,ratings_count,ia,has_fulltext",
        }
    )
    data = response.json()

    books = [parse_book(item) for item in data.get("docs", [])]
    result = {
        "results":  books,
        "category": category,
        "total":    data.get("numFound", len(books)),
    }
    set_to_cache(cache_key, result)
    return result


# ─────────────────────────────────────────
# 4. GET SINGLE BOOK DETAIL
# Used by: Book Details page
# ─────────────────────────────────────────
async def get_book_detail(work_id: str) -> dict:
    """
    GET /api/books/{id}
    Handles both Open Library IDs (OL...) and Gutendex IDs (numeric)
    """
    cache_key = f"book_detail:{work_id}"
    cached = get_from_cache(cache_key)
    if cached: return cached

    client = await async_http_client.get_client()

    # 1. Handle Gutendex (Numeric) IDs for real PDFs
    if work_id.isdigit():
        try:
            res = await client.get(f"{GUTENDEX_BASE}/{work_id}")
            if res.status_code == 200:
                item = res.json()
                formats = item.get("formats", {})
                authors = [a.get("name", "Unknown") for a in item.get("authors", [])]
                result = {
                    "id":          work_id,
                    "title":       item.get("title", "Unknown Title"),
                    "author":      ", ".join(authors),
                    "authors":     authors,
                    "description": f"A classic work from Project Gutenberg. Subjects: {', '.join(item.get('subjects', []))}",
                    "subjects":    item.get("subjects", [])[:10],
                    "category":    item.get("subjects", ["Classic"])[0] if item.get("subjects") else "Classic",
                    "cover_url":   formats.get("image/jpeg", ""),
                    "cover_url_small": formats.get("image/jpeg", ""),
                    "pdf_url":     formats.get("application/pdf", ""),
                    "is_free":     True,
                    "is_premium":  False,
                }
                set_to_cache(cache_key, result)
                return result
        except Exception: pass

    # 2. Handle Open Library IDs
    # Get work details
    work_res = await client.get(f"{OPEN_LIBRARY_BASE}/works/{work_id}.json")
    if work_res.status_code != 200:
        raise Exception(f"Open Library Work not found: {work_id}")
    work = work_res.json()

    # Get author details
    author_keys = work.get("authors", [])
    authors = []
    for a in author_keys[:2]:
        author_key = a.get("author", {}).get("key", "")
        if author_key:
            try:
                author_res = await client.get(f"{OPEN_LIBRARY_BASE}{author_key}.json")
                author_data = author_res.json()
                authors.append({
                    "name": author_data.get("name", "Unknown"),
                    "bio":  author_data.get("bio", {}).get("value", "") if isinstance(author_data.get("bio"), dict) else author_data.get("bio", ""),
                })
            except Exception: pass

    # Try to find IA ID and Cover info (Aggressive search)
    ia_id = None
    fallback_cover_id = None
    fallback_isbn = None
    
    try:
        # 1. Search for editions of this work to get more metadata
        work_key = f"/works/{work_id}" if not work_id.startswith("/") else work_id
        ed_res = await client.get(
            OPEN_LIBRARY_SEARCH,
            params={"work": work_key, "limit": 20, "fields": "ia,has_fulltext,cover_i,isbn"}
        )
        if ed_res.status_code == 200:
            ed_data = ed_res.json()
            # Sort by having IA ID
            docs = sorted(ed_data.get("docs", []), key=lambda d: len(d.get("ia", [])), reverse=True)
            for doc in docs:
                # Get IA ID if available
                if not ia_id:
                    ia_list = doc.get("ia", [])
                    if ia_list: 
                        # Prefer IDs that don't look like tokens or internal hashes
                        ia_id = next((id for id in ia_list if len(id) > 5), ia_list[0])
                
                # Get Cover ID if available
                if not fallback_cover_id:
                    fallback_cover_id = doc.get("cover_i")
                
                # Get ISBN if available
                if not fallback_isbn:
                    isbn_list = doc.get("isbn", [])
                    if isbn_list: fallback_isbn = isbn_list[0]
        
        # 2. If still no IA ID, try a more specific search by title and "Internet Archive"
        if not ia_id:
            search_res = await client.get(
                OPEN_LIBRARY_SEARCH,
                params={
                    "q": f'"{work.get("title")}" author:"{authors[0].get("name") if authors else ""}"',
                    "limit": 5,
                    "fields": "ia,has_fulltext,cover_i,isbn"
                }
            )
            if search_res.status_code == 200:
                search_data = search_res.json()
                for doc in search_data.get("docs", []):
                    if not ia_id:
                        ia_list = doc.get("ia", [])
                        if ia_list: ia_id = ia_list[0]
    except Exception as e:
        logger.error(f"Aggressive metadata search failed: {e}")
    
    # 3. Last Resort: Common Hardcoded IDs for Demo Popularity
    if not ia_id:
        title_norm = work.get("title", "").lower()
        if "atomic habits" in title_norm:
            ia_id = "atomichabitseasy0000clea"
        elif "deep work" in title_norm:
            ia_id = "deep-work-rules-for-focused-success-in-a-distracted-world-cal-newport"
        elif "think and grow rich" in title_norm:
            ia_id = "think-and-grow-rich-napoleon-hill"

    desc = work.get("description", "")
    if isinstance(desc, dict): desc = desc.get("value", "")
    subjects = work.get("subjects", [])
    covers   = work.get("covers", [])
    cover_id = covers[0] if covers else None

    result = {
        "id":          work_id,
        "title":       work.get("title", "Unknown Title"),
        "author":      ", ".join([a.get("name", "") for a in authors]) if authors else "Unknown Author",
        "authors":     [a.get("name", "") for a in authors],
        "description": desc,
        "subjects":    subjects[:10],
        "category":    subjects[0].title() if subjects else "General",
        "cover_url":   get_cover_url(cover_id or fallback_cover_id, isbn=fallback_isbn, size="L"),
        "cover_url_small": get_cover_url(cover_id or fallback_cover_id, isbn=fallback_isbn, size="M"),
        "ia_id":       ia_id,
        "pdf_url":     f"https://archive.org/download/{ia_id}/{ia_id}.pdf" if ia_id else None,
        "has_fulltext": bool(ia_id),
        "is_free":     True,
        "is_premium":  False,
        "difficulty":  "Advanced" if "science" in str(subjects).lower() else "Intermediate",
    }
    set_to_cache(cache_key, result)
    return result


# ─────────────────────────────────────────
# 5. GET TRENDING / POPULAR BOOKS
# Used by: Dashboard "Popular Books" row
# ─────────────────────────────────────────
async def get_trending_books(limit: int = 12) -> dict:
    """
    GET /api/books/trending
    Returns highly-rated popular books
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            OPEN_LIBRARY_SEARCH,
            params={
                "q":      "first_publish_year:[2010 TO 2024]", 
                "limit":  limit,
                "fields": "key,title,author_name,cover_i",
            }
        )
        if response.status_code != 200:
            return {"results": [], "count": 0}
        data = response.json()

    books = [parse_book(item) for item in data.get("docs", [])]
    return {"results": books, "count": len(books)}


# ─────────────────────────────────────────
# 6. GET RECOMMENDED BOOKS (by interests)
# Used by: Onboarding Step 3, Dashboard AI row
# ─────────────────────────────────────────
async def get_recommended_books(interests: list[str],
                                 limit: int = 10) -> dict:
    """
    GET /api/books/recommended?interests=science,technology
    Improved with normalization and multi-stage fallback
    """
    import random
    
    category_map = {
        "philosophy": "philosophy",
        "science": "science",
        "history": "history",
        "technology": "computers",
        "business": "business",
        "psychology": "psychology",
        "fantasy": "fantasy",
        "fiction": "fiction",
        "biography": "biography",
        "self-help": "self-help",
        "social media": "communication",
        "education": "education"
    }

    # Normalize and sample
    normalized = [category_map.get(i.lower(), i.lower()) for i in interests] if interests else []
    sampled = random.sample(normalized, min(len(normalized), 3)) if normalized else []
    
    # Primary Query: OR search for 3 subjects
    query = " OR ".join([f'subject:"{s}"' for s in sampled]) if sampled else "subject:classic"

    logger.info(f"🔍 Recommendations Query: {query}")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                OPEN_LIBRARY_SEARCH,
                params={
                    "q":       query,
                    "limit":   limit,
                    "sort":    "rating", # Try to get better books
                    "fields":  "key,title,author_name,cover_i,subject,ia,has_fulltext",
                }
            )
            
            data = response.json()
            docs = data.get("docs", [])

            # Fallback 1: If OR query failed, try single subjects one by one
            if not docs and sampled:
                for s in sampled:
                    logger.info(f"⚠️ Fallback 1: Trying single subject: {s}")
                    res = await client.get(
                        OPEN_LIBRARY_SEARCH,
                        params={"q": f'subject:"{s}"', "limit": limit, "fields": "key,title,author_name,cover_i"}
                    )
                    docs = res.json().get("docs", [])
                    if docs: break

            # Fallback 2: General high-quality classics
            if not docs:
                logger.info("⚠️ Fallback 2: General fiction/classics")
                res = await client.get(
                    OPEN_LIBRARY_SEARCH,
                    params={"q": "subject:classic", "limit": limit, "fields": "key,title,author_name,cover_i"}
                )
                docs = res.json().get("docs", [])

    except Exception as e:
        logger.error(f"❌ Recommendation Error: {e}")
        return {"results": [], "total": 0, "interests": interests}

    books = [parse_book(item) for item in docs]
    return {
        "results":   books,
        "interests": interests,
        "total":     len(books),
    }


# ─────────────────────────────────────────
# 7. FULL-TEXT SEARCH INSIDE BOOK TITLES
# Used by: Smart Search page
# ─────────────────────────────────────────
async def full_text_search(query: str,
                            limit: int = 20) -> dict:
    """
    GET /api/books/full-search?q=binary+tree
    Returns books with matched title/subject snippets
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            OPEN_LIBRARY_SEARCH,
            params={
                "q":      query,
                "limit":  limit,
                "fields": "key,title,author_name,cover_i,isbn,"
                          "subject,first_publish_year,number_of_pages_median,"
                          "ratings_average,ratings_count,first_sentence",
            }
        )
        data = response.json()

    results = []
    for item in data.get("docs", []):
        book    = parse_book(item)
        snippet = item.get("first_sentence", {})
        if isinstance(snippet, dict):
            snippet = snippet.get("value", "")

        results.append({
            **book,
            "snippet":      snippet[:200] + "..." if len(snippet) > 200
                            else snippet,
            "matched_term": query,
        })

    return {
        "results": results,
        "count":   len(results),
        "query":   query,
    }


# ─────────────────────────────────────────
# 8. GET CLASSIC BOOKS (Gutendex — free PDFs)
# Used by: Free books section
# ─────────────────────────────────────────
async def get_classic_books(search: str = "",
                             limit: int = 12) -> dict:
    """
    GET /api/books/classics?search=sherlock
    Returns classic books with FREE downloadable PDFs
    from Project Gutenberg via Gutendex
    """
    params: dict = {"mime_type": "application/pdf"}
    if search:
        params["search"] = search

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(GUTENDEX_BASE, params=params)
            if response.status_code != 200:
                raise Exception(f"Gutendex returned {response.status_code}")
            data = response.json()
    except Exception as e:
        logger.warning(f"Gutendex failed: {e}. Falling back to Open Library classics.")
        # Fallback: search Open Library for classic books
        try:
            client = await async_http_client.get_client()
            response = await client.get(
                OPEN_LIBRARY_SEARCH,
                params={
                    "q": f"subject:classic {search}".strip(),
                    "limit": limit,
                    "fields": "key,title,author_name,cover_i,isbn,subject,first_publish_year,ia,has_fulltext",
                }
            )
            ol_data = response.json()
            books = [parse_book(item) for item in ol_data.get("docs", [])]
            return {"results": books, "count": len(books), "source": "Open Library Classics"}
        except Exception as e2:
            logger.error(f"Fallback also failed: {e2}")
            return {"results": [], "count": 0, "source": "unavailable"}

    books = []
    for item in data.get("results", [])[:limit]:
        formats  = item.get("formats", {})
        pdf_url  = formats.get("application/pdf", "")
        epub_url = formats.get("application/epub+zip", "")
        cover_url = formats.get("image/jpeg", "")
        authors = [a.get("name", "Unknown") for a in item.get("authors", [])]

        books.append({
            "id":          str(item.get("id")),
            "title":       item.get("title", "Unknown Title"),
            "author":      ", ".join(authors),
            "subjects":    item.get("subjects", [])[:5],
            "category":    item.get("subjects", ["Classic"])[0] if item.get("subjects") else "Classic",
            "cover_url":   cover_url,
            "cover_url_small": cover_url,
            "pdf_url":     pdf_url,
            "epub_url":    epub_url,
            "language":    item.get("languages", ["en"])[0],
            "download_count": item.get("download_count", 0),
            "is_free":     True,
            "is_premium":  False,
            "difficulty":  "Intermediate",
            "rating":      0,
        })

    return {
        "results": books,
        "count":   len(books),
        "source":  "Project Gutenberg (Free Classic Books)"
    }
