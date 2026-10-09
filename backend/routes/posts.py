from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Post, PostReaction, User
from backend.routes.auth import get_current_user
from backend.schemas import PostCreate, PostResponse


router = APIRouter(
    prefix="/api/posts",
    tags=["Posts"]
)


# =========================================================
# HELPERS
# =========================================================

def require_user_state(current_user: User) -> int:

    if current_user.state_id is None:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select a state before accessing state posts"
        )

    return current_user.state_id


def post_to_dict(post: Post, my_reaction=None) -> dict:

    return {
        "id": post.id,
        "user_id": post.user_id,
        "author": post.author,
        "avatar": post.avatar,
        "type": post.type,
        "title": post.title,
        "body": post.body,
        "image": post.image,
        "likes": post.likes or 0,
        "dislikes": post.dislikes or 0,
        "state_id": post.state_id,
        "created_at": post.created_at,
        "my_reaction": my_reaction
    }


def get_user_reaction(db: Session, user_id: int, post_id: int):

    reaction = (
        db.query(PostReaction)
        .filter(
            PostReaction.user_id == user_id,
            PostReaction.post_id == post_id
        )
        .first()
    )

    return reaction.reaction if reaction else None


# =========================================================
# GET LAST 24 HOURS POSTS (ONLY USER'S OWN STATE)
# =========================================================

@router.get("", response_model=list[PostResponse])
def get_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    state_id = require_user_state(current_user)

    since = datetime.utcnow() - timedelta(hours=24)

    posts = (
        db.query(Post)
        .filter(
            Post.state_id == state_id,
            Post.created_at >= since
        )
        .order_by(Post.created_at.desc())
        .all()
    )

    return [
        post_to_dict(
            post,
            get_user_reaction(db, current_user.id, post.id)
        )
        for post in posts
    ]


# =========================================================
# CREATE POST
# =========================================================

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

    author_name = (current_user.name or "").strip()

    if not author_name:

        raise HTTPException(
            status_code=400,
            detail="User name cannot be empty"
        )

    new_post = Post(

        # Actual user who created the post
        user_id=current_user.id,

        author=author_name,

        avatar=author_name[0].upper(),

        type=post.type,

        title=post.title,

        body=post.body,

        image=post.image,

        likes=0,

        dislikes=0,

        # Post belongs to logged-in user's state
        state_id=state_id,

        created_at=datetime.utcnow()
    )

    db.add(new_post)

    db.commit()

    db.refresh(new_post)

    return post_to_dict(new_post, None)


# =========================================================
# EDIT OWN POST
# =========================================================

@router.put(
    "/{post_id}",
    response_model=PostResponse
)
def update_post(
    post_id: int,
    data: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .first()
    )

    if not post:

        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    # Only post owner can edit
    if post.user_id != current_user.id:

        raise HTTPException(
            status_code=403,
            detail="You can edit only your own post"
        )

    post.type = data.type
    post.title = data.title
    post.body = data.body
    post.image = data.image

    db.commit()

    db.refresh(post)

    return post_to_dict(
        post,
        get_user_reaction(db, current_user.id, post.id)
    )


# =========================================================
# LIKE / UNLIKE (TOGGLE)
# =========================================================

@router.post("/{post_id}/reaction")
def react_to_post(
    post_id: int,
    reaction_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    state_id = require_user_state(current_user)

    # -----------------------------------------------------
    # Validate reaction
    # -----------------------------------------------------

    reaction_type = (
        reaction_data.get("reaction") or ""
    ).strip().lower()

    if reaction_type not in ["like", "dislike"]:

        raise HTTPException(
            status_code=400,
            detail="Reaction must be 'like' or 'dislike'"
        )

    # -----------------------------------------------------
    # Find post
    # -----------------------------------------------------

    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .first()
    )

    if not post:

        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    # -----------------------------------------------------
    # State protection
    # -----------------------------------------------------

    if post.state_id != state_id:

        raise HTTPException(
            status_code=403,
            detail="You cannot react to a post from another state"
        )

    # -----------------------------------------------------
    # Existing reaction
    # -----------------------------------------------------

    existing_reaction = (
        db.query(PostReaction)
        .filter(
            PostReaction.user_id == current_user.id,
            PostReaction.post_id == post.id
        )
        .first()
    )

    # =====================================================
    # NO PREVIOUS REACTION -> ADD
    # =====================================================

    if existing_reaction is None:

        db.add(
            PostReaction(
                user_id=current_user.id,
                post_id=post.id,
                reaction=reaction_type
            )
        )

        if reaction_type == "like":
            post.likes = (post.likes or 0) + 1
        else:
            post.dislikes = (post.dislikes or 0) + 1

        final_reaction = reaction_type

    # =====================================================
    # SAME REACTION AGAIN -> REMOVE (like -> unlike)
    # =====================================================

    elif existing_reaction.reaction == reaction_type:

        db.delete(existing_reaction)

        if reaction_type == "like":
            post.likes = max(0, (post.likes or 0) - 1)
        else:
            post.dislikes = max(0, (post.dislikes or 0) - 1)

        final_reaction = None

    # =====================================================
    # DIFFERENT REACTION -> SWITCH
    # =====================================================

    else:

        old_reaction = existing_reaction.reaction

        existing_reaction.reaction = reaction_type

        if old_reaction == "like":

            post.likes = max(0, (post.likes or 0) - 1)
            post.dislikes = (post.dislikes or 0) + 1

        else:

            post.dislikes = max(0, (post.dislikes or 0) - 1)
            post.likes = (post.likes or 0) + 1

        final_reaction = reaction_type

    db.commit()

    db.refresh(post)

    return {
        "success": True,
        "message": "Reaction updated successfully",
        "post_id": post.id,
        "likes": post.likes or 0,
        "dislikes": post.dislikes or 0,
        "my_reaction": final_reaction
    }


# =========================================================
# GET USER'S REACTION
# =========================================================

@router.get("/{post_id}/reaction")
def get_my_reaction(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .first()
    )

    if not post:

        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    if post.state_id != current_user.state_id:

        raise HTTPException(
            status_code=403,
            detail="This post is not available in your state"
        )

    return {
        "post_id": post_id,
        "my_reaction": get_user_reaction(
            db,
            current_user.id,
            post_id
        )
    }


# =========================================================
# DELETE OWN POST
# =========================================================

@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .first()
    )

    if not post:

        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    # Only post owner can delete
    if post.user_id != current_user.id:

        raise HTTPException(
            status_code=403,
            detail="You can delete only your own post"
        )

    # Delete reactions first
    db.query(PostReaction).filter(
        PostReaction.post_id == post.id
    ).delete(
        synchronize_session=False
    )

    db.delete(post)

    db.commit()

    return {
        "success": True,
        "message": "Post deleted successfully"
    }
