from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.config import STATE_NAMES
from backend.services import recent_content
from backend.routes.ai_trends import cached_payload


router = APIRouter(
    prefix="/api",
    tags=["content"],
)


def _format_views(count):

    if not count:
        return None

    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M views"

    if count >= 1_000:
        return f"{count / 1_000:.1f}K views"

    return f"{count} views"


def _relative_time(iso_value):

    published = recent_content.parse_date(iso_value)

    if not published:
        return ""

    now = datetime.now(timezone.utc)

    minutes = max(0, int((now - published).total_seconds() // 60))

    if minutes < 60:
        return f"{max(minutes, 1)}m ago"

    hours = minutes // 60

    if hours < 24:
        return f"{hours}h ago"

    return f"{hours // 24}d ago"


def _is_video(item):
    url = (item.get("url") or "").lower()

    return (
        item.get("content_type") == "video"
        or "youtube.com" in url
        or "youtu.be" in url
    )


def _split_items(items, state_id):

    news = []
    videos = []
    blogs = []

    for item in items:

        if _is_video(item):
            videos.append({
                "id": item.get("id"),
                "creator": item.get("source") or "YouTube",
                "title": item.get("title") or "Political Tea video",
                "views": _format_views(item.get("youtube_views", 0)),
                "time": _relative_time(item.get("published_at", "")),
                "image": item.get("image"),
                "video_url": item.get("url") or "",
                "state_id": state_id,
            })

            continue

        entry = {
            "id": item.get("id"),
            "source": item.get("source") or "News",
            "title": item.get("title") or "Untitled news",
            "description": item.get("description") or "",
            "time": _relative_time(item.get("published_at", "")),
            "image": item.get("image"),
            "url": item.get("url") or "",
            "state_id": state_id,
        }

        if item.get("content_type") == "blog":
            blogs.append(entry)
        else:
            news.append(entry)

    return news, videos, blogs


@router.get("/content/{state_id}")
def get_state_content(
    state_id: int,
    db: Session = Depends(get_db),
):

    state_name = STATE_NAMES.get(state_id)

    if not state_name:
        raise HTTPException(
            status_code=404,
            detail="Unknown state_id",
        )

    payload = cached_payload(
        db,
        state_id,
        lambda: recent_content.fetch_recent_content(state_name),
    )

    news, videos, blogs = _split_items(
        payload.get("items", []),
        state_id,
    )

    return {
        "news": news,
        "videos": videos,
        "blogs": blogs,
        "fetched_at": payload.get("fetched_at"),
        "source_errors": payload.get("source_errors", []),
    }