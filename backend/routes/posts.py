from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Post, User
from backend.routes.auth import get_current_user
from backend.schemas import PostCreate, PostResponse


router = APIRouter(
    prefix="/api/posts",
    tags=["Posts"]
)


def require_user_state(current_user: User) -> int:

    if current_user.state_id is None:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select a state before accessing state posts"
        )

    return current_user.state_id


@router.get(
    "",
    response_model=list[PostResponse]
)
def get_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    state_id = require_user_state(current_user)
    since = datetime.utcnow() - timedelta(hours=24)

    return db.query(Post).filter(
        Post.state_id == state_id,
        Post.created_at >= since
    ).order_by(
        Post.created_at.desc()
    ).all()


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED
)
def create_post(
    post: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    state_id = require_user_state(current_user)

    new_post = Post(
        author=current_user.name,
        avatar=current_user.name.strip()[0].upper(),
        type=post.type,
        title=post.title,
        body=post.body,
        image=post.image,
        state_id=state_id
    )

    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    return new_post