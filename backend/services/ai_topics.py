import json
import os
import re
from typing import List, Dict

import requests
from dotenv import load_dotenv

load_dotenv()


OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-oss-20b:free"
)


def _extract_json(text):

    if not text:
        return []

    text = text.strip()

    # Remove markdown code fences
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    try:
        data = json.loads(text)

        if isinstance(data, list):
            return data

    except json.JSONDecodeError:
        pass

    # Try extracting JSON array
    match = re.search(
        r"\[[\s\S]*\]",
        text
    )

    if match:

        try:
            data = json.loads(
                match.group(0)
            )

            if isinstance(data, list):
                return data

        except json.JSONDecodeError:
            pass

    return []


def _call_openrouter(
    system_prompt,
    user_prompt
):

    if not OPENROUTER_API_KEY:

        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured"
        )

    headers = {
        "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",

        "Content-Type":
            "application/json",

        "HTTP-Referer":
            "http://127.0.0.1:8000",

        "X-Title":
            "Political Tea"
    }

    payload = {

        "model":
            OPENROUTER_MODEL,

        "messages": [

            {
                "role":
                    "system",

                "content":
                    system_prompt
            },

            {
                "role":
                    "user",

                "content":
                    user_prompt
            }
        ],

        "temperature":
            0.2,

        "max_tokens":
            1200
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    try:

        return data[
            "choices"
        ][0][
            "message"
        ][
            "content"
        ]

    except (
        KeyError,
        IndexError,
        TypeError
    ):

        raise RuntimeError(
            "Invalid response from OpenRouter"
        )


def _prepare_news(news):

    prepared = []

    for index, item in enumerate(
        news[:40],
        start=1
    ):

        prepared.append({
            "id": index,
            "title":
                item.get(
                    "title",
                    ""
                ),

            "description":
                item.get(
                    "description",
                    ""
                ),

            "source":
                item.get(
                    "source",
                    ""
                ),

            "published_at":
                item.get(
                    "published_at",
                    ""
                )
        })

    return prepared


def generate_state_topics(
    state_name,
    news
):

    prepared_news = _prepare_news(
        news
    )

    if not prepared_news:
        return []

    system_prompt = """
You are the AI trend analyst for Political Tea,
an Indian political news platform.

Your job is to identify REAL trending political
topics from the supplied last-24-hours news.

Do NOT invent stories.

Do NOT treat every article as a separate topic.

Group articles discussing the same event,
person, policy, protest, election issue,
government decision or political controversy.

Rank topics using:
1. Number of related articles
2. Recency
3. Political importance
4. Public-interest relevance
5. Cross-source coverage

Return ONLY valid JSON.

Format:

[
  {
    "title": "Short topic title",
    "mentions": "12 sources",
    "change": "+34%",
    "summary": "One short sentence explaining why it is trending"
  }
]

Return maximum 5 topics.

The title must be short and suitable for a
website card.

The change value should represent estimated
trend momentum from the supplied coverage.
It is NOT a real Google Trends percentage.
"""

    user_prompt = f"""
State: {state_name}

These are news items from approximately the
last 24 hours:

{json.dumps(
    prepared_news,
    ensure_ascii=False,
    indent=2
)}

Identify the most important and genuinely
trending topics in {state_name}.
"""

    try:

        result = _call_openrouter(
            system_prompt,
            user_prompt
        )

        topics = _extract_json(
            result
        )

        clean_topics = []

        for topic in topics[:5]:

            if not isinstance(
                topic,
                dict
            ):
                continue

            title = str(
                topic.get(
                    "title",
                    ""
                )
            ).strip()

            if not title:
                continue

            clean_topics.append({

                "title":
                    title[:100],

                "mentions":
                    str(
                        topic.get(
                            "mentions",
                            ""
                        )
                    )[:40],

                "change":
                    str(
                        topic.get(
                            "change",
                            ""
                        )
                    )[:20],

                "summary":
                    str(
                        topic.get(
                            "summary",
                            ""
                        )
                    )[:250]
            })

        return clean_topics

    except Exception as error:

        print(
            "State AI topic error:",
            error
        )

        return []


def generate_worldwide_topics(
    news
):

    prepared_news = _prepare_news(
        news
    )

    if not prepared_news:
        return []

    system_prompt = """
You are the worldwide political trend analyst
for Political Tea.

Analyze the supplied recent political news and
identify the biggest CURRENT political stories
being discussed internationally.

Prioritize:
- Major governments
- Elections
- International conflicts
- Diplomacy
- Major policy decisions
- Global political controversies
- Leaders and political movements

Group duplicate stories from multiple sources.

Do NOT invent information.

Use ONLY the supplied news.

Return ONLY valid JSON.

Format:

[
  {
    "title": "Short topic title",
    "mentions": "25 sources",
    "change": "+48%",
    "summary": "One short sentence explaining why this topic is trending"
  }
]

Maximum 6 topics.

The change value is an estimated momentum score
based on the supplied coverage, NOT a real
Google Trends percentage.
"""

    user_prompt = f"""
Here is recent worldwide political news:

{json.dumps(
    prepared_news,
    ensure_ascii=False,
    indent=2
)}

Identify the biggest worldwide political trends
from this data.
"""

    try:

        result = _call_openrouter(
            system_prompt,
            user_prompt
        )

        topics = _extract_json(
            result
        )

        clean_topics = []

        for topic in topics[:6]:

            if not isinstance(
                topic,
                dict
            ):
                continue

            title = str(
                topic.get(
                    "title",
                    ""
                )
            ).strip()

            if not title:
                continue

            clean_topics.append({

                "title":
                    title[:100],

                "mentions":
                    str(
                        topic.get(
                            "mentions",
                            ""
                        )
                    )[:40],

                "change":
                    str(
                        topic.get(
                            "change",
                            ""
                        )
                    )[:20],

                "summary":
                    str(
                        topic.get(
                            "summary",
                            ""
                        )
                    )[:250]
            })

        return clean_topics

    except Exception as error:

        print(
            "Worldwide AI topic error:",
            error
        )

        return []