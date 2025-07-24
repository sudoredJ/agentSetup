"""Logic for polling specialist evaluations and assigning the task to the best one.
This code was factored out of ``src/main.py`` unchanged (apart from explicit
parameterisation) so behaviour remains identical.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Dict, Any

from slack_sdk.errors import SlackApiError
from yaspin import yaspin

__all__ = ("check_and_assign",)


def check_and_assign(
    client,
    thread_ts: str,
    request_data: dict | None = None,
    *,
    specialists: Dict[str, Any],
    coordination_channel: str,
    active_requests: Dict[str, Dict[str, Any]] | None = None,  # currently unused
) -> None:
    """Poll a coordination‐thread, gather evaluations, then assign a specialist.

    All arguments mirror the variables that were captured from the outer scope
    when this logic lived in ``main.py``.  Making them explicit means the
    function is now pure and easily testable.
    """

    timeout = 8  # seconds total wait (unchanged)
    check_interval = 0.5  # seconds between polls
    start_time = time.time()

    logging.info(
        "Checking thread %s for evaluations... (timeout %ss)", thread_ts, timeout
    )
    logging.info("Expected specialists: %s", list(specialists.keys()))

    evaluations: Dict[str, int] = {}

    try:
        with yaspin(text="Waiting for evaluations", color="cyan") as spin:
            while time.time() - start_time < timeout:
                try:
                    # Fresh API call every loop so we don't miss late messages
                    thread = client.conversations_replies(
                        channel=coordination_channel, ts=thread_ts
                    )
                except SlackApiError as api_err:
                    if api_err.response.get("error") == "ratelimited":
                        retry_after = int(api_err.response.headers.get("Retry-After", 2))
                        logging.warning(
                            "Rate limited when fetching thread %s. Retrying after %ss…",
                            thread_ts,
                            retry_after,
                        )
                        time.sleep(retry_after)
                        continue
                    raise  # re-raise unknown errors

                for msg in thread.get("messages", []):
                    text = msg.get("text", "")
                    match = re.search(
                        r"(?:🧠\s*)?(\w+)\s+reporting:\s+Confidence\s+(\d+)%", text
                    )
                    if match:
                        agent_name = match.group(1)
                        confidence = int(match.group(2))
                        if agent_name not in evaluations:
                            evaluations[agent_name] = confidence
                            logging.info(
                                "  Found evaluation: %s = %s%%", agent_name, confidence
                            )
                            spin.text = (
                                f"Collected {len(evaluations)}/{len(specialists)} evaluations"
                            )

                if len(evaluations) >= len(specialists):
                    logging.info("All specialists have responded!")
                    break

                time.sleep(check_interval)

            spin.ok("✔")

        logging.info(
            "Total evaluations received: %d out of %d specialists",
            len(evaluations),
            len(specialists),
        )
        missing_specialists = set(specialists.keys()) - set(evaluations.keys())
        if missing_specialists:
            logging.warning("Missing responses from: %s", missing_specialists)

        if evaluations:
            logging.info("Evaluations: %s", evaluations)
        else:
            logging.info("No evaluations found. Dumping raw thread messages for debugging…")
            thread = client.conversations_replies(
                channel=coordination_channel, ts=thread_ts
            )
            for i, msg in enumerate(thread.get("messages", [])):
                logging.info("Message %d: %s", i, msg.get("text", "")[:120])

        # ---------------- Assignment ----------------
        if evaluations:
            agent_name, confidence = max(evaluations.items(), key=lambda x: x[1])
            if confidence > 0 and agent_name in specialists:
                specialist = specialists[agent_name]
                logging.info(
                    "Assigning to %s (confidence: %s%%)", agent_name, confidence
                )
                try:
                    client.chat_postMessage(
                        channel=coordination_channel,
                        thread_ts=thread_ts,
                        text=(
                            f"ASSIGNED: <@{specialist.bot_user_id}> - Please handle this request."
                        ),
                    )
                except Exception as exc:
                    logging.error("Failed to post assignment: %s", exc)
            else:
                client.chat_postMessage(
                    channel=coordination_channel,
                    thread_ts=thread_ts,
                    text="No specialist confident enough to handle this request.",
                )
        else:
            logging.warning("No evaluations received in time!")
            try:
                client.chat_postMessage(
                    channel=coordination_channel,
                    thread_ts=thread_ts,
                    text="No specialists responded to evaluation request.",
                )
            except Exception as exc:
                logging.error("Failed to post no-response message: %s", exc)

    except Exception as err:
        logging.error("Assignment error: %s", err, exc_info=True)
        try:
            client.chat_postMessage(
                channel=coordination_channel,
                thread_ts=thread_ts,
                text=f"Error during assignment: {err}",
            )
        except Exception:
            pass 