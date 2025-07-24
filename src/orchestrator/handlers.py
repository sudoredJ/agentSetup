"""Specialist event-handler registration extracted from ``src/main.py``.

The function adds Slack event callbacks to a *single* Specialist agent and is
identical to the original version except that all previously-global
dependencies are now explicit keyword arguments.
"""

from __future__ import annotations

import logging
import re
import threading
from typing import Dict, Any

from src.agents.specialist_agent import SpecialistAgent

__all__ = ("register_specialist_handlers",)


def register_specialist_handlers(
    specialist: SpecialistAgent,
    specialist_name: str,
    *,
    orchestrator,
    coordination_channel: str,
    active_requests: Dict[str, Dict[str, Any]],
) -> None:
    """Attach message / mention / reaction callbacks to *specialist*.

    Parameters are injected to avoid hidden global coupling; behaviour is
    unchanged from the inline implementation.
    """

    # ------------------------------------------------------------------
    # Preserve original closure variables
    # ------------------------------------------------------------------
    spec = specialist
    name = specialist_name

    @spec.app.event("message")
    def spec_message_handler(event: Dict[str, Any], client, logger):
        channel = event.get("channel")
        if channel != coordination_channel:
            return

        # Ignore bot messages except from orchestrator
        if event.get("bot_id") and event.get("user") != orchestrator.bot_user_id:
            return

        text = event.get("text", "")
        msg_ts = event["ts"]
        thread_ts = event.get("thread_ts", msg_ts)

        # ---------------- Evaluation phase ----------------
        if "please evaluate" in text and f"<@{spec.bot_user_id}>" in text:
            m_task = re.search(r'Task: "(.*)"', text, re.DOTALL)
            if m_task:
                task = m_task.group(1)
                logger.info("%s evaluating: '%s'", name, task)

                def run_evaluation():
                    try:
                        _, conf = spec.evaluate_request(task)
                        reply = (
                            f"🧠 {name} reporting: Confidence {conf}% for \"{task}\""
                        )
                        logger.info("%s posting evaluation: %s%%", name, conf)
                        client.chat_postMessage(
                            channel=coordination_channel,
                            thread_ts=msg_ts,
                            text=reply,
                        )
                    except Exception:
                        logger.error("%s failed to post evaluation", name, exc_info=True)

                threading.Thread(target=run_evaluation, daemon=True).start()

        # ---------------- Assignment phase ----------------
        elif f"ASSIGNED: <@{spec.bot_user_id}>" in text:
            logger.info("%s received assignment!", name)

            req_meta = active_requests.get(thread_ts, {})

            try:
                thread = client.conversations_replies(
                    channel=coordination_channel, ts=thread_ts
                )
            except Exception as exc:
                logger.error("Failed to get thread replies: %s", exc)
                return

            for msg in thread.get("messages", []):
                user_match = re.search(r"Request from <@(\w+)>", msg.get("text", ""))
                task_match = re.search(r'Task: "(.*)"', msg.get("text", ""), re.DOTALL)

                if user_match and task_match:
                    user_id = user_match.group(1)
                    request_text = task_match.group(1)

                    coord_context = thread.get("messages", [])
                    orig_context: list[dict] = []

                    if req_meta.get("channel_id") and req_meta.get("original_thread_ts"):
                        try:
                            orig_thread = orchestrator.client.conversations_replies(
                                channel=req_meta["channel_id"],
                                ts=req_meta["original_thread_ts"],
                                limit=50,
                            )
                            orig_context = orig_thread.get("messages", [])
                        except Exception:
                            logger.error(
                                "Could not fetch original thread context", exc_info=True
                            )

                    full_context = coord_context + orig_context

                    logger.info("DEBUG: %s Assignment details", name)
                    logger.info("  • request_text: '%s'", request_text)
                    logger.info("  • user_id: %s", user_id)
                    logger.info("  • context messages: %d", len(full_context))

                    def run_assignment():
                        tlog = logging.getLogger(f"Thread-{name}")
                        tlog.info("Assignment thread started")
                        try:
                            process_method = getattr(spec, "process_assignment", None)
                            if not callable(process_method):
                                raise AttributeError("process_assignment not found")

                            tlog.info("Calling process_assignment …")
                            process_method(request_text, user_id, thread_ts, full_context)
                            tlog.info("process_assignment finished")
                        except Exception as err:
                            tlog.error("Error inside assignment thread", exc_info=True)
                            try:
                                client.chat_postMessage(
                                    channel=coordination_channel,
                                    text=(
                                        f"❌ {name} error: {type(err).__name__}: {err}"
                                    ),
                                    thread_ts=thread_ts,
                                )
                            except Exception:
                                pass

                    try:
                        t = threading.Thread(
                            target=run_assignment,
                            name=f"{name}-Assign-{thread_ts[:8]}",
                            daemon=True,
                        )
                        t.start()
                        logger.info("Started thread %s", t.name)
                    except Exception as thread_err:
                        logger.error("Failed to start assignment thread", exc_info=True)
                        client.chat_postMessage(
                            channel=coordination_channel,
                            text=f"❌ Thread creation failed for {name}: {thread_err}",
                            thread_ts=thread_ts,
                        )
                    break

    # ----------------------------------------------------
    # Additional event handlers
    # ----------------------------------------------------
    @spec.app.event("app_mention")
    def spec_mention_handler(event, client, logger):
        if event.get("channel") != coordination_channel:
            client.chat_postMessage(
                channel=event["channel"],
                thread_ts=event.get("thread_ts", event["ts"]),
                text=(
                    f"Please mention <@{orchestrator.bot_user_id}> for assistance. "
                    "I work through the orchestrator."
                ),
            )

    @spec.app.event("reaction_added")
    def spec_reaction_handler(event, logger):
        pass  # Suppress warnings 