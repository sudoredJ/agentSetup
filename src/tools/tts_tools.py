from __future__ import annotations

"""Text-to-speech utilities based on Microsoft Edge-TTS.

This module provides two tools:
1. ``TextToSpeechTool`` – converts text to speech and returns the local file path.
2. ``SlackTTSTool``      – converts text to speech and uploads it to a Slack channel / thread.

Both are written as subclasses of ``smolagents.Tool`` so they can be loaded in
agent profiles just like any other tool.
"""

import asyncio
import os
import tempfile
from typing import Dict, Any, Optional

import edge_tts
from smolagents import Tool
from slack_sdk import WebClient

__all__ = ["TextToSpeechTool", "SlackTTSTool"]


class TextToSpeechTool(Tool):
    name = "text_to_speech"
    description = "Convert text to speech audio file. Returns file path."
    inputs = {
        "text": {
            "type": "string",
            "description": "Text to convert to speech",
        },
        "voice": {
            "type": "string",
            "description": "Voice name (optional)",
            "default": "en-US-AriaNeural",
        },
        "rate": {
            "type": "string",
            "description": "Speech rate (optional)",
            "default": "+0%",
        },
    }
    output_type = "string"  # Returns local file path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    async def _synthesize(text: str, voice: str, rate: str, file_path: str) -> None:
        """Run Edge-TTS synthesis coroutine."""
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
        await communicate.save(file_path)

    # ------------------------------------------------------------------
    # Public API – smolagents entry point
    # ------------------------------------------------------------------
    def forward(self, text: str, voice: str = "en-US-AriaNeural", rate: str = "+0%") -> str:  # type: ignore[override]
        """Generate speech for *text* and return the path to the MP3 file."""
        # Create a temp file that persists after closing so Slack can upload it.
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp_path = tmp.name
        tmp.close()

        # Run the async TTS generation – handle cases where an event loop exists.
        async def _run():
            await self._synthesize(text, voice, rate, tmp_path)

        try:
            asyncio.run(_run())
        except RuntimeError:
            # Fallback when already inside an event loop (e.g. Jupyter / async app)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())

        return tmp_path


class SlackTTSTool(Tool):
    name = "slack_tts"
    description = "Convert text to speech and upload the audio file to a Slack channel or thread."
    inputs = {
        "text": {"type": "string", "description": "Text to convert to speech"},
        "channel": {"type": "string", "description": "Slack channel ID"},
        "thread_ts": {
            "type": "string",
            "description": "Thread timestamp (optional)",
            "default": None,
        },
        "voice": {
            "type": "string",
            "description": "Voice name (optional)",
            "default": "en-US-AriaNeural",
        },
    }
    output_type = "dict"  # Returns Slack API response

    # Slack client will be injected by agent loader
    _slack: Optional[WebClient] = None

    def __init__(self, slack_client: WebClient | None = None):
        # Allow manual injection or rely on SpecialistAgent injection mechanism.
        if slack_client is not None:
            self._slack = slack_client
        self.tts_tool = TextToSpeechTool()

    # --------------------------------------------------------------
    def forward(
        self,
        text: str,
        channel: str,
        thread_ts: str | None = None,
        voice: str = "en-US-AriaNeural",
    ) -> Dict[str, Any]:  # type: ignore[override]
        """Generate TTS and upload it to Slack, then return the API response."""
        if self._slack is None:
            raise RuntimeError("Slack client not initialised – injection missing")

        # 1. Generate audio file
        audio_path = self.tts_tool(text=text, voice=voice)

        # 2. Upload to Slack
        try:
            resp = self._slack.files_upload(
                channels=channel,
                file=audio_path,
                title="TTS Audio",
                thread_ts=thread_ts,
            )
            return resp
        finally:
            # Always delete temp file
            try:
                os.remove(audio_path)
            except OSError:
                pass 