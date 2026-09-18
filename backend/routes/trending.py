from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus
from xml.etree import ElementTree

import requests

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.routes.auth import get_current_user
from backend.config import STATE_NAMES

from backend.services.recent_content import (
    fetch_recent_content
)

from backend.services.ai_topics import (
    generate_state_topics,
    generate_worldwide_topics
)


router = APIRouter(
    prefix="/api/trending",
    tags=["Trending"]
)


def fetch_world_news():

    now = datetime.now(
        timezone.utc
    )

    cutoff = (
        now -
        timedelta(hours=24)
    )

    query = quote_plus(
        """
        politics OR election OR government
        OR president OR prime minister
        OR parliament OR diplomacy
        OR international relations
        """
    )

    url = (
        "https://news.google.com/rss/search?"
        f"q={query}"
        "&hl=en-IN"
        "&gl=IN"
        "&ceid=IN:en"
    )

    try:

        response = requests.get(
            url,
            headers={
                "User-Agent":
                    "Mozilla/5.0 PoliticalTea/1.0"
            },
            timeout=10
        )

        response.raise_for_status()

        root = ElementTree.fromstring(
            response.content
        )

        news = []

        for item in root.findall(
            ".//item"
        ):

            title = (
                item.findtext("title")
                or ""
            ).strip()

            link = (
                item.findtext("link")
                or ""
            ).strip()

            pub_date = (
                item.findtext("pubDate")
                or ""
            )

            from email.utils import (
                parsedate_to_datetime
            )

            try:

                published = (
                    parsedate_to_datetime(
                        pub_date
                    )
                )

                if published.tzinfo is None:
                    published = published.replace(
                        tzinfo=timezone.utc
                    )

                published = published.astimezone(
                    timezone.utc
                )

            except Exception:
                continue

            if published < cutoff:
                continue

            source_node = item.find(
                "source"
            )

            source = (
                source_node.text
                if source_node is not None
                else "News"
            )

            description = (
                item.findtext(
                    "description"
                )
                or ""
            )

            news.append({

                "title":
                    title,

                "description":
                    description[:500],

                "source":
                    source,

                "published_at":
                    published.isoformat(),

                "url":
                    link
            })

        return news[:50]

    except Exception as error:

        print(
            "Worldwide RSS error:",
            error
        )

        return []


@router.get("")
def get_trending(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):

    if current_user.state_id is None:

        return {
            "state_topics": [],
            "worldwide_topics": [],
            "state":
                None
        }

    state_name = STATE_NAMES.get(
        current_user.state_id
    )

    if not state_name:

        return {
            "state_topics": [],
            "worldwide_topics": [],
            "state":
                None
        }

    # -------------------------
    # STATE NEWS
    # -------------------------

    state_payload = (
        fetch_recent_content(
            state_name
        )
    )

    state_news = [
        item
        for item in state_payload.get(
            "items",
            []
        )
        if item.get(
            "content_type"
        ) == "news"
    ]

    # -------------------------
    # AI STATE TOPICS
    # -------------------------

    state_topics = (
        generate_state_topics(
            state_name,
            state_news
        )
    )

    # -------------------------
    # WORLD NEWS
    # -------------------------

    world_news = fetch_world_news()

    # -------------------------
    # AI WORLD TOPICS
    # -------------------------

    worldwide_topics = (
        generate_worldwide_topics(
            world_news
        )
    )

    return {

        "state":
            state_name,

        "state_topics":
            state_topics,

        "worldwide_topics":
            worldwide_topics,

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat()
    }