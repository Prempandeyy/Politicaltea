from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# =========================================
# AUTH
# =========================================

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    state_id: Optional[int] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    state_id: Optional[int] = None

    class Config:
        from_attributes = True


# =========================================
# UPDATE USER PROFILE
# =========================================

class UserUpdate(BaseModel):
    name: str
    email: EmailStr
    state_id: Optional[int] = None


# =========================================
# STATE
# =========================================

class StateResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


# =========================================
# TOPIC
# =========================================

class TopicResponse(BaseModel):
    id: int
    title: str
    mentions: str
    change: str
    state_id: int

    class Config:
        from_attributes = True


# =========================================
# POST
# =========================================

class PostCreate(BaseModel):
    type: str
    title: str
    body: str
    image: Optional[str] = None


class PostResponse(BaseModel):
    id: int

    # Owner
    user_id: int

    # Basic post information
    author: str
    avatar: Optional[str] = None
    type: str
    title: str
    body: str
    image: Optional[str] = None

    # Reactions
    likes: int = 0
    dislikes: int = 0

    # State and timestamp
    state_id: int
    created_at: datetime

    # Current logged-in user's reaction
    # Possible values: "like", "dislike", None
    my_reaction: Optional[str] = None

    class Config:
        from_attributes = True


# =========================================
# POST REACTION
# =========================================

class PostReactionRequest(BaseModel):
    reaction: str


class PostReactionResponse(BaseModel):
    success: bool
    message: str
    post_id: int
    likes: int
    dislikes: int
    my_reaction: Optional[str] = None


# =========================================
# VIDEO
# =========================================

class VideoResponse(BaseModel):
    id: int
    creator: str
    title: str
    views: Optional[str] = None
    image: Optional[str] = None
    video_url: Optional[str] = None
    state_id: int

    class Config:
        from_attributes = True


# =========================================
# NEWS
# =========================================

class NewsResponse(BaseModel):
    id: int
    source: str
    title: str
    time: Optional[str] = None
    image: Optional[str] = None
    url: Optional[str] = None
    state_id: int

    class Config:
        from_attributes = True


# =========================================
# TRENDING
# =========================================

class TrendingTopicResponse(BaseModel):
    title: str
    mentions: str
    change: str
    score: int
    state_id: int


class TrendingResponse(BaseModel):
    state_topics: list[TrendingTopicResponse]
    worldwide_topics: list[TrendingTopicResponse]


# =========================================
# RECENT CONTENT
# =========================================

class RecentContentItem(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    source: str
    published_at: str
    url: str
    image: Optional[str] = None
    youtube_views: int = 0
    trending_score: int = 0


class RecentContentResponse(BaseModel):
    items: list[RecentContentItem]
    fetched_at: str
    source_errors: list[str] = []
