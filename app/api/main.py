from collections import defaultdict, deque
from threading import Lock
from time import time
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import get_db
from app.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
app = FastAPI(title="German Feed Scraper API", version="1.0.0")

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

_rate_limit_lock = Lock()
_request_windows: dict[str, deque[float]] = defaultdict(deque)

LIST_FIELDS = (
    "id,title,url,published_date,source_domain,theme,estimated_difficulty,estimated_reading_time,created_at"
)
DETAIL_FIELDS = (
    "id,url,title,published_date,author,source_domain,source_feed,theme,created_at,updated_at,"
    "cleaned_content,vocabulary_annotations,grammar_patterns,cultural_notes,"
    "comprehension_questions,estimated_difficulty,estimated_reading_time,enhanced_at"
)
VALID_LEVELS = {"A2", "B1", "B2", "C1", "C2"}


@app.middleware("http")
async def simple_rate_limit(request: Request, call_next):
    """Basic in-memory per-IP rate limiting for read endpoints."""
    if request.method == "GET":
        client_ip = request.client.host if request.client else "unknown"
        now = time()
        window_start = now - 60
        max_requests = max(1, settings.api_rate_limit_per_minute)

        with _rate_limit_lock:
            bucket = _request_windows[client_ip]
            while bucket and bucket[0] < window_start:
                bucket.popleft()
            if len(bucket) >= max_requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please retry later."},
                )
            bucket.append(now)

    return await call_next(request)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/articles")
def list_articles(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    domain: Optional[str] = Query(default=None, min_length=2, max_length=255),
    difficulty: Optional[str] = Query(default=None),
):
    try:
        query = (
            get_db()
            .table("article_list_view")
            .select(LIST_FIELDS)
            .order("published_date", desc=True, nullsfirst=False)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )

        if domain:
            query = query.eq("source_domain", domain.lower().strip())
        if difficulty:
            normalized_level = difficulty.strip().upper()
            if normalized_level not in VALID_LEVELS:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid difficulty. Use one of: {', '.join(sorted(VALID_LEVELS))}",
                )
            query = query.eq("estimated_difficulty", normalized_level)

        result = query.execute()
        return {"items": result.data or [], "limit": limit, "offset": offset}
    except HTTPException:
        raise
    except Exception:
        logger.error("Failed to fetch articles list from database")
        raise HTTPException(status_code=500, detail="Failed to fetch articles")


@app.get("/api/articles/{article_id}")
def get_article(article_id: UUID):
    try:
        result = (
            get_db()
            .table("article_detail_view")
            .select(DETAIL_FIELDS)
            .eq("id", str(article_id))
            .limit(1)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Article not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.error("Failed to fetch article detail from database")
        raise HTTPException(status_code=500, detail="Failed to fetch article")
