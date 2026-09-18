from datetime import datetime, timedelta, timezone
import os
from urllib.parse import unquote

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status

from backend.models import User
from backend.routes.auth import get_current_user
from backend.routes.content import STATE_MAP
from backend.schemas import XPostResponse


load_dotenv()

router = APIRouter(
    prefix="/api/x-posts",
    tags=["X Posts"]
)

X_BEARER_TOKEN = unquote(
    os.getenv("X_BEARER_TOKEN", "")
)
X_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


@router.get(
    "",
    response_model=list[XPostResponse]
)
def get_recent_x_posts(
    current_user: User = Depends(get_current_user)
):

    if current_user.state_id is None:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select a state before accessing X posts"
        )

    if not X_BEARER_TOKEN:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="X_BEARER_TOKEN is not configured"
        )

    state_name = STATE_MAP[current_user.state_id]
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=24)

    try:

        response = requests.get(
            X_SEARCH_URL,
            headers={
                "Authorization": f"Bearer {X_BEARER_TOKEN}"
            },
            params={
                "query": f'"{state_name}" -is:retweet lang:en',
                "start_time": start_time.isoformat().replace("+00:00", "Z"),
                "end_time": now.isoformat().replace("+00:00", "Z"),
                "max_results": 100,
                "tweet.fields": "author_id,created_at,text",
                "expansions": "author_id",
                "user.fields": "name,username"
            },
            timeout=15
        )

    except requests.RequestException as error:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to reach the X API"
        ) from error

    if not response.ok:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to fetch recent X posts"
        )

    payload = response.json()
    users = {
        user["id"]: user
        for user in payload.get("includes", {}).get("users", [])
    }
    x_posts = []

    for post in payload.get("data", []):

        author = users.get(post.get("author_id"), {})
        created_at = datetime.fromisoformat(
            post["created_at"].replace("Z", "+00:00")
        )

        x_posts.append({
            "id": post["id"],
            "text": post["text"],
            "author": author.get("name", "X user"),
            "author_username": author.get("username"),
            "created_at": created_at,
            "url": (
                f'https://x.com/{author["username"]}/status/{post["id"]}'
                if author.get("username")
                else None
            ),
            "state_id": current_user.state_id
        })

    return sorted(
        x_posts,
        key=lambda post: post["created_at"],
        reverse=True
    )