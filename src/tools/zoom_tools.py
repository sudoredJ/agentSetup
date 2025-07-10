"""Zoom integration stub tools.

Step-2: first working tool that simply calls the stub ZoomClient and returns a join URL.
Once real OAuth is wired this file stays the same – only the client implementation changes.
"""

from __future__ import annotations

import logging
from typing import Optional
from smolagents import tool

from src.integrations.zoom_client import ZoomClient

# These dependencies are injected at runtime by SpecialistAgent so that the
# tool can stay framework-agnostic.
_zoom_client: Optional[ZoomClient] = None  # type: ignore
_slack_client = None  # slack_sdk.WebClient – injected if available

logger = logging.getLogger(__name__)

@tool
def create_zoom_meeting(topic: str = "Quick Meeting", duration: int = 30, announce_channel: str | None = None) -> str:
    """Create a Zoom meeting and (optionally) announce it in Slack.

    Args:
        topic (str): Title for the meeting. Defaults to "Quick Meeting".
        duration (int): Duration in minutes. Defaults to 30.
        announce_channel (str, optional): Slack channel ID to post meeting
            details in. If omitted, nothing is posted automatically.

    Returns:
        str: Human-readable meeting details or an error message.
    """
    if _zoom_client is None:
        return "ERROR: Zoom client not initialized"

    try:
        meeting = _zoom_client.create_meeting(topic=topic, duration=duration)
        details = (
            "📅 Zoom meeting created:\n"
            f"• Topic: {meeting['topic']}\n"
            f"• Join URL: {meeting['join_url']}\n"
            f"• Password: {meeting['password']}\n"
            f"• Duration: {meeting['duration']} minutes"
        )

        # Optionally announce in Slack
        if announce_channel and _slack_client:
            try:
                _slack_client.chat_postMessage(channel=announce_channel, text=details)
            except Exception as slack_err:
                details += f"\n⚠️ Failed to post to Slack: {slack_err}"

        return details
    except Exception as exc:
        return f"ERROR: Failed to create Zoom meeting – {exc}" 