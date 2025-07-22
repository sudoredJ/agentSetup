import logging
import time
import re
from typing import Dict, Any
from yaspin import yaspin
from slack_sdk.errors import SlackApiError

__all__ = ["check_and_assign"]

def check_and_assign(client,
                     thread_ts: str,
                     request_data: dict | None,
                     specialists: Dict[str, Any],
                     coordination_channel: str,
                     timeout: int = 8,
                     check_interval: float = 0.5) -> None:
    """Poll the coordination thread, collect specialists' confidence reports and assign.

    Args:
        client: Slack WebClient.
        thread_ts: Thread timestamp in the coordination channel.
        request_data: Optional metadata dict (currently unused but kept for API parity).
        specialists: Mapping of specialist name → SpecialistAgent instance.
        coordination_channel: ID of the coordination channel.
        timeout: Max seconds to wait for all evaluations.
        check_interval: Poll interval in seconds.
    """
    start_time = time.time()

    logging.info(f"Checking thread {thread_ts} for evaluations... (timeout {timeout}s)")
    logging.info(f"Expected specialists: {list(specialists.keys())}")

    evaluations: Dict[str, int] = {}

    try:
        with yaspin(text="Waiting for evaluations", color="cyan") as spin:
            while time.time() - start_time < timeout:
                try:
                    # Fetch latest replies each loop so we don't miss late messages
                    thread = client.conversations_replies(channel=coordination_channel, ts=thread_ts)
                except SlackApiError as api_err:
                    if api_err.response.get("error") == "ratelimited":
                        retry_after = int(api_err.response.headers.get("Retry-After", 2))
                        logging.warning(
                            f"Rate limited when fetching thread {thread_ts}. Retrying after {retry_after}s…"
                        )
                        time.sleep(retry_after)
                        continue
                    raise

                for msg in thread.get("messages", []):
                    text = msg.get("text", "")
                    match = re.search(r'(?:🧠\s*)?(\w+)\s+reporting:\s+Confidence\s+(\d+)%', text)
                    if match:
                        agent_name = match.group(1)
                        confidence = int(match.group(2))
                        if agent_name not in evaluations:
                            evaluations[agent_name] = confidence
                            logging.info(f"  Found evaluation: {agent_name} = {confidence}%")
                            spin.text = f"Collected {len(evaluations)}/{len(specialists)} evaluations"

                if len(evaluations) >= len(specialists):
                    logging.info("All specialists have responded!")
                    break

                time.sleep(check_interval)

            spin.ok("✔")

        logging.info(
            f"Total evaluations received: {len(evaluations)} out of {len(specialists)} specialists"
        )
        missing = set(specialists.keys()) - set(evaluations.keys())
        if missing:
            logging.warning(f"Missing responses from: {missing}")

        if not evaluations:
            logging.info("No evaluations found. Dumping raw thread messages for debugging…")
            thread = client.conversations_replies(channel=coordination_channel, ts=thread_ts)
            for i, msg in enumerate(thread.get("messages", [])):
                logging.info(f"Message {i}: {msg.get('text', '')[:120]}")
            _post(client, coordination_channel, thread_ts, "No specialists responded to evaluation request.")
            return

        logging.info(f"Evaluations: {evaluations}")
        # Pick winner
        agent_name, confidence = max(evaluations.items(), key=lambda x: x[1])
        if confidence > 0 and agent_name in specialists:
            specialist = specialists[agent_name]
            logging.info(f"Assigning to {agent_name} (confidence: {confidence}%)")
            _post(
                client,
                coordination_channel,
                thread_ts,
                f"ASSIGNED: <@{specialist.bot_user_id}> - Please handle this request."
            )
        else:
            _post(client, coordination_channel, thread_ts, "No specialist confident enough to handle this request.")

    except Exception as exc:
        logging.error(f"Assignment error: {exc}", exc_info=True)
        _post(client, coordination_channel, thread_ts, f"Error during assignment: {str(exc)}")


def _post(client, channel: str, thread_ts: str, text: str) -> None:
    """Helper to post a message safely, swallowing errors."""
    try:
        client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=text)
    except Exception as e:
        logging.error(f"Failed to post message to {channel}: {e}") 