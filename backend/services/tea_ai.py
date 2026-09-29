import os
import httpx
from typing import Optional


# =========================================================
# OPENROUTER CONFIG
# =========================================================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_M = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b")

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)


# =========================================================
# STATE NAMES
# =========================================================

STATE_NAMES = {
    1: "Uttar Pradesh",
    2: "Delhi",
    3: "Maharashtra",
    4: "Rajasthan",
    5: "Bihar",
    6: "Jharkhand",
    7: "Madhya Pradesh",
    8: "West Bengal",
    9: "Tamil Nadu",
    10: "Karnataka",
    11: "Gujarat",
    12: "Haryana",
}


# =========================================================
# SYSTEM PROMPT
# =========================================================

def build_system_prompt(
    state_id: Optional[int],
) -> str:

    state_name = STATE_NAMES.get(
        state_id,
        "India"
    )

    return f"""
You are "Tea", the AI assistant of Political Tea.

Political Tea is a state-focused platform where people
discuss news, politics, public issues and what is happening
around their state.

The user's current state is:

{state_name}

Your job is to help the user understand what is happening
locally and nationally.

IMPORTANT RULES:

1. Be factual, neutral and informative.

2. Do not promote or attack any political party,
   politician, government or ideology.

3. Never invent news, statistics, quotes, events,
   sources or statements.

4. For current or recent news, use web search when
   necessary.

5. Prioritize news and information relevant to:
   {state_name}

6. If the user asks about a city, district or local area,
   focus on that location.

7. Clearly distinguish:
   - confirmed facts
   - reported claims
   - opinions
   - analysis

8. If information is unavailable or cannot be verified,
   clearly say that.

9. If multiple sources report the same event, summarize
   the event rather than repeating every article.

10. When discussing political topics, present relevant
    positions fairly and do not tell the user what political
    decision they should make.

11. Keep answers conversational and easy to understand.

12. You can use a light "Tea" personality, but do not
    sacrifice factual accuracy.

13. When web sources are available, mention the source
    naturally in the response.

14. For "today", "latest", "right now", "this morning",
    "yesterday" or similar questions, use current web
    information rather than relying on model memory.

Example style:

"☕ Here's what's brewing in Uttar Pradesh:

• ...
• ...
• ...

The latest reports indicate ...
Source: ..."

Do not claim that something is breaking news unless
the available evidence supports that description.
"""


# =========================================================
# CHAT WITH TEA
# =========================================================

async def ask_tea(
    message: str,
    state_id: Optional[int] = None,
    conversation: Optional[list] = None,
):

    if not OPENROUTER_API_KEY:

        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured"
        )

    system_prompt = build_system_prompt(
        state_id
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    # -----------------------------------------------------
    # Previous conversation
    # -----------------------------------------------------

    if conversation:

        for item in conversation[-10:]:

            role = item.get("role")
            content = item.get("content")

            if role not in ["user", "assistant"]:
                continue

            if not content:
                continue

            messages.append({
                "role": role,
                "content": str(content)
            })

    # -----------------------------------------------------
    # Current question
    # -----------------------------------------------------

    messages.append({
        "role": "user",
        "content": message
    })

    # -----------------------------------------------------
    # OpenRouter request
    # -----------------------------------------------------

    payload = {
        "model": OPENROUTER_MODEL,

        "messages": messages,

        "temperature": 0.2,

        "max_tokens": 1200,

        "tools": [
            {
                "type": "openrouter:web_search",
                "parameters": {
                    "max_results": 5
                }
            }
        ]
    }

    headers = {
        "Authorization": (
            f"Bearer {OPENROUTER_API_KEY}"
        ),
        "Content-Type": "application/json",

        # Optional but useful for OpenRouter
        "HTTP-Referer": (
            os.getenv(
                "FRONTEND_URL",
                "https://politicaltea.com"
            )
        ),

        "X-Title": "Political Tea"
    }

    timeout = httpx.Timeout(
        60.0,
        connect=15.0
    )

    async with httpx.AsyncClient(
        timeout=timeout
    ) as client:

        response = await client.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload
        )

    # -----------------------------------------------------
    # OpenRouter errors
    # -----------------------------------------------------

    if response.status_code != 200:

        try:
            error_data = response.json()

        except Exception:
            error_data = {
                "error": response.text
            }

        detail = error_data.get(
            "error",
            error_data
        )

        if isinstance(detail, dict):

            detail = detail.get(
                "message",
                str(detail)
            )

        raise RuntimeError(
            f"OpenRouter error: {detail}"
        )

    data = response.json()

    # -----------------------------------------------------
    # Extract answer
    # -----------------------------------------------------

    choices = data.get(
        "choices",
        []
    )

    if not choices:

        raise RuntimeError(
            "OpenRouter returned no answer"
        )

    assistant_message = choices[0].get(
        "message",
        {}
    )

    answer = assistant_message.get(
        "content"
    )

    if not answer:

        answer = (
            "☕ I couldn't find enough information "
            "to answer that right now."
        )

    return {
        "answer": answer,
        "state_id": state_id,
        "state_name": STATE_NAMES.get(
            state_id,
            "India"
        ),
        "model": OPENROUTER_MODEL
    }
