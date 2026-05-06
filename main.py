"""
Midnight Scholar — FastAPI Entry Point
======================================
Boots the API server, registers all route modules, and enables CORS.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# Route Imports
from app.api.routes_auth import router as auth_router
from app.api.routes_ai import router as ai_router
from app.api.routes_books import router as books_router
from app.api.routes_reader import router as reader_router
from app.api.routes_social import router as social_router
from app.api.routes_gamification import router as gamification_router
from app.api.routes_admin import router as admin_router
from app.api.routes_teacher import router as teacher_router
from app.api.routes_notifications import router as notifications_router
from app.api.routes_subscription import router as subscription_router


from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


def run_migrations():
    """Run alembic migrations automatically on startup — no shell needed."""
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Database migrations applied successfully.")
    except Exception as e:
        logger.warning(f"⚠️ Migration warning (non-fatal): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: run DB migrations. Shutdown: cleanup."""
    run_migrations()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered E-Book Library Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — Allow all Vercel deployments + localhost
def is_allowed_origin(origin: str) -> bool:
    allowed = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
    if origin in allowed:
        return True
    # Allow ALL vercel.app subdomains (preview + production)
    if origin.endswith(".vercel.app"):
        return True
    if origin in ("http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"):
        return True
    return False

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:\d+|http://127\.0\.0\.1:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all route modules
app.include_router(auth_router, prefix="/api", tags=["Auth"])
app.include_router(ai_router, prefix="/api", tags=["AI Engine"])
app.include_router(books_router, prefix="/api", tags=["Books"])
app.include_router(reader_router, prefix="/api", tags=["Reader"])
app.include_router(social_router, prefix="/api", tags=["Social"])
app.include_router(gamification_router, prefix="/api", tags=["Gamification"])
app.include_router(admin_router, prefix="/api", tags=["Admin"])
app.include_router(teacher_router, prefix="/api", tags=["Teacher"])
app.include_router(notifications_router, prefix="/api", tags=["Notifications"])
app.include_router(subscription_router, prefix="/api", tags=["Subscription"])


@app.get("/")
async def root():
    return {"status": "online", "service": "Midnight Scholar API", "version": "1.0.0"}
