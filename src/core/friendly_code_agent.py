"""FriendlyCodeAgent – tolerant version of smolagents.CodeAgent.

Executes the *first* bare function-call line it can locate, allowing the LLM to add explanatory prose before/after.
Keeps smolagents untouched – just use this class instead of CodeAgent.
"""

from __future__ import annotations
import re
from smolagents import CodeAgent

# Matches a single-line function call like slack_dm_tool('U123', 'hi')
_CALL_PATTERN = re.compile(r"^[a-zA-Z_]\w*\s*\(.*\)$", re.M)

class FriendlyCodeAgent(CodeAgent):
    """A CodeAgent that gracefully extracts the first tool-call line."""

    # type: ignore[override]  – parent doesn't annotate
    def _extract_code(self, text: str):  # noqa: D401
        """Return first valid call line if original extraction fails."""
        extracted = super()._extract_code(text)
        if extracted:
            return extracted
        match = _CALL_PATTERN.search(text.strip())
        return match.group(0).strip() if match else None 