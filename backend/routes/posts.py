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
# REQUIRE USER STATE
# =========================================================

def require_user_state(current_user: User) -> int:

    if current_user.state_id is None:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select a state before accessing state posts"
        )

    return current_user.state_id


# =========================================================
# GET LAST 24 HOURS POSTS
# =========================================================

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

    posts = (
        db.query(Post)
        .filter(
            Post.state_id == state_id,
            Post.created_at >= since
        )
        .order_by(
            Post.created_at.desc()
        )
        .all()
    )

    result = []

    for post in posts:

        reaction = (
            db.query(PostReaction)
            .filter(
                PostReaction.user_id == current_user.id,
                PostReaction.post_id == post.id
            )
            .first()
        )

        result.append({
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
            "my_reaction": (
                reaction.reaction
                if reaction
                else None
            )
        })

    return result


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

    # Make sure name exists
    author_name = current_user.name.strip()

    if not author_name:

        raise HTTPException(
            status_code=400,
            detail="User name cannot be empty"
        )

    new_post = Post(

        # IMPORTANT:
        # Store the actual user who created the post
        user_id=current_user.id,

        author=author_name,

        avatar=author_name[0].upper(),

        type=post.type,

        title=post.title,

        body=post.body,

        image=post.image,

        # New post starts with zero reactions
        likes=0,

        dislikes=0,

        # VERY IMPORTANT:
        # Post belongs to logged-in user's state
        state_id=state_id,

        created_at=datetime.utcnow()
    )

    db.add(new_post)

    db.commit()

    db.refresh(new_post)

    return {
        "id": new_post.id,
        "user_id": new_post.user_id,
        "author": new_post.author,
        "avatar": new_post.avatar,
        "type": new_post.type,
        "title": new_post.title,
        "body": new_post.body,
        "image": new_post.image,
        "likes": 0,
        "dislikes": 0,
        "state_id": new_post.state_id,
        "created_at": new_post.created_at,
        "my_reaction": None
    }


# =========================================================
# LIKE / DISLIKE
# =========================================================

@router.post(
    "/{post_id}/reaction"
)
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
    # STATE PROTECTION
    # -----------------------------------------------------

    if post.state_id != state_id:

        raise HTTPException(
            status_code=403,
            detail="You cannot react to a post from another state"
        )

    # -----------------------------------------------------
    # Check existing reaction
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
    # NO PREVIOUS REACTION
    # =====================================================

    if existing_reaction is None:

        new_reaction = PostReaction(
            user_id=current_user.id,
            post_id=post.id,
            reaction=reaction_type
        )

        db.add(new_reaction)

        if reaction_type == "like":

            post.likes = (post.likes or 0) + 1

        else:

            post.dislikes = (post.dislikes or 0) + 1

    # =====================================================
    # SAME REACTION AGAIN
    # =====================================================

    elif existing_reaction.reaction == reaction_type:

        # Do nothing.
        #
        # This is what prevents:
        #
        # Like → Like → Like → Like
        #
        # from increasing the count multiple times.

        return {
            "success": True,
            "message": "You have already reacted to this post",
            "post_id": post.id,
            "likes": post.likes or 0,
            "dislikes": post.dislikes or 0,
            "my_reaction": existing_reaction.reaction
        }

    # =====================================================
    # CHANGE LIKE → DISLIKE
    # =====================================================

    else:

        old_reaction = existing_reaction.reaction

        existing_reaction.reaction = reaction_type

        if old_reaction == "like":

            post.likes = max(
                0,
                (post.likes or 0) - 1
            )

            post.dislikes = (
                post.dislikes or 0
            ) + 1

        # =================================================
        # CHANGE DISLIKE → LIKE
        # =================================================

        else:

            post.dislikes = max(
                0,
                (post.dislikes or 0) - 1
            )

            post.likes = (
                post.likes or 0
            ) + 1

    db.commit()

    db.refresh(post)

    return {
        "success": True,
        "message": "Reaction updated successfully",
        "post_id": post.id,
        "likes": post.likes or 0,
        "dislikes": post.dislikes or 0,
        "my_reaction": reaction_type
    }


# =========================================================
# GET USER'S REACTION
# =========================================================

@router.get(
    "/{post_id}/reaction"
)
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

    reaction = (
        db.query(PostReaction)
        .filter(
            PostReaction.user_id == current_user.id,
            PostReaction.post_id == post_id
        )
        .first()
    )

    return {
        "post_id": post_id,
        "my_reaction": (
            reaction.reaction
            if reaction
            else None
        )
    }


# =========================================================
# DELETE OWN POST
# =========================================================

@router.delete(
    "/{post_id}"
)
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
