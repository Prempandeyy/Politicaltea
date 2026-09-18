from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


# =========================================
# USER
# =========================================

class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    email = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    password = Column(String, nullable=False)

    state_id = Column(
        Integer,
        ForeignKey("states.id"),
        nullable=True
    )

    state = relationship(
        "State",
        back_populates="users"
    )


# =========================================
# USER CONTENT HISTORY
# =========================================

class UserContentSnapshot(Base):

    __tablename__ = "user_content_snapshots"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    state_id = Column(
        Integer,
        ForeignKey("states.id"),
        nullable=False
    )

    kind = Column(String, nullable=False)

    payload = Column(Text, nullable=False)

    captured_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )


class RecentContentCache(Base):

    __tablename__ = "recent_content_cache"

    id = Column(Integer, primary_key=True, index=True)

    state_id = Column(
        Integer,
        ForeignKey("states.id"),
        nullable=False,
        unique=True
    )

    payload = Column(Text, nullable=False)

    fetched_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )


# =========================================
# STATE
# =========================================

class State(Base):

    __tablename__ = "states"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        unique=True,
        nullable=False
    )

    users = relationship(
        "User",
        back_populates="state"
    )

    topics = relationship(
        "Topic",
        back_populates="state"
    )

    posts = relationship(
        "Post",
        back_populates="state"
    )

    videos = relationship(
        "Video",
        back_populates="state"
    )

    news = relationship(
        "News",
        back_populates="state"
    )


# =========================================
# TOPIC
# =========================================

class Topic(Base):

    __tablename__ = "topics"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    title = Column(
        String,
        nullable=False
    )

    mentions = Column(
        String,
        nullable=False
    )

    change = Column(
        String,
        nullable=False
    )

    state_id = Column(
        Integer,
        ForeignKey("states.id"),
        nullable=False
    )

    state = relationship(
        "State",
        back_populates="topics"
    )


# =========================================
# POST
# =========================================

class Post(Base):

    __tablename__ = "posts"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    author = Column(
        String,
        nullable=False
    )

    avatar = Column(
        String,
        nullable=True
    )

    type = Column(
        String,
        nullable=False
    )

    title = Column(
        String,
        nullable=False
    )

    body = Column(
        Text,
        nullable=False
    )

    image = Column(
        String,
        nullable=True
    )

    likes = Column(
        Integer,
        default=0
    )

    state_id = Column(
        Integer,
        ForeignKey("states.id"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    state = relationship(
        "State",
        back_populates="posts"
    )


# =========================================
# VIDEO
# =========================================

class Video(Base):

    __tablename__ = "videos"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    creator = Column(
        String,
        nullable=False
    )

    title = Column(
        String,
        nullable=False
    )

    views = Column(
        String,
        nullable=True
    )

    image = Column(
        String,
        nullable=True
    )

    video_url = Column(
        String,
        nullable=True
    )

    state_id = Column(
        Integer,
        ForeignKey("states.id"),
        nullable=False
    )

    state = relationship(
        "State",
        back_populates="videos"
    )


# =========================================
# NEWS
# =========================================

class News(Base):

    __tablename__ = "news"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    source = Column(
        String,
        nullable=False
    )

    title = Column(
        String,
        nullable=False
    )

    time = Column(
        String,
        nullable=True
    )

    image = Column(
        String,
        nullable=True
    )

    url = Column(
        String,
        nullable=True
    )

    state_id = Column(
        Integer,
        ForeignKey("states.id"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    state = relationship(
        "State",
        back_populates="news"
    )