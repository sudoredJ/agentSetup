"""Slack helper tools
~~~~~~~~~~~~~~~~~~~~~~
This module groups all tool functions that interact with Slack and can be
called from agents via the `smolagents.tool` decorator.

Key sections:
• Message helpers:   `slack_dm_tool`, `slack_post_tool`, `slack_channel_tool`
• User lookup:       `lookup_user_tool`
• TTS helper:        `slack_tts_tool` – converts text to speech with edge-tts,
  uploads to a public file-sharing host (file.io, 0x0.st fallback) and posts
  the download link to Slack.  No `files:write` scope required.

All functions are safe for import-time injection: the `SpecialistAgent`
injects `_client` (Slack WebClient) and `_bot_name` at runtime.
"""

from smolagents import tool
from slack_sdk import WebClient
import logging
import os
import asyncio
import uuid
import requests
import re

# Lazy import for edge_tts to avoid ImportError when it's not installed
edge_tts = None
def _ensure_edge_tts():
    global edge_tts
    if edge_tts is None:
        try:
            import edge_tts as _edge_tts
            edge_tts = _edge_tts
        except ImportError:
            raise ImportError(
                "edge-tts is required for TTS functionality. "
                "Install it with: pip install edge-tts"
            )

# Module-level storage for injected dependencies
_client: WebClient | None = None
_bot_name: str | None = None

logger = logging.getLogger(__name__)


def markdown_to_slack_mrkdwn(text: str) -> str:
    """Convert standard markdown to Slack mrkdwn format.
    
    Args:
        text: Text with standard markdown formatting
        
    Returns:
        Text formatted for Slack mrkdwn
    """
    # Replace **bold** with *bold*
    converted = text.replace('**', '*')
    
    # Replace __italic__ with _italic_
    converted = converted.replace('__', '_')
    
    # Headers: Replace markdown headers with bold text
    converted = re.sub(r'^#{1,6}\s+(.+)$', r'*\1*', converted, flags=re.MULTILINE)
    converted = re.sub(r'\n#{1,6}\s+(.+)', r'\n*\1*', converted)
    
    # Lists are already compatible
    # Code blocks with ``` are already compatible
    # Links [text](url) are already compatible
    
    return converted


@tool
def slack_dm_tool(user_id: str, message: str, thread_ts: str | None = None) -> str:
    """Sends a direct message to a specific Slack user.

    Args:
        user_id: Slack ID of the user to message (e.g. U12345ABC)
        message: Message text to send
        thread_ts: Timestamp of the thread to reply to (optional)
    """
    if _client is None:
        return "ERROR: Slack client not initialized"

    try:
        # Convert markdown to Slack mrkdwn format
        formatted_message = markdown_to_slack_mrkdwn(message)
        
        formatted = f"Hello!\n\n{formatted_message}\n\n— {_bot_name or 'Assistant'}"
        logger.info(f"[slack_dm_tool] Sending DM to {user_id} | thread_ts={thread_ts} | len(message)={len(message)}")
        _client.chat_postMessage(
            channel=user_id, 
            text=formatted, 
            thread_ts=thread_ts,
            mrkdwn=True  # Explicitly enable mrkdwn
        )
        logger.info("[slack_dm_tool] DM sent successfully")
        return f"DM sent successfully to user {user_id}"
    except Exception as e:
        logger.error("ERROR in slack_dm_tool", exc_info=True)
        return f"Failed to send DM: {e}"


@tool
def lookup_user_tool(name: str) -> str:
    """Look up a Slack user ID by display name, real name or username.

    Args:
        name: Name or username to resolve
    """
    if _client is None:
        return "ERROR_NO_CLIENT"

    if name.startswith("U") and len(name) == 11:
        return name

    try:
        resp = _client.users_list(limit=1000)
        for user in resp.get("members", []):
            if user.get("deleted") or user.get("is_bot"):
                continue
            profile = user.get("profile", {})
            candidates = {
                profile.get("display_name", "").lower(),
                profile.get("real_name", "").lower(),
                user.get("name", "").lower(),
            }
            if name.lower() in candidates or name.lower() in profile.get("real_name", "").lower():
                return user["id"]
        return "USER_NOT_FOUND"
    except Exception as e:
        logger.error("ERROR in lookup_user_tool", exc_info=True)
        return "ERROR_LOOKUP"


@tool
def slack_post_tool(channel_id: str, message: str, thread_ts: str | None = None) -> str:
    """Post a message to a Slack channel.

    Args:
        channel_id: Channel ID (e.g. C12345ABC)
        message: Text to post
        thread_ts: Timestamp of the thread to reply to (optional)
    """
    if _client is None:
        return "ERROR: Slack client not initialized"

    try:
        # Convert markdown to Slack mrkdwn format
        formatted_message = markdown_to_slack_mrkdwn(message)
        
        logger.info(f"[slack_post_tool] Posting to {channel_id} | thread_ts={thread_ts} | len(message)={len(message)}")
        _client.chat_postMessage(channel=channel_id, text=formatted_message, thread_ts=thread_ts, mrkdwn=True)
        logger.info("[slack_post_tool] Message posted successfully")
        return f"Message posted successfully to channel {channel_id}"
    except Exception as e:
        logger.error("ERROR in slack_post_tool", exc_info=True)
        return f"Failed to post message: {e}"


@tool
def slack_channel_tool(channel_id: str, message: str, thread_ts: str | None = None) -> str:
    """Send a message to a Slack channel or thread.

    Args:
        channel_id: ID of the Slack channel to post in (e.g. C12345ABC)
        message: The text message to send
        thread_ts: The timestamp of a thread to reply within (optional)
    """
    if _client is None:
        return "Error: Slack client not initialized"

    try:
        # Convert markdown to Slack mrkdwn format
        formatted_message = markdown_to_slack_mrkdwn(message)
        
        kwargs = {"channel": channel_id, "text": formatted_message, "mrkdwn": True}
        if thread_ts:
            kwargs["thread_ts"] = thread_ts
        logger.info(f"[slack_channel_tool] Posting to {channel_id} (thread_ts={thread_ts}) | len(message)={len(message)}")
        _client.chat_postMessage(**kwargs)
        logger.info("[slack_channel_tool] Message posted successfully")
        location = f"thread {thread_ts}" if thread_ts else f"channel {channel_id}"
        return f"Message sent to {location}"
    except Exception as e:
        logger.error("Failed to send channel message", exc_info=True)
        return f"Failed to send message: {e}"


@tool
def slack_tts_tool(channel_id: str, text: str, voice: str = "en-US-AriaNeural") -> str:
    """Generate Text-to-Speech audio and share via file.io link in Slack.

    Args:
        channel_id: The Slack channel or user ID to send the audio link to
        text: The text to convert to speech
        voice: The voice to use for TTS (default is en-US-AriaNeural)
    """
    if _client is None:
        return "ERROR: Slack client not initialized"

    try:
        # Ensure edge_tts is available
        _ensure_edge_tts()
        
        filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"

        async def _generate():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(filename)

        try:
            asyncio.run(_generate())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_generate())

        link: str | None = None

        with open(filename, "rb") as audio_file:
            files = {"file": (filename, audio_file, "audio/mpeg")}

            # Try file.io first
            try:
                resp = requests.post("https://file.io", files=files, timeout=30)
                if resp.ok:
                    try:
                        data = resp.json()
                        if data.get("success"):
                            link = data.get("link")
                            logger.info("file.io upload successful: %s", link)
                    except Exception:
                        pass
            except Exception as e:
                logger.warning("file.io upload failed: %s", e)

            # Fallback to 0x0.st if file.io failed
            if not link:
                try:
                    audio_file.seek(0)
                    resp = requests.post("https://0x0.st", files={"file": (filename, audio_file, "audio/mpeg")}, timeout=30)
                    if resp.ok:
                        link = resp.text.strip()
                        logger.info("0x0.st upload successful: %s", link)
                except Exception as e:
                    logger.warning("0x0.st upload failed: %s", e)

        # Remove local file
        if os.path.exists(filename):
            os.remove(filename)

        if link:
            preview = text[:100] + ("..." if len(text) > 100 else "")
            message = (
                "🔊 *Text-to-Speech Audio Generated*\n\n"
                f"🔗 Download: {link}\n"
                f"🎙️ Voice: `{voice}`\n"
                f"📝 Text: _{preview}_\n\n"
                "_Note: Link expires in 24 hours_"
            )
            _client.chat_postMessage(channel=channel_id, text=message, unfurl_links=False, mrkdwn=True)
            return f"TTS audio link sent to {channel_id}"

        return "Failed to upload audio to file sharing service"

    except ImportError:
        return "TTS generation failed: edge-tts not installed. Run: pip install edge-tts"
    except Exception as e:
        logger.error("TTS generation failed", exc_info=True)
        return f"TTS generation failed: {e}"