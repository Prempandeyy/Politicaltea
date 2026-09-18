from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import RecentContentCache
from backend.config import STATE_NAMES

from backend.services.recent_content import (
    deserialize,
    fetch_recent_content,
    fetch_worldwide_content,
    is_fresh,
    sanitize_payload,
    serialize,
    utc_naive_now,
)

from backend.services.ai_trends import generate_ai_trends


router = APIRouter(
    prefix="/api/ai",
    tags=["AI Trends"],
)


CACHE_MINUTES = 15

def cached_payload(
    db: Session,
    cache_id,
    fetcher,
    minutes=CACHE_MINUTES,
):
    """
    Generic cache handler.

    cache_id:
        - Valid state ID -> database cache
        - None -> worldwide content (no DB cache)
    """

    # --------------------------------------------------
    # WORLDWIDE CONTENT
    # --------------------------------------------------

    if cache_id is None:

        payload = sanitize_payload(
            fetcher()
        )

        return payload

    # --------------------------------------------------
    # STATE CACHE
    # --------------------------------------------------

    row = (
        db.query(RecentContentCache)
        .filter(
            RecentContentCache.state_id == cache_id
        )
        .first()
    )

    # --------------------------------------------------
    # RETURN FRESH CACHE
    # --------------------------------------------------

    if row and is_fresh(
        row.fetched_at,
        minutes=minutes,
    ):
        return sanitize_payload(
            deserialize(row.payload)
        )

    # --------------------------------------------------
    # FETCH FRESH CONTENT
    # --------------------------------------------------

    payload = sanitize_payload(
        fetcher()
    )

    # --------------------------------------------------
    # FALLBACK TO STALE CACHE
    # --------------------------------------------------

    if (
        not payload.get("items")
        and row
        and row.payload
    ):
        stale = sanitize_payload(
            deserialize(row.payload)
        )

        if stale.get("items"):

            stale["source_errors"] = (
                payload.get(
                    "source_errors",
                    []
                )
            )

            return stale

    # --------------------------------------------------
    # SERIALIZE
    # --------------------------------------------------

    serialized = serialize(
        payload
    )

    # --------------------------------------------------
    # UPDATE EXISTING CACHE
    # --------------------------------------------------

    if row:

        row.payload = serialized
        row.fetched_at = utc_naive_now()

    # --------------------------------------------------
    # CREATE STATE CACHE
    # --------------------------------------------------

    else:

        row = RecentContentCache(
            state_id=cache_id,
            payload=serialized,
            fetched_at=utc_naive_now(),
        )

        db.add(row)

    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------

    db.commit()

    return payload

@router.get("/trends/{state_id}")
def get_ai_trends(
    state_id: int,
    db: Session = Depends(get_db),
):

    # --------------------------------------------------
    # Validate state
    # --------------------------------------------------

    state_name = STATE_NAMES.get(
        state_id
    )

    if not state_name:
        raise HTTPException(
            status_code=404,
            detail="Unknown state_id",
        )

    # --------------------------------------------------
    # STATE CONTENT
    # --------------------------------------------------

    state_payload = cached_payload(
        db=db,
        cache_id=state_id,
        fetcher=lambda: fetch_recent_content(
            state_name
        ),
    )

    # --------------------------------------------------
    # WORLDWIDE CONTENT
    # --------------------------------------------------

    worldwide_payload = cached_payload(
        db=db,
        cache_id=None,
        fetcher=fetch_worldwide_content,
    )

    # --------------------------------------------------
    # Extract articles
    # --------------------------------------------------

    state_news = (
        state_payload.get(
            "items",
            []
        )
    )

    worldwide_news = (
        worldwide_payload.get(
            "items",
            []
        )
    )

    # --------------------------------------------------
    # Generate AI trends
    # --------------------------------------------------

    try:

        trends = generate_ai_trends(
            state_name=state_name,
            state_news=state_news,
            worldwide_news=worldwide_news,
        )

    except Exception as exc:

        trends = {
            "ai": False,
            "state_topics": [],
            "worldwide_topics": [],
            "error": str(exc),
        }

    # --------------------------------------------------
    # Source errors
    # --------------------------------------------------

    source_errors = []

    source_errors.extend(
        state_payload.get(
            "source_errors",
            []
        )
    )

    source_errors.extend(
        worldwide_payload.get(
            "source_errors",
            []
        )
    )

    if trends.get("error"):
        source_errors.append(
            trends["error"]
        )

    # --------------------------------------------------
    # Response
    # --------------------------------------------------

    return {
        "state": state_name,

        "period": "last_24_hours",

        "ai_generated": trends.get(
            "ai",
            False
        ),

        "state_topics": trends.get(
            "state_topics",
            []
        ),

        "worldwide_topics": trends.get(
            "worldwide_topics",
            []
        ),

        "counts": {
            "state_articles": len(
                state_news
            ),

            "worldwide_articles": len(
                worldwide_news
            ),
        },

        "source_errors": source_errors,
    }