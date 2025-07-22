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
from src.orchestrator.assignment import check_and_assign
from src.orchestrator.handlers import register_specialist_handlers

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
active_requests: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

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
    threading.Thread(
        target=check_and_assign,
        args=(client, coord_thread_ts, active_requests[coord_thread_ts], specialists, coordination_channel),
        daemon=True
    ).start()

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
            args=(client, coord_thread_ts, active_requests[coord_thread_ts], specialists, coordination_channel),
            daemon=True
        ).start()

    @orchestrator.app.event('message')
    def suppress_orchestrator_messages(event, logger):
        pass  # Orchestrator ignores channel chatter

    # ------------------------------------------------ Specialist handlers (moved to src/orchestrator/handlers.py)

    # Register handlers for each specialist using refactored helper
    for n, s in specialists.items():
        register_specialist_handlers(s, n, coordination_channel, orchestrator, active_requests)

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