from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    RecentContentCache,
    User,
)

from backend.routes.auth import (
    get_current_user
)

from backend.config import STATE_NAMES

from backend.schemas import (
    RecentContentResponse
)

from backend.services.recent_content import (
    deserialize,
    fetch_recent_content,
    is_fresh,
    sanitize_payload,
    serialize,
)


router = APIRouter(
    prefix="/api/recent-content",
    tags=["Recent Content"]
)


@router.get(
    "",
    response_model=RecentContentResponse
)
def get_recent_content(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):

    if current_user.state_id is None:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Select a state before "
                "loading recent content"
            )
        )

    state_name = STATE_NAMES.get(
        current_user.state_id
    )

    if not state_name:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown state"
        )

    cache = (
        db.query(
            RecentContentCache
        )
        .filter(
            RecentContentCache.state_id
            == current_user.state_id
        )
        .first()
    )

    # Return cached data if fresh
    if (
        cache
        and is_fresh(
            cache.fetched_at
        )
    ):

        return sanitize_payload(
            deserialize(
                cache.payload
            )
        )

    # Fetch fresh content
    payload = fetch_recent_content(
        state_name
    )

    # If fetching fails but old cache exists,
    # return stale data instead of breaking UI.
    if (
        cache
        and not payload.get("items")
        and payload.get("source_errors")
    ):

        stale_payload = sanitize_payload(
            deserialize(
                cache.payload
            )
        )

        stale_payload[
            "source_errors"
        ] = payload[
            "source_errors"
        ]

        return stale_payload

    serialized = serialize(
        payload
    )

    if cache is None:

        cache = RecentContentCache(
            state_id=current_user.state_id,
            payload=serialized,
            fetched_at=datetime.utcnow(),
        )

        db.add(cache)

    else:

        cache.payload = serialized
        cache.fetched_at = (
            datetime.utcnow()
        )

    db.commit()

    return sanitize_payload(
        payload
    )