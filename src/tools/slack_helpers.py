"""Slack helper utilities for posting while guaranteeing thread context."""

from slack_sdk import WebClient

_client: WebClient | None = None  # injected by SpecialistAgent
_bot_name: str | None = None


def post(channel: str, text: str, *, thread_ts: str | None = None) -> str:
    """Universal post function used by agents/tools.

    If ``thread_ts`` is provided the message is posted as a reply; otherwise
    it starts a new root message. Returns the resulting ts or an error string.
    """
    if _client is None:
        return "ERR_NO_CLIENT"

    try:
        response = _client.chat_postMessage(channel=channel, text=text, thread_ts=thread_ts)
        return response.get("ts", "ERR_NO_TS")
    except Exception as e:
        return f"ERR_POST:{e}" 