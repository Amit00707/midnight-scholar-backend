"""
Vector Store Service — Optional Qdrant + OpenAI Embeddings
============================================================
Disabled gracefully when qdrant_client or langchain_openai not installed.
"""

from typing import List

from app.core.config import settings

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    _qdrant_available = True
except ImportError:
    _qdrant_available = False

try:
    from langchain_openai import OpenAIEmbeddings
    _embeddings_available = True
except ImportError:
    _embeddings_available = False

import uuid

# Only initialize if both packages are available
if _qdrant_available and _embeddings_available:
    client = QdrantClient(url=settings.QDRANT_URL)
    embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
else:
    client = None
    embeddings = None


async def create_collection_if_not_exists():
    """Ensure the vector collection exists."""
    if not client:
        return
    collections = client.get_collections().collections
    names = [c.name for c in collections]
    if settings.QDRANT_COLLECTION not in names:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )


async def store_page_embedding(book_id: int, page_number: int, text: str):
    """Convert page text to a vector embedding and store in Qdrant."""
    if not client or not embeddings:
        return
    vector = await embeddings.aembed_query(text)
    point = PointStruct(
        id=str(uuid.uuid4()),
        vector=vector,
        payload={"book_id": book_id, "page_number": page_number, "text": text},
    )
    client.upsert(collection_name=settings.QDRANT_COLLECTION, points=[point])


async def search_similar(query: str, book_id: int, top_k: int = 3) -> List[dict]:
    """Find the most relevant passages for a user's question."""
    if not client or not embeddings:
        return []
    vector = await embeddings.aembed_query(query)
    results = client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=vector,
        query_filter={"must": [{"key": "book_id", "match": {"value": book_id}}]},
        limit=top_k,
    )
    return [{"text": r.payload["text"], "page": r.payload["page_number"], "score": r.score} for r in results]
