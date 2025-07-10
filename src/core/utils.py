import re
from functools import lru_cache

def sanitize_mentions(text: str, slack_client) -> str:
    """Convert <@U123ABC> Slack mentions into plain @username to avoid accidental pings."""
    pattern = re.compile(r"<@([A-Z0-9]+)>")

    @lru_cache(maxsize=256)
    def _lookup(user_id: str) -> str:
        try:
            info = slack_client.users_info(user=user_id)
            profile = info.get("user", {}).get("profile", {})
            return profile.get("display_name") or info["user"].get("name", "user")
        except Exception:
            return "user"

    return pattern.sub(lambda m: f"@{_lookup(m.group(1))}", text)

def format_context_for_ai(context_messages, request_data):
    """Format context (Slack message dicts) and request metadata into a structure that can be serialized for LLMs.

    Args:
        context_messages (list[dict]): Raw Slack message JSON objects composing the thread history.
        request_data (dict): Metadata about the current request (expects keys: 'request', 'user_id').
    Returns:
        dict: Structured payload ready for inclusion in an LLM prompt.
    """
    formatted = {
        "conversation_history": context_messages,
        "current_request": request_data.get("request"),
        "user_id": request_data.get("user_id"),
        "channel_type": "thread" if request_data.get("original_thread_ts") else "direct",
        "participants": list({msg.get("user") for msg in context_messages if msg.get("user")})
    }
    return formatted

