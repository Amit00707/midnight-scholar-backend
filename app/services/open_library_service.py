# ============================================================
# app/services/open_library_service.py
# Midnight Scholar — Open Library API Integration
# 100% Free | No API Key | No Card | No Limits
# ============================================================

import httpx
from typing import Optional

OPEN_LIBRARY_BASE    = "https://openlibrary.org"
OPEN_LIBRARY_SEARCH  = "https://openlibrary.org/search.json"
OPEN_LIBRARY_COVERS  = "https://covers.openlibrary.org/b"
GUTENDEX_BASE        = "https://gutendex.com/books"


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
    # Fallback placeholder in amber tone
    return f"https://placehold.co/200x300/1C1917/D97706?text=No+Cover"


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
    offset = (page - 1) * limit

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            OPEN_LIBRARY_SEARCH,
            params={
                "q":      query,
                "limit":  limit,
                "offset": offset,
                "fields": "key,title,author_name,cover_i,isbn,"
                          "subject,first_publish_year,number_of_pages_median,"
                          "ratings_average,ratings_count,language,publisher,"
                          "first_sentence",
            }
        )
        data = response.json()

    books      = [parse_book(item) for item in data.get("docs", [])]
    total      = data.get("numFound", 0)
    total_pages = -(-total // limit)  # Ceiling division

    return {
        "results":     books,
        "count":       len(books),
        "total":       total,
        "page":        page,
        "total_pages": total_pages,
        "query":       query,
    }


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
# Used by: Dashboard rows, Book listing filter
# ─────────────────────────────────────────
async def get_books_by_category(category: str,
                                 limit: int = 12) -> dict:
    """
    GET /api/books/category/science?limit=12
    Categories: fiction, science, history, technology,
                business, self-help, philosophy, mathematics,
                psychology, biography
    """
    # Map display names to Open Library subject queries
    category_map = {
        "fiction":      "fiction",
        "science":      "science",
        "history":      "history",
        "technology":   "computers",
        "business":     "business & economics",
        "self-help":    "self-help",
        "philosophy":   "philosophy",
        "mathematics":  "mathematics",
        "psychology":   "psychology",
        "biography":    "biography",
        "art":          "art & design",
        "economics":    "economics",
    }
    subject = category_map.get(category.lower(), category)

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            OPEN_LIBRARY_SEARCH,
            params={
                "subject": subject,
                "limit":   limit,
                "sort":    "rating desc",
                "fields":  "key,title,author_name,cover_i,isbn,"
                           "subject,first_publish_year,number_of_pages_median,"
                           "ratings_average,ratings_count",
            }
        )
        data = response.json()

    books = [parse_book(item) for item in data.get("docs", [])]
    return {
        "results":  books,
        "category": category,
        "count":    len(books),
    }


# ─────────────────────────────────────────
# 4. GET SINGLE BOOK DETAIL
# Used by: Book Details page
# ─────────────────────────────────────────
async def get_book_detail(work_id: str) -> dict:
    """
    GET /api/books/OL82563W
    work_id example: OL82563W (from search results "id" field)
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Get work details
        work_res = await client.get(
            f"{OPEN_LIBRARY_BASE}/works/{work_id}.json"
        )
        work = work_res.json()

        # Get author details
        author_keys = work.get("authors", [])
        authors = []
        for a in author_keys[:2]:  # Max 2 authors
            author_key = a.get("author", {}).get("key", "")
            if author_key:
                try:
                    author_res = await client.get(
                        f"{OPEN_LIBRARY_BASE}{author_key}.json"
                    )
                    author_data = author_res.json()
                    authors.append({
                        "name": author_data.get("name", "Unknown"),
                        "bio":  author_data.get("bio", {}).get("value", "")
                                if isinstance(author_data.get("bio"), dict)
                                else author_data.get("bio", ""),
                        "photo_url": f"https://covers.openlibrary.org/a/olid/"
                                     f"{author_key.replace('/authors/', '')}-L.jpg"
                    })
                except Exception:
                    pass

    # Parse description
    desc = work.get("description", "")
    if isinstance(desc, dict):
        desc = desc.get("value", "")

    # Parse subjects
    subjects = work.get("subjects", [])

    # Get covers
    covers   = work.get("covers", [])
    cover_id = covers[0] if covers else None

    return {
        "id":          work_id,
        "title":       work.get("title", "Unknown Title"),
        "authors":     authors,
        "description": desc,
        "subjects":    subjects[:10],
        "category":    subjects[0].title() if subjects else "General",
        "cover_url":   get_cover_url(cover_id, size="L"),
        "cover_url_small": get_cover_url(cover_id, size="M"),
        "created":     work.get("created", {}).get("value", ""),
        "is_free":     True,
        "is_premium":  False,
    }


# ─────────────────────────────────────────
# 5. GET TRENDING / POPULAR BOOKS
# Used by: Dashboard "Popular Books" row
# ─────────────────────────────────────────
async def get_trending_books(limit: int = 12) -> dict:
    """
    GET /api/books/trending
    Returns highly-rated popular books
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            OPEN_LIBRARY_SEARCH,
            params={
                "q":      "programming",  # broad popular query
                "sort":   "rating desc",
                "limit":  limit,
                "fields": "key,title,author_name,cover_i,isbn,"
                          "subject,first_publish_year,number_of_pages_median,"
                          "ratings_average,ratings_count",
            }
        )
        data = response.json()

    books = [parse_book(item) for item in data.get("docs", [])]
    return {"results": books, "count": len(books)}


# ─────────────────────────────────────────
# 6. GET RECOMMENDED BOOKS (by interests)
# Used by: Onboarding Step 3, Dashboard AI row
# ─────────────────────────────────────────
async def get_recommended_books(interests: list[str],
                                 limit: int = 6) -> dict:
    """
    GET /api/books/recommended?interests=science,technology
    Used after onboarding interest selection
    """
    # Build query from user interests
    query = " OR ".join(interests[:3])  # Max 3 interests combined

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            OPEN_LIBRARY_SEARCH,
            params={
                "subject": interests[0] if interests else "fiction",
                "sort":    "rating desc",
                "limit":   limit,
                "fields":  "key,title,author_name,cover_i,isbn,"
                           "subject,first_publish_year,number_of_pages_median,"
                           "ratings_average,ratings_count",
            }
        )
        data = response.json()

    books = [parse_book(item) for item in data.get("docs", [])]
    return {
        "results":   books,
        "interests": interests,
        "count":     len(books),
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

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(GUTENDEX_BASE, params=params)
        data     = response.json()

    books = []
    for item in data.get("results", [])[:limit]:
        # Get PDF download URL
        formats  = item.get("formats", {})
        pdf_url  = formats.get("application/pdf", "")
        epub_url = formats.get("application/epub+zip", "")

        # Get cover
        cover_url = formats.get("image/jpeg", "")

        # Get authors
        authors = [a.get("name", "Unknown")
                   for a in item.get("authors", [])]

        books.append({
            "id":          str(item.get("id")),
            "title":       item.get("title", "Unknown Title"),
            "author":      ", ".join(authors),
            "subjects":    item.get("subjects", [])[:5],
            "category":    item.get("subjects", ["Classic"])[0]
                           if item.get("subjects") else "Classic",
            "cover_url":   cover_url,
            "pdf_url":     pdf_url,    # Free downloadable PDF
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
