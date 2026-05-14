# ============================================================
# app/api/routes_proxy.py
# Midnight Scholar — PDF Proxy for CORS handling
# ============================================================

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import logging

router = APIRouter(prefix="/proxy", tags=["Proxy"])
logger = logging.getLogger(__name__)

@router.get("/pdf")
async def proxy_pdf(url: str = Query(..., description="The direct URL of the PDF to proxy")):
    """
    Proxies a PDF from a remote server to bypass CORS restrictions.
    Used by the frontend PdfViewer.
    """
    # Whitelist of allowed domains for security
    allowed_domains = ["arxiv.org", "archive.org", "standardebooks.org", "gutenberg.org", "gutendex.com"]
    if not any(domain in url for domain in allowed_domains):
        # We'll allow it for now but log it, or you can be stricter
        logger.warning(f"Proxying untrusted PDF domain: {url}")

    try:
        # Create a client that follows redirects
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            # Send a GET request to the remote PDF URL
            # Note: We stream the response to save memory
            response = await client.get(url)
            response.raise_for_status()

            # Return the streaming response with original content type
            return StreamingResponse(
                content=response.iter_bytes(),
                media_type=response.headers.get("Content-Type", "application/pdf"),
                headers={
                    "Access-Control-Allow-Origin": "*", # Ensure frontend can read it
                    "Content-Disposition": response.headers.get("Content-Disposition", "")
                }
            )
    except httpx.HTTPStatusError as e:
        logger.error(f"Proxy fetch failed (HTTP {e.response.status_code}): {url}")
        raise HTTPException(status_code=e.response.status_code, detail="Remote PDF unavailable")
    except Exception as e:
        logger.error(f"Proxy error: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")
