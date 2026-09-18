"""
Content fetching for Political Tea.

Sources:
  - Google News RSS  -> news
  - YouTube          -> video  (Data API if YOUTUBE_API_KEY is set,
                                otherwise a Google News site: fallback)
  - Blog / opinion   -> blog
  - Worldwide RSS    -> news
"""

import hashlib
import html
import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
from xml.etree import ElementTree

import requests


RSS_TIMEOUT_SECONDS = 10
YOUTUBE_TIMEOUT_SECONDS = 10
MAX_ITEMS = 30
WINDOW_HOURS = 24

USER_AGENT = (
    "Mozilla/5.0 (compatible; PoliticalTea/1.0; RSS Reader)"
)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

MEDIA_NS = "{http://search.yahoo.com/mrss/}content"

BLOG_SITES = [
    "thewire.in",
    "scroll.in",
    "theprint.in",
    "newslaundry.com",
    "medium.com",
    "substack.com",
    "blogspot.com",
    "wordpress.com",
]


STATE_SEARCH_TERMS = {
    "Uttar Pradesh": ["Uttar Pradesh", "Lucknow", "Kanpur", "Varanasi"],
    "Delhi": ["Delhi", "New Delhi", "Noida", "Gurugram"],
    "Maharashtra": ["Maharashtra", "Mumbai", "Pune", "Nagpur"],
    "Rajasthan": ["Rajasthan", "Jaipur", "Jodhpur", "Udaipur"],
    "Bihar": ["Bihar", "Patna", "Gaya", "Muzaffarpur"],
    "Jharkhand": ["Jharkhand", "Ranchi", "Jamshedpur", "Dhanbad"],
    "Madhya Pradesh": ["Madhya Pradesh", "Bhopal", "Indore", "Gwalior"],
    "West Bengal": ["West Bengal", "Kolkata", "Siliguri", "Howrah"],
    "Tamil Nadu": ["Tamil Nadu", "Chennai", "Coimbatore", "Madurai"],
    "Karnataka": ["Karnataka", "Bengaluru", "Mysuru", "Mangaluru"],
    "Gujarat": ["Gujarat", "Ahmedabad", "Surat", "Vadodara"],
    "Haryana": ["Haryana", "Chandigarh", "Gurugram", "Faridabad"],
}

SUBJECT_TERMS = (
    "politics OR government OR election OR minister OR "
    "assembly OR policy OR protest OR development OR "
    "political OR scheme"
)


# =====================================================
# QUERY BUILDERS
# =====================================================

def _location_clause(state_name):
    locations = STATE_SEARCH_TERMS.get(state_name, [state_name])

    return " OR ".join(
        f'"{location}"' for location in locations
    )


def state_query(state_name):
    return f"({_location_clause(state_name)}) AND ({SUBJECT_TERMS})"


def blog_query(state_name):
    sites = " OR ".join(
        f"site:{site}" for site in BLOG_SITES
    )

    return (
        f"({_location_clause(state_name)}) "
        f"AND (opinion OR analysis OR blog OR column) "
        f"AND ({sites})"
    )


def google_news_url(query, region="IN", language="en-IN"):
    country = region
    return (
        "https://news.google.com/rss/search?"
        f"q={quote_plus(query)}"
        f"&hl={language}"
        f"&gl={country}"
        f"&ceid={country}:en"
    )


def feed_urls(state_name):
    """(source_name, content_type, url) tuples for one state."""

    feeds = [
        (
            "Google News",
            "news",
            google_news_url(state_query(state_name)),
        ),
        (
            "Blogs",
            "blog",
            google_news_url(blog_query(state_name)),
        ),
    ]

    # Only used when the YouTube Data API key is missing.
    if not os.getenv("YOUTUBE_API_KEY"):
        feeds.append((
            "YouTube",
            "video",
            google_news_url(
                f'({_location_clause(state_name)}) '
                f'AND (politics OR news) AND site:youtube.com'
            ),
        ))

    return feeds


def worldwide_feed_urls():
    return [
        (
            "Worldwide News",
            "news",
            google_news_url(
                "(politics OR election OR government OR protest OR "
                "conflict OR war OR economy OR technology OR climate)",
                region="US",
                language="en-US",
            ),
        ),
        (
            "Worldwide Politics",
            "news",
            google_news_url(
                "(world politics OR international relations OR "
                "geopolitics OR summit OR sanctions)",
                region="US",
                language="en-US",
            ),
        ),
    ]


# =====================================================
# PARSING HELPERS
# =====================================================

def parse_date(value):
    if not value:
        return None

    try:
        parsed = parsedate_to_datetime(value)

    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except ValueError:
            return None

    if parsed is None:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def clean_text(value):
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_image(value):
    match = re.search(
        r"<img[^>]+src=[\"']([^\"']+)[\"']",
        value or "",
        re.IGNORECASE,
    )

    return html.unescape(match.group(1)) if match else None


def parse_views(text):
    match = re.search(
        r"([\d,.]+)\s*(K|M|B)?\s+views",
        text or "",
        re.IGNORECASE,
    )

    if not match:
        return 0

    multiplier = {
        "K": 1_000,
        "M": 1_000_000,
        "B": 1_000_000_000,
    }.get((match.group(2) or "").upper(), 1)

    try:
        return int(float(match.group(1).replace(",", "")) * multiplier)
    except ValueError:
        return 0


def item_id(url, title):
    key = (url or title or "").strip().lower()
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def dedupe_key(item):
    """Google News links differ per feed, so also fold on the title."""
    title = re.sub(r"[^a-z0-9]+", "", (item.get("title") or "").lower())
    return title[:90] or item["url"]


# =====================================================
# RSS
# =====================================================

def fetch_feed(source_name, content_type, url, now, hours=WINDOW_HOURS):
    """Return a list of normalised item dicts. Raises on network/XML errors."""

    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=RSS_TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    root = ElementTree.fromstring(response.content)

    items = []
    cutoff = now - timedelta(hours=hours)

    for node in root.findall(".//item"):

        title = clean_text(node.findtext("title"))
        link = (node.findtext("link") or "").strip()
        published_at = parse_date(node.findtext("pubDate"))

        if not title or not link or not published_at:
            continue

        if published_at < cutoff:
            continue

        source_node = node.find("source")

        publisher = clean_text(
            source_node.text if source_node is not None else ""
        )

        raw_description = node.findtext("description") or ""
        description = clean_text(raw_description)

        image = extract_image(raw_description)

        media = node.find(MEDIA_NS)
        enclosure = node.find("enclosure")

        if media is not None and media.attrib.get("url"):
            image = media.attrib["url"]
        elif enclosure is not None and enclosure.attrib.get("url"):
            image = enclosure.attrib["url"]

        lowered = link.lower()

        is_video = (
            content_type == "video"
            or "youtube.com" in lowered
            or "youtu.be" in lowered
        )

        items.append({
            "id": item_id(link, title),
            "title": title,
            "url": link,
            "source": publisher or source_name,
            "feed": source_name,
            "content_type": "video" if is_video else content_type,
            "published_at": published_at.isoformat(),
            "description": description[:500],
            "image": image,
            "youtube_views": parse_views(description),
        })

    return items


# =====================================================
# YOUTUBE DATA API
# =====================================================

def fetch_youtube_videos(state_name, now, hours=WINDOW_HOURS, limit=15):
    """Real YouTube results when YOUTUBE_API_KEY is set, else []."""

    api_key = os.getenv("YOUTUBE_API_KEY")

    if not api_key:
        return []

    published_after = (
        (now - timedelta(hours=hours))
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    search = requests.get(
        YOUTUBE_SEARCH_URL,
        params={
            "key": api_key,
            "part": "snippet",
            "type": "video",
            "order": "relevance",
            "maxResults": limit,
            "regionCode": "IN",
            "relevanceLanguage": "en",
            "publishedAfter": published_after,
            "q": f"{state_name} politics news",
        },
        timeout=YOUTUBE_TIMEOUT_SECONDS,
    )

    search.raise_for_status()

    entries = search.json().get("items", [])

    video_ids = [
        entry["id"]["videoId"]
        for entry in entries
        if entry.get("id", {}).get("videoId")
    ]

    views = {}

    if video_ids:
        stats = requests.get(
            YOUTUBE_VIDEOS_URL,
            params={
                "key": api_key,
                "part": "statistics",
                "id": ",".join(video_ids),
            },
            timeout=YOUTUBE_TIMEOUT_SECONDS,
        )

        if stats.ok:
            for video in stats.json().get("items", []):
                views[video["id"]] = int(
                    video.get("statistics", {}).get("viewCount", 0)
                )

    items = []

    for entry in entries:

        video_id = entry.get("id", {}).get("videoId")
        snippet = entry.get("snippet", {})

        if not video_id or not snippet:
            continue

        published_at = parse_date(snippet.get("publishedAt"))

        if not published_at:
            continue

        url = f"https://www.youtube.com/watch?v={video_id}"

        thumbnails = snippet.get("thumbnails", {})

        thumbnail = (
            thumbnails.get("high")
            or thumbnails.get("medium")
            or thumbnails.get("default")
            or {}
        )

        items.append({
            "id": item_id(url, snippet.get("title", "")),
            "title": clean_text(snippet.get("title")),
            "url": url,
            "source": clean_text(snippet.get("channelTitle")) or "YouTube",
            "feed": "YouTube",
            "content_type": "video",
            "published_at": published_at.isoformat(),
            "description": clean_text(snippet.get("description"))[:500],
            "image": thumbnail.get("url"),
            "youtube_views": views.get(video_id, 0),
        })

    return items


# =====================================================
# SCORING
# =====================================================

def score_items(items, now, limit=MAX_ITEMS):

    if not items:
        return []

    source_counts = Counter(item.get("source", "") for item in items)

    topic_counts = Counter()

    for item in items:
        words = re.findall(r"[a-zA-Z]{5,}", item.get("title", "").lower())
        topic_counts.update(set(words))

    for item in items:

        published_at = parse_date(item.get("published_at")) or now

        hours_old = max(
            0.0,
            (now - published_at).total_seconds() / 3600,
        )

        recency_score = max(0, 60 - int(hours_old * 2.5))

        words = set(
            re.findall(r"[a-zA-Z]{5,}", item.get("title", "").lower())
        )

        topic_score = sum(topic_counts[word] for word in words)

        item["trending_score"] = (
            recency_score
            + min(source_counts[item.get("source", "")] * 10, 30)
            + min(topic_score * 2, 30)
            + min(item.get("youtube_views", 0) // 1000, 20)
        )

    return sorted(
        items,
        key=lambda item: (
            item["trending_score"],
            item.get("published_at", ""),
        ),
        reverse=True,
    )[:limit]


# =====================================================
# PUBLIC FETCHERS
# =====================================================

def _collect(feeds, now, errors):
    unique = {}

    for source_name, content_type, url in feeds:
        try:
            for item in fetch_feed(source_name, content_type, url, now):
                unique.setdefault(dedupe_key(item), item)

        except (requests.RequestException, ElementTree.ParseError) as error:
            errors.append(f"{source_name}: {error}")

    return unique


def fetch_recent_content(state_name):

    now = datetime.now(timezone.utc)
    errors = []

    unique = _collect(feed_urls(state_name), now, errors)

    try:
        for item in fetch_youtube_videos(state_name, now):
            unique.setdefault(dedupe_key(item), item)

    except (requests.RequestException, ValueError, KeyError) as error:
        errors.append(f"YouTube API: {error}")

    items = score_items(list(unique.values()), now)

    return {
        "items": items,
        "fetched_at": now.isoformat(),
        "source_errors": errors,
    }


def fetch_worldwide_content():

    now = datetime.now(timezone.utc)
    errors = []

    unique = _collect(worldwide_feed_urls(), now, errors)

    items = score_items(list(unique.values()), now)

    return {
        "items": items,
        "fetched_at": now.isoformat(),
        "source_errors": errors,
    }


# =====================================================
# CACHE HELPERS
# =====================================================

def utc_naive_now():
    """Naive UTC, so it matches whatever is already in the cache column."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def is_fresh(fetched_at, minutes=15):

    if not fetched_at:
        return False

    if isinstance(fetched_at, str):
        fetched_at = parse_date(fetched_at)

        if fetched_at is None:
            return False

    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)

    return (now - fetched_at) < timedelta(minutes=minutes)


def serialize(payload):
    return json.dumps(payload, ensure_ascii=False)


def deserialize(payload):
    if not payload:
        return {"items": [], "fetched_at": None, "source_errors": []}

    try:
        data = json.loads(payload)
    except (TypeError, ValueError):
        return {"items": [], "fetched_at": None, "source_errors": []}

    data.setdefault("items", [])
    data.setdefault("source_errors", [])

    return data


def sanitize_payload(payload):

    for item in payload.get("items", []):
        item["title"] = clean_text(item.get("title"))
        item["description"] = clean_text(item.get("description"))[:500]
        item["source"] = clean_text(item.get("source"))

    return payload