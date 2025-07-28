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

    timeout = 8  # seconds total wait (balanced for speed and reliability)
    check_interval = 0.3  # seconds between polls (avoid rate limiting)
    min_confidence = 30  # minimum confidence threshold
    start_time = time.time()

    logging.info(
        "Checking thread %s for evaluations... (timeout %ss)", thread_ts, timeout
    )
    logging.info("Expected specialists: %s", list(specialists.keys()))

    evaluations: Dict[str, int] = {}
    
    # Add a small initial delay to allow agents to start processing
    time.sleep(0.2)  # minimal delay for faster response
    logging.info("Starting evaluation check after 0.2s delay")

    try:
        with yaspin(text="Waiting for evaluations", color="cyan") as spin:
            while time.time() - start_time < timeout:
                try:
                    # Fresh API call every loop so we don't miss late messages
                    thread = client.conversations_replies(
                        channel=coordination_channel, ts=thread_ts
                    )
                    logging.info(f"DEBUG: Fetched thread with {len(thread.get('messages', []))} messages")
                except SlackApiError as api_err:
                    if api_err.response.get("error") == "ratelimited":
                        retry_after = int(api_err.response.headers.get("Retry-After", 2))
                        # Cap retry delay at 10 seconds for better responsiveness
                        actual_retry = min(retry_after, 10)
                        logging.warning(
                            "Rate limited when fetching thread %s. Retrying after %ss (capped from %ss)…",
                            thread_ts,
                            actual_retry,
                            retry_after,
                        )
                        # Don't count rate limit delays against our timeout
                        start_time += actual_retry
                        time.sleep(actual_retry)
                        continue
                    raise  # re-raise unknown errors

                messages = thread.get("messages", [])
                logging.info(f"DEBUG: Processing {len(messages)} messages in evaluation loop")
                for i, msg in enumerate(messages):
                    text = msg.get("text", "")
                    logging.info(f"DEBUG: Message {i}: '{text[:100]}...'")
                    # Debug logging
                    if "reporting:" in text.lower():
                        logging.info(f"DEBUG: Found potential eval message: '{text}'")
                    match = re.search(
                        r"(?:🧠\s*)?(\w+)\s+reporting:\s+Confidence\s+(\d+)%.*", text, re.IGNORECASE
                    )
                    if match:
                        agent_name = match.group(1)
                        confidence = int(match.group(2))
                        logging.info(
                            "  Regex matched! agent_name='%s', confidence=%s", agent_name, confidence
                        )
                        if agent_name not in evaluations:
                            evaluations[agent_name] = confidence
                            logging.info(
                                "  Added evaluation: %s = %s%%", agent_name, confidence
                            )
                            spin.text = (
                                f"Collected {len(evaluations)}/{len(specialists)} evaluations"
                            )
                        else:
                            logging.info(
                                "  Duplicate evaluation for %s ignored", agent_name
                            )

                if len(evaluations) >= len(specialists):
                    logging.info("All specialists have responded!")
                    break

                # Log progress
                elapsed = time.time() - start_time
                logging.info(f"Evaluation progress: {len(evaluations)}/{len(specialists)} specialists, {elapsed:.1f}s elapsed")
                
                # Dynamic check interval - start slow, speed up near timeout
                if elapsed < 2:
                    time.sleep(0.5)  # Check every 0.5s initially to avoid rate limits
                elif elapsed < 5:
                    time.sleep(0.3)  # Medium frequency
                else:
                    time.sleep(0.2)  # Fast polling near timeout

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
            # Check if we need collaborative discussion
            max_confidence = max(evaluations.values()) if evaluations else 0
            
            # If initial max confidence is below 50%, start collaborative discussion
            if max_confidence < 50:
                logging.info("Max confidence %s%% is below 50%%, starting collaborative discussion", max_confidence)
                
                try:
                    # Import and use the discussion coordinator
                    from src.agents.negotiation_module import AgentDiscussionCoordinator
                    
                    coordinator = AgentDiscussionCoordinator()
                    
                    # Extract task from thread
                    task = None
                    thread = client.conversations_replies(channel=coordination_channel, ts=thread_ts)
                    for msg in thread.get("messages", []):
                        task_match = re.search(r'Task: "(.*?)"', msg.get("text", ""), re.DOTALL)
                        if task_match:
                            task = task_match.group(1)
                            break
                    
                    if task:
                        # Run collaborative discussion
                        final_agent, final_confidence, final_evaluations = coordinator.facilitate_discussion(
                            task, specialists, client, coordination_channel, thread_ts
                        )
                        
                        if final_agent and final_confidence >= min_confidence:
                            specialist = specialists[final_agent]
                            logging.info(
                                "After discussion, assigning to %s (confidence: %s%%)", final_agent, final_confidence
                            )
                            client.chat_postMessage(
                                channel=coordination_channel,
                                thread_ts=thread_ts,
                                text=(
                                    f"ASSIGNED: <@{specialist.bot_user_id}> - Please handle this request."
                                ),
                            )
                            return
                        else:
                            logging.info("Discussion did not reach consensus above threshold")
                    
                except Exception as e:
                    logging.error("Failed to run collaborative discussion: %s", e)
                    # Fall back to regular assignment
            
            # Regular assignment (or fallback)
            agent_name, confidence = max(evaluations.items(), key=lambda x: x[1])
            if confidence >= min_confidence and agent_name in specialists:
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
                logging.info(
                    "Highest confidence %s%% is below threshold %s%%", 
                    confidence, min_confidence
                )
                client.chat_postMessage(
                    channel=coordination_channel,
                    thread_ts=thread_ts,
                    text=f"No specialist confident enough to handle this request. (Highest: {agent_name} with {confidence}%, threshold: {min_confidence}%)",
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
        logging.error("Assignment error during evaluation loop: %s", err, exc_info=True)
        try:
            client.chat_postMessage(
                channel=coordination_channel,
                thread_ts=thread_ts,
                text=f"Error during assignment: {err}",
            )
        except Exception:
            pass 