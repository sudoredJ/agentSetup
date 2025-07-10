"""Zoom API client.

This version supports two modes:
1. Stub (credentials missing) – returns fake meeting data so local testing never fails.
2. Real Server-to-Server OAuth – when ZOOM_ACCOUNT_ID / CLIENT_ID / CLIENT_SECRET are present.
"""

from __future__ import annotations
import os, time, base64, logging
from typing import Dict, Any, Optional

import requests  # added to requirements.txt

log = logging.getLogger(__name__)

class ZoomClient:
    """Handles minimal subset of Zoom REST API we need (create meeting)."""

    token: Optional[str] = None
    token_expires_at: float = 0.0

    def __init__(self) -> None:
        self.account_id    = os.getenv("ZOOM_ACCOUNT_ID")
        self.client_id      = os.getenv("ZOOM_CLIENT_ID")
        self.client_secret  = os.getenv("ZOOM_CLIENT_SECRET")
        self.base_url       = "https://api.zoom.us/v2"

        creds_ok = all([self.account_id, self.client_id, self.client_secret])
        self._stub = not creds_ok
        mode = "STUB" if self._stub else "LIVE"
        log.info(f"ZoomClient initialised in {mode} mode")

    # ------------------------- Public API -------------------------
    def create_meeting(self, topic: str = "Quick Meeting", duration: int = 30) -> Dict[str, Any]:
        """Create a Zoom meeting or stub."""
        if self._stub:
            return {
                "id":        "00000000000",
                "topic":     topic,
                "join_url":  "https://zoom.us/j/00000000000",
                "password":  "stub123",
                "duration":  duration,
            }

        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        data = {
            "topic": topic,
            "type": 1,  # instant meeting for now
            "duration": duration,
            "settings": {
                "join_before_host": True,
                "waiting_room": False,
            },
        }
        resp = requests.post(f"{self.base_url}/users/me/meetings", json=data, headers=headers, timeout=10)
        resp.raise_for_status()
        m = resp.json()
        return {
            "id": str(m["id"]),
            "topic": m["topic"],
            "join_url": m["join_url"],
            "password": m.get("password", ""),
            "duration": m.get("duration", duration),
        }

    def test_connection(self) -> bool:
        if self._stub:
            log.info("ZoomClient in stub mode – test_connection always true")
            return True
        try:
            token = self._get_token()
            resp = requests.get(f"{self.base_url}/users/me", headers={"Authorization": f"Bearer {token}"}, timeout=5)
            resp.raise_for_status()
            return True
        except Exception as exc:
            log.error("Zoom connection test failed", exc_info=True)
            return False

    # ------------------------- Internal -------------------------
    def _get_token(self) -> str:
        """Fetch or refresh S2S OAuth token."""
        if self.token and time.time() < self.token_expires_at - 60:
            return self.token

        creds = f"{self.client_id}:{self.client_secret}"
        basic = base64.b64encode(creds.encode()).decode()
        resp = requests.post(
            "https://zoom.us/oauth/token",
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "account_credentials", "account_id": self.account_id},
            timeout=10,
        )
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json()
        self.token = data["access_token"]
        self.token_expires_at = time.time() + data.get("expires_in", 3600)
        log.info("Zoom token refreshed, expires in %.1f min", (self.token_expires_at - time.time()) / 60)
        return self.token 