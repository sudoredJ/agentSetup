import os
import sys
import yaml
import logging
import threading
import time
import re
import atexit
from typing import Dict, Any
from dotenv import load_dotenv
from collections import defaultdict, deque
import json
from rich.logging import RichHandler
from rich.console import Console
from rich.panel import Panel
from yaspin import yaspin
from slack_sdk.errors import SlackApiError
from src.core.config_loader import load_config  # NEW shared config loader

# Build the path to the .env file
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
dotenv_path = os.path.join(project_root, '.env')

# ----------------------------------------------------------------------------
# Logging setup (Rich)
# ----------------------------------------------------------------------------
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)]
)

# ----------------------------------------------------------------------------
# Environment loading
# ----------------------------------------------------------------------------
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, encoding='utf-8')
    logging.info(f"Loaded .env from {dotenv_path}")
else:
    logging.error(f"No .env file at {dotenv_path}")
    sys.exit(1)

sys.path.insert(0, project_root)

from src.core.base_agent import BaseAgent
from src.agents.specialist_agent import SpecialistAgent
from src.core.utils import sanitize_mentions

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
active_requests: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def _legacy_load_config(path: str = 'configs/system_config.yaml') -> dict:
    """Load YAML config and expand ${ENV} placeholders."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        placeholders = re.findall(r'\$\{(\w+)\}', content)
        for ph in placeholders:
            env_val = os.environ.get(ph)
            if env_val is None:
                logging.error(f"Missing env var referenced in config: {ph}")
                sys.exit(1)
            # replace both quoted and un-quoted occurrences
            content = content.replace(f'"${{{ph}}}"', f'"{env_val}"')
            content = content.replace(f'${{{ph}}}', env_val)

        return yaml.safe_load(content)
    except Exception as exc:
        logging.error(f"Config error: {exc}")
        sys.exit(1)

# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def main():
    console.print(Panel("[bold magenta]STARTING MULTI-AGENT SLACK SYSTEM[/bold magenta]", expand=False))

    config = load_config()

    # API keys
    if 'anthropic' in config.get('api_keys', {}):
        os.environ['ANTHROPIC_API_KEY'] = config['api_keys']['anthropic']

    handlers_to_close = []

    def _cleanup():
        """Close all SocketMode handlers without raising—even KeyboardInterrupt."""
        for h in handlers_to_close:
            try:
                h.close()
            except BaseException:
                # Ignore all errors during interpreter shutdown
                pass

    atexit.register(_cleanup)

    # ------------------------------------------------ Orchestrator
    with yaspin(text="Initializing Orchestrator", color="cyan") as spin:
        orchestrator = BaseAgent(name="Orchestrator", token=config['slack_tokens']['orchestrator_bot_token'])
        orchestrator.logger.setLevel(logging.INFO)
        orch_handler = orchestrator.start_in_thread(config['slack_tokens']['orchestrator_app_token'])
        handlers_to_close.append(orch_handler)
        spin.ok("✅ ")
    logging.info(f"Orchestrator ready: @{orchestrator.bot_name}")

    # ------------------------------------------------ Specialists
    specialists: Dict[str, SpecialistAgent] = {}
    profiles_dir = 'configs/agents'
    for fname in [f for f in os.listdir(profiles_dir) if f.endswith('.yaml')]:
        try:
            with open(os.path.join(profiles_dir, fname), 'r', encoding='utf-8') as f:
                profile = yaml.safe_load(f)
            agent_name = profile.get('name', 'Unknown')
            bot_token = config['slack_tokens'].get(f"{agent_name.lower()}_bot_token")
            app_token = config['slack_tokens'].get(f"{agent_name.lower()}_app_token")
            if not bot_token or not app_token:
                logging.error(f"Missing tokens for {agent_name}")
                continue
            with yaspin(text=f"Loading {agent_name}", color="yellow") as spin:
                spec = SpecialistAgent(
                    agent_profile=profile, 
                    slack_token=bot_token, 
                    coordination_channel=config['channels']['coordination']
                )
                spec.logger.setLevel(logging.INFO)
                handler = spec.start_in_thread(app_token)
                handlers_to_close.append(handler)
                specialists[agent_name] = spec
                spin.ok("✅ ")
            logging.info(f"{agent_name} ready: @{spec.bot_name}")
        except Exception as e:
            logging.error(f"Failed to load {fname}: {e}")

    if not specialists:
        logging.error("No specialists loaded – exiting")
        sys.exit(1)

    # ------------------------------------------------ Info dump
    logging.info("=== Specialist Bot IDs ===")
    for name, spec in specialists.items():
        logging.info(f"{name}: bot_user_id={spec.bot_user_id}, bot_name={spec.bot_name}")
    logging.info("========================")

    coordination_channel = config['channels']['coordination']

    # ------------------------------------------------ Assignment logic
    def check_and_assign(client, thread_ts: str, request_data: dict | None = None):
        """Poll the thread for evaluation messages and assign the best specialist."""
        timeout = 8          # seconds total wait (increased)
        check_interval = 0.5 # seconds between polls (decreased)
        start_time = time.time()

        logging.info(f"Checking thread {thread_ts} for evaluations... (timeout {timeout}s)")
        logging.info(f"Expected specialists: {list(specialists.keys())}")

        evaluations: Dict[str, int] = {}

        try:
            with yaspin(text="Waiting for evaluations", color="cyan") as spin:
                while time.time() - start_time < timeout:
                    try:
                        # Fresh API call every loop so we don't miss late messages
                        thread = client.conversations_replies(channel=coordination_channel, ts=thread_ts)
                    except SlackApiError as api_err:
                        # Handle rate limiting gracefully
                        if api_err.response.get("error") == "ratelimited":
                            retry_after = int(api_err.response.headers.get("Retry-After", 2))
                            logging.warning(f"Rate limited when fetching thread {thread_ts}. Retrying after {retry_after}s…")
                            time.sleep(retry_after)
                            continue  # retry loop without counting towards timeout
                        else:
                            raise

                    for msg in thread.get("messages", []):
                        text = msg.get("text", "")

                        # Pattern: agent evaluation report (with or without emoji)
                        # Try both patterns to be flexible
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

                # end while loop
                spin.ok("✔")

            logging.info(f"Total evaluations received: {len(evaluations)} out of {len(specialists)} specialists")
            missing_specialists = set(specialists.keys()) - set(evaluations.keys())
            if missing_specialists:
                logging.warning(f"Missing responses from: {missing_specialists}")
            
            if evaluations:
                logging.info(f"Evaluations: {evaluations}")
            else:
                logging.info("No evaluations found. Dumping raw thread messages for debugging…")
                thread = client.conversations_replies(channel=coordination_channel, ts=thread_ts)
                for i, msg in enumerate(thread.get("messages", [])):
                    logging.info(f"Message {i}: {msg.get('text', '')[:120]}")

            # Assign best specialist
            if evaluations:
                agent_name, confidence = max(evaluations.items(), key=lambda x: x[1])
                if confidence > 0 and agent_name in specialists:
                    specialist = specialists[agent_name]
                    logging.info(f"Assigning to {agent_name} (confidence: {confidence}%)")
                    try:
                        client.chat_postMessage(
                            channel=coordination_channel, 
                            thread_ts=thread_ts,
                            text=f"ASSIGNED: <@{specialist.bot_user_id}> - Please handle this request."
                        )
                    except Exception as e:
                        logging.error(f"Failed to post assignment: {e}")
                else:
                    client.chat_postMessage(
                        channel=coordination_channel, 
                        thread_ts=thread_ts,
                        text="No specialist confident enough to handle this request."
                    )
            else:
                logging.warning(f"No evaluations received in time!")
                try:
                    client.chat_postMessage(
                        channel=coordination_channel, 
                        thread_ts=thread_ts,
                        text="No specialists responded to evaluation request."
                    )
                except Exception as e:
                    logging.error(f"Failed to post no-response message: {e}")

        except Exception as e:
            logging.error(f"Assignment error: {e}", exc_info=True)
            try:
                client.chat_postMessage(
                    channel=coordination_channel, 
                    thread_ts=thread_ts,
                    text=f"Error during assignment: {str(e)}"
                )
            except Exception:
                pass

    # ------------------------------------------------ Orchestrator handlers
    @orchestrator.app.event("app_mention")
    def handle_orchestrator_mention(event: Dict[str, Any], client):
        if event.get("bot_id") is not None:
            return

        user_id = event.get("user")
        channel_id = event.get("channel")
        message_ts = event.get("ts")
        thread_ts = event.get("thread_ts", message_ts)
        raw_text = event.get("text", "")

        text = re.sub(fr'<@{orchestrator.bot_user_id}>', '', raw_text).strip()
        text = sanitize_mentions(text, client)

        logging.info(f"📨 New request from {user_id}: '{text}' (thread: {thread_ts})")

        context_messages = []
        if thread_ts != message_ts:
            try:
                thread = client.conversations_replies(channel=channel_id, ts=thread_ts, limit=20)
                for msg in thread.get("messages", []):
                    if msg.get("ts") != message_ts:
                        context_messages.append({
                            "user": msg.get("user", ""),
                            "text": msg.get("text", ""),
                            "type": "message"
                        })
            except Exception as e:
                logging.error(f"Error fetching thread context: {e}")

        try:
            client.reactions_add(channel=channel_id, timestamp=message_ts, name="thinking_face")
        except Exception:
            pass

        specialist_mentions = " ".join([f"<@{s.bot_user_id}>" for s in specialists.values()])
        coord_msg = client.chat_postMessage(
            channel=coordination_channel,
            text=f"Request from <@{user_id}> | Task: \"{text}\"\n\n{specialist_mentions} please evaluate."
        )

        coord_thread_ts = coord_msg['ts']
        active_requests[coord_thread_ts] = {
            'user_id': user_id,
            'channel_id': channel_id,
            'request': text,
            'timestamp': time.time(),
            'original_thread_ts': thread_ts if thread_ts != message_ts else None,
            'context': context_messages
        }

        threading.Thread(
            target=check_and_assign,
            args=(client, coord_thread_ts, active_requests[coord_thread_ts]),
            daemon=True
        ).start()

    @orchestrator.app.event('message')
    def suppress_orchestrator_messages(event, logger):
        pass  # Orchestrator ignores channel chatter

    # ------------------------------------------------ Specialist handlers
    def register_specialist_handlers(specialist: SpecialistAgent, specialist_name: str):
        """Register message/event handlers for a specialist with proper closure."""
        
        # Store references in the closure
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
                m_task = re.search(r'Task: "(.*?)"', text, re.DOTALL)
                if m_task:
                    task = m_task.group(1)
                    logger.info(f"{name} evaluating: '{task}'")
                    
                    # Run evaluation in a thread to avoid blocking
                    def run_evaluation():
                        try:
                            _, conf = spec.evaluate_request(task)
                            reply = f"🧠 {name} reporting: Confidence {conf}% for \"{task}\""
                            logger.info(f"{name} posting evaluation: {conf}%")
                            client.chat_postMessage(
                                channel=coordination_channel, 
                                thread_ts=msg_ts, 
                                text=reply
                            )
                        except Exception as e:
                            logger.error(f"{name} failed to post evaluation", exc_info=True)
                    
                    threading.Thread(target=run_evaluation, daemon=True).start()

            # ---------------- Assignment phase ----------------
            elif f"ASSIGNED: <@{spec.bot_user_id}>" in text:
                logger.info(f"{name} received assignment!")

                req_meta = active_requests.get(thread_ts, {})
                
                # Get thread messages
                try:
                    thread = client.conversations_replies(channel=coordination_channel, ts=thread_ts)
                except Exception as e:
                    logger.error(f"Failed to get thread replies: {e}")
                    return

                for msg in thread.get("messages", []):
                    # Fixed regex - single backslash
                    user_match = re.search(r'Request from <@(\w+)>', msg.get("text", ""))
                    task_match = re.search(r'Task: "(.*?)"', msg.get("text", ""), re.DOTALL)

                    if user_match and task_match:
                        user_id = user_match.group(1)
                        request_text = task_match.group(1)

                        # Build context
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
                            except Exception as fetch_err:
                                logger.error("Could not fetch original thread context", exc_info=True)

                        full_context = coord_context + orig_context

                        # --- Deep debug dump
                        logger.info(f"DEBUG: {name} Assignment details")
                        logger.info(f"  • request_text: '{request_text}'")
                        logger.info(f"  • user_id: {user_id}")
                        logger.info(f"  • context messages: {len(full_context)}")

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
                                        text=f"❌ {name} error: {type(err).__name__}: {err}",
                                        thread_ts=thread_ts,
                                    )
                                except Exception:
                                    pass

                        try:
                            t = threading.Thread(
                                target=run_assignment, 
                                name=f"{name}-Assign-{thread_ts[:8]}", 
                                daemon=True
                            )
                            t.start()
                            logger.info(f"Started thread {t.name}")
                        except Exception as thread_err:
                            logger.error("Failed to start assignment thread", exc_info=True)
                            client.chat_postMessage(
                                channel=coordination_channel,
                                text=f"❌ Thread creation failed for {name}: {thread_err}",
                                thread_ts=thread_ts,
                            )
                        break

        # other event handlers
        @spec.app.event('app_mention')
        def spec_mention_handler(event, client, logger):
            if event.get('channel') != coordination_channel:
                client.chat_postMessage(
                    channel=event['channel'], 
                    thread_ts=event.get('thread_ts', event['ts']),
                    text=f"Please mention <@{orchestrator.bot_user_id}> for assistance. I work through the orchestrator."
                )

        @spec.app.event('reaction_added')
        def spec_reaction_handler(event, logger):
            pass  # Suppress warnings

    # Register handlers for each specialist
    for n, s in specialists.items():
        register_specialist_handlers(s, n)
        logging.info(f"✓ Registered handlers for {n}")

    # ------------------------------------------------ Ready!
    console.print(Panel(
        f"[bold green]SYSTEM READY![/bold green]\n"
        f"Users mention [bold cyan]@{orchestrator.bot_name}[/bold cyan] for help\n"
        f"Active specialists: [yellow]{', '.join(specialists.keys())}[/yellow]\n"
        f"Coordination channel ID: [blue]{coordination_channel}[/blue]", 
        expand=False
    ))

    # connectivity check message
    time.sleep(3)
    for name, spec in specialists.items():
        try:
            res = spec.client.chat_postMessage(
                channel=coordination_channel, 
                text=f"🤖 {name} online and ready!"
            )
            if res.get('ok'):
                logging.info(f"✓ {name} connected to coordination channel")
            else:
                logging.error(f"✗ {name} failed connectivity post: {res}")
        except Exception as e:
            logging.error(f"✗ {name} connectivity test failed: {e}", exc_info=True)

    # Additional suppression for overly verbose third-party loggers
    for noisy in ['slack_sdk', 'slack_bolt', 'httpcore', 'httpx', 'urllib3']:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # keep process alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
        sys.exit(0)


if __name__ == '__main__':
    main()