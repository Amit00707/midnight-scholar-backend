"""Compatibility entrypoint for uvicorn.

This module re-exports the FastAPI app defined at the repository root so
`uvicorn app.main:app` works as expected.
"""

from main import app
