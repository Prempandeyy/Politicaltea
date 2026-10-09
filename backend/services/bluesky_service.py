import asyncio
import os
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

from atproto import Client
from dotenv import load_dotenv


# Load credentials from the project's .env file.
load_dotenv()


# ---------------------------------------------------------
# STATE CONFIGURATION
# ---------------------------------------------------------

STATE_CONFIG = {
    1: {
        "name": "Uttar Pradesh",
        "terms": [
            "Uttar Pradesh", "UP politics", "Lucknow",
            "Yogi Adityanath", "Samajwadi Party", "Akhilesh Yadav",
            "BSP", "Mayawati", "UP BJP", "UP Congress",
            "Prayagraj", "Kanpur", "Varanasi", "Ayodhya",
            "Gorakhpur", "Meerut", "Bareilly", "Agra",
        ],
    },
    2: {
        "name": "Delhi",
        "terms": [
            "Delhi politics", "Delhi government", "New Delhi",
            "Delhi BJP", "Delhi Congress", "AAP Delhi",
            "Rekha Gupta", "Arvind Kejriwal", "Atishi",
            "Delhi Assembly", "Delhi CM", "Delhi minister",
        ],
    },
    3: {
        "name": "Maharashtra",
        "terms": [
            "Maharashtra politics", "Mumbai politics",
            "Maharashtra government", "Maharashtra BJP",
            "Maharashtra Congress", "Shiv Sena", "NCP",
            "Devendra Fadnavis", "Eknath Shinde",
            "Uddhav Thackeray", "Nagpur politics", "Pune politics",
        ],
    },
    4: {
        "name": "Rajasthan",
        "terms": [
            "Rajasthan politics", "Jaipur politics",
            "Rajasthan government", "Rajasthan BJP",
            "Rajasthan Congress", "Bhajan Lal Sharma",
            "Ashok Gehlot", "Sachin Pilot", "Jodhpur politics",
        ],
    },
    5: {
        "name": "Bihar",
        "terms": [
            "Bihar politics", "Patna politics",
            "Bihar government", "Bihar BJP", "Bihar Congress",
            "Nitish Kumar", "Tejashwi Yadav", "RJD",
            "JDU", "Bihar Assembly", "Chirag Paswan",
        ],
    },
    6: {
        "name": "Jharkhand",
        "terms": [
            "Jharkhand politics", "Ranchi politics",
            "Jharkhand government", "Jharkhand BJP",
            "Jharkhand Congress", "Hemant Soren",
            "Champai Soren", "JMM", "Jharkhand Assembly",
        ],
    },
    7: {
        "name": "Madhya Pradesh",
        "terms": [
            "Madhya Pradesh politics", "MP politics",
            "Bhopal politics", "MP government",
            "Madhya Pradesh BJP", "Madhya Pradesh Congress",
            "Mohan Yadav", "Kamal Nath", "MP Assembly",
            "Indore politics", "Gwalior politics",
        ],
    },
    8: {
        "name": "West Bengal",
        "terms": [
            "West Bengal politics", "Kolkata politics",
            "Bengal government", "West Bengal BJP",
            "Trinamool Congress", "TMC", "Mamata Banerjee",
            "Suvendu Adhikari", "West Bengal Assembly",
        ],
    },
    9: {
        "name": "Tamil Nadu",
        "terms": [
            "Tamil Nadu politics", "Chennai politics",
            "Tamil Nadu government", "Tamil Nadu BJP",
            "DMK", "AIADMK", "M K Stalin",
            "Edappadi Palaniswami", "Tamil Nadu Assembly",
        ],
    },
    10: {
        "name": "Karnataka",
        "terms": [
            "Karnataka politics", "Bengaluru politics",
            "Karnataka government", "Karnataka BJP",
            "Karnataka Congress", "Siddaramaiah",
            "D K Shivakumar", "Karnataka Assembly",
            "Mysuru politics",
        ],
    },
    11: {
        "name": "Gujarat",
        "terms": [
            "Gujarat politics", "Ahmedabad politics",
            "Gujarat government", "Gujarat BJP",
            "Gujarat Congress", "Bhupendra Patel",
            "Gujarat Assembly", "Surat politics",
        ],
    },
    12: {
        "name": "Haryana",
        "terms": [
            "Haryana politics", "Haryana government",
            "Chandigarh politics", "Haryana BJP",
            "Haryana Congress", "Nayab Singh Saini",
            "Bhupinder Hooda", "Haryana Assembly",
            "Gurugram politics", "Hisar politics",
        ],
    },
}


# ---------------------------------------------------------
# POLITICS FILTER
# ---------------------------------------------------------

POLITICS_KEYWORDS = [
    "politics",
    "political",
    "government",
    "governance",
    "chief minister",
    "prime minister",
    "minister",
    "ministry",
    "mla",
    "mp",
    "member of parliament",
    "assembly",
    "parliament",
    "legislature",
    "opposition",
    "ruling party",
    "political party",
    "election",
    "electoral",
    "manifesto",
    "campaign",
    "ballot",
    "voting",
    "vote",
    "bjp",
    "congress",
    "aam aadmi party",
    "aap",
    "samajwadi party",
    "bahujan samaj party",
    "bsp",
    "trinamool congress",
    "tmc",
    "dmk",
    "aiadmk",
    "rjd",
    "jdu",
    "jmm",
    "shiv sena",
    "ncp",
    "cabinet",
    "policy",
    "public policy",
    "government scheme",
    "budget",
    "bill passed",
    "ordinance",
    "reservation",
    "political rally",
    "press conference",
    "no confidence",
    "floor test",
    "party spokesperson",
    "political leader",
    "constituency",
    "by-election",
    "by-election",
    "coalition",
    "corruption allegation",
    "governor",
    "municipal election",
    "panchayat election",
]


# Basic spam signals. These are heuristics, not proof of authenticity.
URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
REPEATED_CHAR_PATTERN = re.compile(r"(.)\1{7,}")
HASHTAG_PATTERN = re.compile(r"(?<!\w)#\w+")


# ---------------------------------------------------------
# CREDENTIALS AND TRUSTED HANDLES
# ---------------------------------------------------------

def get_bluesky_credentials():
    """
    Required .env variables:

    BLUESKY_IDENTIFIER=your-handle.bsky.social
    BLUESKY_APP_PASSWORD=your-generated-app-password

    Never expose these credentials in frontend code.
    """
    load_dotenv(override=False)

    identifier = os.getenv("BLUESKY_IDENTIFIER", "").strip()
    app_password = os.getenv("BLUESKY_APP_PASSWORD", "").strip()

    if not identifier or not app_password:
        raise ValueError(
            "Bluesky credentials are missing. Set "
            "BLUESKY_IDENTIFIER and BLUESKY_APP_PASSWORD "
            "in your backend .env file."
        )

    return identifier, app_password


def get_trusted_handles():
    """
    Optional comma-separated list in .env:

    BLUESKY_TRUSTED_HANDLES=handle1.bsky.social,handle2.bsky.social

    Add only accounts you have independently reviewed.
    """
    raw = os.getenv("BLUESKY_TRUSTED_HANDLES", "")
    return {
        handle.strip().lower().lstrip("@")
        for handle in raw.split(",")
        if handle.strip()
    }


# ---------------------------------------------------------
# TEXT AND DATE HELPERS
# ---------------------------------------------------------

def normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_keyword(text: str, keyword: str) -> bool:
    """
    Match whole words for short terms such as MP, UP and AAP,
    reducing accidental matches inside unrelated words.
    """
    text = normalize_text(text)
    keyword = normalize_text(keyword)

    if not text or not keyword:
        return False

    pattern = (
        r"(?<!\w)"
        + re.escape(keyword).replace(r"\ ", r"\s+")
        + r"(?!\w)"
    )
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def is_politics_related(text: str) -> bool:
    if not text or len(text.strip()) < 25:
        return False

    return any(
        contains_keyword(text, keyword)
        for keyword in POLITICS_KEYWORDS
    )


def is_state_related(text: str, state_terms: list[str]) -> bool:
    if not text:
        return False

    return any(
        contains_keyword(text, term)
        for term in state_terms
    )


def parse_datetime(value: Any):
    if not value:
        return None

    if isinstance(value, datetime):
        dt = value
    else:
        try:
            value = str(value).strip()
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            dt = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def build_post_url(handle: str, uri: str) -> str | None:
    if not handle or not uri:
        return None

    # AT Protocol post URIs look like:
    # at://did:plc:.../app.bsky.feed.post/POST_ID
    parts = uri.rstrip("/").split("/")
    post_id = parts[-1] if parts else ""

    if not post_id:
        return None

    return f"https://bsky.app/profile/{handle}/post/{post_id}"


def looks_like_spam(text: str) -> bool:
    text = (text or "").strip()

    if len(text) < 25:
        return True

    if REPEATED_CHAR_PATTERN.search(text):
        return True

    hashtags = HASHTAG_PATTERN.findall(text)
    if len(hashtags) > 10:
        return True

    urls = URL_PATTERN.findall(text)
    if len(urls) > 4:
        return True

    # Very low text-to-link ratio is often promotional.
    clean_text = URL_PATTERN.sub("", text).strip()
    if len(urls) >= 3 and len(clean_text) < 40:
        return True

    return False


def get_source_quality(handle: str, trusted_handles: set[str]) -> str:
    if handle and handle.lower().lstrip("@") in trusted_handles:
        return "trusted"

    return "unreviewed"


# ---------------------------------------------------------
# BLUESKY SEARCH
# ---------------------------------------------------------

def fetch_posts_sync(state_id: int) -> dict:
    if state_id not in STATE_CONFIG:
        raise ValueError(
            f"Invalid state_id: {state_id}. "
            f"Allowed IDs: {', '.join(map(str, STATE_CONFIG.keys()))}"
        )

    identifier, app_password = get_bluesky_credentials()
    state = STATE_CONFIG[state_id]
    trusted_handles = get_trusted_handles()

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    client = Client()

    try:
        client.login(identifier, app_password)
    except Exception as exc:
        raise RuntimeError(
            "Bluesky login failed. Check BLUESKY_IDENTIFIER and "
            "BLUESKY_APP_PASSWORD in your backend .env file. "
            "Use a Bluesky App Password, not your main password."
        ) from exc

    posts_by_uri = {}

    # Search terms are state-related; political filtering happens
    # locally after each result is returned.
    #
    # A small number of searches helps limit API calls.
    search_terms = state["terms"][:12]

    for term in search_terms:
        query = f'"{term}"'

        try:
            response = client.app.bsky.feed.search_posts(
                params={
                    "q": query,
                    "sort": "latest",
                    "since": cutoff.strftime("%Y-%m-%d"),
                    "until": now.strftime("%Y-%m-%d"),
                    "limit": 50,
                }
            )
        except Exception:
            # One failed search should not discard results from
            # other state-specific searches.
            continue

        for post in getattr(response, "posts", []) or []:
            record = getattr(post, "record", None)
            text = getattr(record, "text", "") or ""

            # 1. Only political posts.
            if not is_politics_related(text):
                continue

            # 2. Require a clear state-related term in the post.
            if not is_state_related(text, state["terms"]):
                continue

            # 3. Remove obvious spam.
            if looks_like_spam(text):
                continue

            # 4. Keep only posts from the last 24 hours.
            created_at = (
                getattr(record, "created_at", None)
                or getattr(post, "indexed_at", None)
            )
            created_dt = parse_datetime(created_at)

            if created_dt is None or not (cutoff <= created_dt <= now):
                continue

            uri = getattr(post, "uri", None)
            if not uri:
                continue

            # 5. Avoid duplicate posts returned by different searches.
            if uri in posts_by_uri:
                continue

            author_obj = getattr(post, "author", None)
            handle = getattr(author_obj, "handle", "") or ""
            display_name = getattr(author_obj, "display_name", "") or ""

            author_did = getattr(author_obj, "did", None)
            post_url = build_post_url(handle, uri)

            # Bluesky search results do not prove that a post is true.
            # Only label an account trusted if it is in the manual allowlist.
            source_quality = get_source_quality(
                handle,
                trusted_handles,
            )

            posts_by_uri[uri] = {
                "id": uri,
                "uri": uri,
                "platform": "bluesky",
                "state_id": state_id,
                "state": state["name"],
                "text": text,
                "author": display_name or handle or "Unknown",
                "handle": handle,
                "author_did": author_did,
                "created_at": created_dt.isoformat(),
                "url": post_url,
                "source_quality": source_quality,
                "like_count": getattr(post, "like_count", 0) or 0,
                "repost_count": getattr(post, "repost_count", 0) or 0,
                "reply_count": getattr(post, "reply_count", 0) or 0,
                "quote_count": getattr(post, "quote_count", 0) or 0,
            }

    items = list(posts_by_uri.values())

    # Trusted accounts first; within each group, newest posts first.
    items.sort(
        key=lambda item: (
            item["source_quality"] == "trusted",
            item["created_at"],
        ),
        reverse=True,
    )

    return {
        "state_id": state_id,
        "state": state["name"],
        "period_hours": 24,
        "fetched_at": now.isoformat(),
        "count": len(items),
        "items": items,
        "source": "Bluesky authenticated search",
        "message": (
            "Political posts from the last 24 hours, filtered for "
            "state relevance and basic spam signals. "
            "Trusted status reflects your manual allowlist, not "
            "independent verification of the post's claims."
        ),
    }


# ---------------------------------------------------------
# ASYNC FUNCTION FOR FASTAPI
# ---------------------------------------------------------

async def fetch_bluesky_posts(state_id: int) -> dict:
    """
    Call this from an async FastAPI endpoint.

    The synchronous Bluesky SDK work runs in a worker thread
    so it does not block the event loop.
    """
    return await asyncio.to_thread(fetch_posts_sync, state_id)
