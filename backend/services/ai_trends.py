"""
Political Tea - AI Hot Topic Generation

Uses OpenRouter for AI-generated trends and a deterministic
fallback when the AI call is unavailable or fails.
"""

import json
import os
import re
from collections import Counter
from typing import Any

import requests


# =========================================================
# CONFIG
# =========================================================

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-4o-mini",
)

OPENROUTER_FALLBACK_MODEL = os.getenv(
    "OPENROUTER_FALLBACK_MODEL",
    "meta-llama/llama-3.1-8b-instruct",
)

APP_URL = os.getenv(
    "APP_URL",
    "http://localhost",
)

REQUEST_TIMEOUT = 45

STATE_TOPIC_LIMIT = 6
WORLD_TOPIC_LIMIT = 5


CHANGE_LABELS = {
    "Rising",
    "Hot",
    "High attention",
    "Fast rising",
}


# =========================================================
# STOPWORDS
# =========================================================

STOPWORDS = {
    # English
    "after",
    "about",
    "against",
    "amid",
    "among",
    "being",
    "before",
    "could",
    "first",
    "front",
    "their",
    "there",
    "these",
    "those",
    "today",
    "under",
    "which",
    "while",
    "would",
    "should",
    "says",
    "said",
    "over",
    "with",
    "from",
    "that",
    "this",
    "news",
    "latest",
    "update",
    "updates",
    "video",
    "watch",
    "report",
    "reports",
    "state",
    "india",
    "indian",
    "government",
    "minister",
    "ministers",
    "people",
    "party",
    "political",
    "politics",

    # Common Hindi/Hinglish
    "aaj",
    "abhi",
    "bada",
    "badi",
    "bade",
    "news",
    "kaha",
    "kahan",
    "liye",
    "sarkar",
    "sarkari",
    "rajya",
    "desh",
    "desh mein",
    "mukhyamantri",
    "mantri",
    "netaji",
    "neta",
    "chunav",
    "election",
    "samachar",
    "khabar",
    "khabrein",
}


# =========================================================
# TEXT HELPERS
# =========================================================

def _clean_text(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()


def _clean_json(text: str) -> str:
    """
    Cleans common markdown/prose wrappers around JSON.
    """

    text = _clean_text(text)

    if not text:
        raise ValueError("Empty AI response")

    # Remove markdown fences
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^```\s*",
        "",
        text,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    text = text.strip()

    # Extract outer JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return text.strip()


def _safe_source(article: dict[str, Any]) -> str:
    source = article.get("source", "")

    if isinstance(source, dict):
        return _clean_text(
            source.get("name")
            or source.get("title")
            or ""
        )

    return _clean_text(source)


# =========================================================
# ARTICLE COMPRESSION
# =========================================================

def _compact(
    articles: list[dict[str, Any]],
    limit: int = 20,
) -> list[dict[str, Any]]:

    compact = []

    for article in (articles or [])[:limit]:

        if not isinstance(article, dict):
            continue

        title = _clean_text(
            article.get("title")
        )

        if not title:
            continue

        description = _clean_text(
            article.get("description")
        )

        published_at = _clean_text(
            article.get("published_at")
            or article.get("publishedAt")
            or article.get("time")
        )

        compact.append(
            {
                "title": title[:300],
                "source": _safe_source(article),
                "published_at": published_at,
                "description": description[:300],
            }
        )

    return compact


# =========================================================
# AI TOPIC NORMALISATION
# =========================================================

def _normalise_topics(
    topics: Any,
    limit: int,
) -> list[dict[str, str]]:

    cleaned = []
    seen = set()

    if not isinstance(topics, list):
        return cleaned

    for topic in topics:

        if isinstance(topic, str):
            title = _clean_text(topic)

            topic = {
                "title": title,
                "mentions": "",
                "change": "Rising",
            }

        if not isinstance(topic, dict):
            continue

        title = _clean_text(
            topic.get("title")
            or topic.get("topic")
            or topic.get("name")
        )

        if not title:
            continue

        normalized_key = title.lower()

        if normalized_key in seen:
            continue

        seen.add(normalized_key)

        mentions = _clean_text(
            topic.get("mentions")
            or topic.get("reason")
            or topic.get("description")
        )

        change = _clean_text(
            topic.get("change")
        )

        if change not in CHANGE_LABELS:
            change = "Rising"

        cleaned.append(
            {
                "title": title[:90],
                "mentions": mentions[:200],
                "change": change,
            }
        )

        if len(cleaned) >= limit:
            break

    return cleaned


# =========================================================
# DETERMINISTIC FALLBACK
# =========================================================

def _extract_keywords(title: str) -> list[str]:

    title = _clean_text(title).lower()

    # English words
    english_words = re.findall(
        r"[a-zA-Z]{4,}",
        title,
    )

    # Hindi Unicode words
    hindi_words = re.findall(
        r"[\u0900-\u097F]{3,}",
        title,
    )

    words = english_words + hindi_words

    return [
        word
        for word in words
        if word not in STOPWORDS
    ]


def _fallback_topics(
    articles: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, str]]:

    articles = articles or []

    if not articles:
        return []

    keyword_counts = Counter()

    for article in articles:

        title = _clean_text(
            article.get("title")
        )

        if not title:
            continue

        words = set(
            _extract_keywords(title)
        )

        keyword_counts.update(words)

    topics = []

    used_titles = set()

    for keyword, count in keyword_counts.most_common(50):

        if len(topics) >= limit:
            break

        match = None

        for article in articles:

            title = _clean_text(
                article.get("title")
            )

            if not title:
                continue

            if title in used_titles:
                continue

            if keyword.lower() in title.lower():

                match = article
                break

        if not match:
            continue

        title = _clean_text(
            match.get("title")
        )

        used_titles.add(title)

        source = _safe_source(match)

        if count >= 3:
            change = "Hot"
        elif count >= 2:
            change = "High attention"
        else:
            change = "Rising"

        if count > 1:
            mentions = (
                f"Multiple headlines are focusing on this issue."
            )
        elif source:
            mentions = (
                f"Reported by {source}."
            )
        else:
            mentions = (
                "A recent story is drawing attention."
            )

        topics.append(
            {
                "title": title[:90],
                "mentions": mentions[:200],
                "change": change,
            }
        )

    return topics


# =========================================================
# PROMPT
# =========================================================

def _build_prompt(
    state_name: str,
    state_data: list[dict[str, Any]],
    worldwide_data: list[dict[str, Any]],
) -> str:

    return f"""
You are the AI trend engine for Political Tea.

Analyze ONLY the news supplied below.

STATE:
{state_name}

STATE NEWS:
{json.dumps(
    state_data,
    ensure_ascii=False,
    indent=2,
)}

WORLDWIDE NEWS:
{json.dumps(
    worldwide_data,
    ensure_ascii=False,
    indent=2,
)}

TASK:

1. Identify up to {STATE_TOPIC_LIMIT} important/trending topics
   from the STATE NEWS.

2. Identify up to {WORLD_TOPIC_LIMIT} important/trending topics
   from the WORLDWIDE NEWS.

3. Use ONLY the supplied articles.

4. Do not invent facts.

5. Do not use outside knowledge.

6. Merge duplicate or highly similar stories.

7. Prefer significant:
   - politics
   - government decisions
   - elections
   - protests
   - public issues
   - major policy decisions
   - international affairs
   - major world events

8. Keep titles short and engaging.

9. "mentions" should briefly explain why the topic is receiving attention.

10. Never fabricate percentages or statistics.

11. "change" MUST be exactly one of:
   "Rising"
   "Hot"
   "High attention"
   "Fast rising"

12. If there are fewer valid topics, return fewer topics.
   Do not invent topics to reach the limit.

Return ONLY valid JSON.

Format:

{{
    "state_topics": [
        {{
            "title": "Short topic title",
            "mentions": "Short reason",
            "change": "Rising"
        }}
    ],
    "worldwide_topics": [
        {{
            "title": "Short worldwide topic",
            "mentions": "Short reason",
            "change": "Hot"
        }}
    ]
}}
"""


# =========================================================
# OPENROUTER
# =========================================================

def _call_openrouter(
    api_key: str,
    model: str,
    prompt: str,
) -> dict[str, Any]:

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": APP_URL,
            "X-Title": "Political Tea",
        },
        json={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a factual news trend analyzer. "
                        "Return valid JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.2,
        },
        timeout=REQUEST_TIMEOUT,
    )

    # Give a useful error instead of generic raise_for_status()
    if not response.ok:

        try:
            error_data = response.json()
        except Exception:
            error_data = response.text

        raise RuntimeError(
            f"HTTP {response.status_code}: {error_data}"
        )

    result = response.json()

    if not isinstance(result, dict):
        raise RuntimeError(
            "Invalid OpenRouter response"
        )

    choices = result.get("choices")

    if not choices:
        raise RuntimeError(
            f"OpenRouter returned no choices: {result}"
        )

    message = choices[0].get("message", {})

    content = message.get("content")

    # Some providers can return structured content
    if isinstance(content, list):

        text_parts = []

        for item in content:

            if isinstance(item, dict):

                text = item.get("text")

                if text:
                    text_parts.append(
                        str(text)
                    )

        content = "".join(text_parts)

    if not content:
        raise RuntimeError(
            "OpenRouter returned empty content"
        )

    cleaned = _clean_json(
        str(content)
    )

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Invalid JSON from {model}: {error}"
        )

    if not isinstance(parsed, dict):
        raise RuntimeError(
            "AI response is not a JSON object"
        )

    return parsed


# =========================================================
# PUBLIC FUNCTION
# =========================================================

def generate_ai_trends(
    state_name: str,
    state_news: list[dict[str, Any]],
    worldwide_news: list[dict[str, Any]],
) -> dict[str, Any]:

    state_data = _compact(
        state_news
    )

    worldwide_data = _compact(
        worldwide_news
    )

    # -----------------------------------------------------
    # No news
    # -----------------------------------------------------

    if not state_data and not worldwide_data:

        return {
            "state_topics": [],
            "worldwide_topics": [],
            "ai": False,
            "error": (
                "No news available in the last 24 hours"
            ),
        }

    # -----------------------------------------------------
    # OpenRouter
    # -----------------------------------------------------

    api_key = os.getenv(
        "OPENROUTER_API_KEY"
    )

    last_error = None

    if api_key:

        prompt = _build_prompt(
            state_name,
            state_data,
            worldwide_data,
        )

        models = [
            OPENROUTER_MODEL,
        ]

        if (
            OPENROUTER_FALLBACK_MODEL
            and OPENROUTER_FALLBACK_MODEL
            != OPENROUTER_MODEL
        ):
            models.append(
                OPENROUTER_FALLBACK_MODEL
            )

        for model in models:

            try:

                data = _call_openrouter(
                    api_key,
                    model,
                    prompt,
                )

                state_topics = _normalise_topics(
                    data.get("state_topics", []),
                    STATE_TOPIC_LIMIT,
                )

                worldwide_topics = _normalise_topics(
                    data.get("worldwide_topics", []),
                    WORLD_TOPIC_LIMIT,
                )

                if (
                    state_topics
                    or worldwide_topics
                ):

                    return {
                        "state_topics": state_topics,
                        "worldwide_topics": worldwide_topics,
                        "ai": True,
                        "error": None,
                    }

                last_error = (
                    f"{model}: AI returned empty topics"
                )

            except Exception as error:

                last_error = (
                    f"{model}: {type(error).__name__}: {error}"
                )

    else:

        last_error = (
            "OPENROUTER_API_KEY is not configured"
        )

    # -----------------------------------------------------
    # Deterministic fallback
    # -----------------------------------------------------

    state_topics = _fallback_topics(
        state_data,
        STATE_TOPIC_LIMIT,
    )

    worldwide_topics = _fallback_topics(
        worldwide_data,
        WORLD_TOPIC_LIMIT,
    )

    return {
        "state_topics": state_topics,
        "worldwide_topics": worldwide_topics,
        "ai": False,
        "error": last_error,
    }