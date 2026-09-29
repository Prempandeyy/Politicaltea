from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from pydantic import BaseModel
from typing import Optional, List

from backend.routes.auth import get_current_user
from backend.models import User

from backend.services.tea_ai import ask_tea


router = APIRouter(
    prefix="/api/tea",
    tags=["Tea AI"]
)


# =========================================================
# REQUEST SCHEMAS
# =========================================================

class TeaMessage(BaseModel):

    role: str

    content: str


class TeaChatRequest(BaseModel):

    message: str

    conversation: Optional[
        List[TeaMessage]
    ] = None


# =========================================================
# RESPONSE
# =========================================================

class TeaChatResponse(BaseModel):

    answer: str

    state_id: Optional[int] = None

    state_name: str

    model: str


# =========================================================
# ASK TEA
# =========================================================

@router.post(
    "/chat",
    response_model=TeaChatResponse
)
async def chat_with_tea(
    request: TeaChatRequest,
    current_user: User = Depends(
        get_current_user
    )
):

    # -----------------------------------------------------
    # Validate message
    # -----------------------------------------------------

    message = request.message.strip()

    if not message:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    # Prevent unnecessarily huge requests
    if len(message) > 4000:

        raise HTTPException(
            status_code=400,
            detail=(
                "Message is too long. "
                "Please keep it under 4000 characters."
            )
        )

    # -----------------------------------------------------
    # Conversation
    # -----------------------------------------------------

    conversation = None

    if request.conversation:

        conversation = [
            {
                "role": item.role,
                "content": item.content
            }

            for item in request.conversation[-10:]
        ]

    # -----------------------------------------------------
    # Ask Tea
    # -----------------------------------------------------

    try:

        result = await ask_tea(
            message=message,
            state_id=current_user.state_id,
            conversation=conversation
        )

        return result

    except RuntimeError as error:

        print(
            f"Tea AI error: {error}"
        )

        raise HTTPException(
            status_code=502,
            detail=str(error)
        )

    except Exception as error:

        print(
            f"Unexpected Tea AI error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Tea is temporarily unavailable. "
                "Please try again."
            )
        )
