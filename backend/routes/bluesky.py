
import logging

from fastapi import APIRouter, HTTPException

from backend.services.bluesky_service import fetch_bluesky_posts

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/bluesky",
    tags=["Bluesky"],
)


@router.get("/last-24-hours/{state_id}")
async def get_last_24_hours_posts(state_id: int):
    if state_id not in range(1, 13):
        raise HTTPException(
            status_code=400,
            detail="Invalid state ID. Expected a value from 1 to 12.",
        )

    try:
        return await fetch_bluesky_posts(state_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        logger.exception("Bluesky configuration error")
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Bluesky authentication or search failed")
        raise HTTPException(
            status_code=502,
            detail=(
                "Bluesky login or search failed. Check the backend "
                "terminal for the detailed error."
            ),
        ) from exc
