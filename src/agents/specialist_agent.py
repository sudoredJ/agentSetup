import logging
import time
import re
import importlib
from typing import Dict, Any, List, Callable
import json

from smolagents import LiteLLMModel
from src.core.friendly_code_agent import FriendlyCodeAgent
from src.core.base_agent import BaseAgent
from src.integrations.zoom_client import ZoomClient


class SpecialistAgent(BaseAgent):
    """An intelligent agent initialized from a profile."""

    def __init__(self, agent_profile: dict, slack_token: str, coordination_channel: str):
        self.agent_profile = agent_profile
        super().__init__(name=self.agent_profile['name'], token=slack_token)

        self.coordination_channel = coordination_channel
        self.thinking_step = 0
        self.pending_requests: Dict[str, Dict[str, Any]] = {}

        initialized_tools = self._initialize_tools()

        self.ai_agent = FriendlyCodeAgent(
            tools=initialized_tools,
            model=LiteLLMModel(
                model_id=self.agent_profile['model_id'],
                system=self.agent_profile['system_prompt']
            ),
            max_steps=3
        )

    # ---------------------------------------------------------------------
    # Tool initialisation
    # ---------------------------------------------------------------------
    def _initialize_tools(self) -> List[Callable]:
        """Initialize tools with verbose success/failure logging."""
        self.logger.debug("=== TOOL INITIALIZATION START ===")
        tool_list: List[Callable] = []

        if 'tools' not in self.agent_profile:
            self.logger.warning("No tools specified in profile – skipping initialization")
            return tool_list

        for tool_config in self.agent_profile['tools']:
            module_path = tool_config['module']
            try:
                self.logger.debug(f"Loading tool module '{module_path}'…")
                module = importlib.import_module(module_path)

                # Inject client and bot_name into the module (if the tool expects it)
                if hasattr(module, '_client'):
                    module._client = self.client
                    self.logger.debug(f"Injected Slack client into {module_path}")
                if hasattr(module, '_bot_name'):
                    module._bot_name = self.bot_name
                    self.logger.debug(f"Injected bot name '{self.bot_name}' into {module_path}")

                # If this is the zoom_tools module, inject ZoomClient and slack client
                if module_path == 'src.tools.zoom_tools':
                    if hasattr(module, '_zoom_client'):
                        module._zoom_client = getattr(self, '_zoom_stub', None) or ZoomClient()
                        self._zoom_stub = module._zoom_client  # cache so only one instance
                    if hasattr(module, '_slack_client'):
                        module._slack_client = self.client

                for func_name in tool_config.get('functions', []):
                    if hasattr(module, func_name):
                        attr = getattr(module, func_name)

                        # Check if it's already a tool instance (from @tool decorator)
                        if (
                            hasattr(attr, '__class__')
                            and hasattr(attr.__class__, '__name__')
                            and 'Tool' in attr.__class__.__name__
                        ):
                            # It's already a tool instance from @tool decorator
                            tool_list.append(attr)
                            self.logger.debug(f"Loaded tool instance '{func_name}' from '{module_path}'")
                        else:
                            # It's a regular function or something else
                            self.logger.warning(f"'{func_name}' in '{module_path}' is not a decorated tool")
                    else:
                        self.logger.error(f"Function '{func_name}' not found in module '{module_path}'")

            except Exception as e:
                self.logger.error(f"Could not load tools from module '{module_path}': {e}", exc_info=True)

        self.logger.info(f"Initialized {len(tool_list)} tools for agent '{self.name}'")
        self.logger.debug(f"Tool names: {[t.name if hasattr(t, 'name') else str(t) for t in tool_list]}")
        self.logger.debug("=== TOOL INITIALIZATION END ===")
        return tool_list

    # ---------------------------------------------------------------------
    # Request evaluation
    # ---------------------------------------------------------------------
    def evaluate_request(self, request_text: str) -> tuple[bool, int]:
        """Evaluate if this specialist can handle the request."""
        self.logger.debug(f"[{self.name}] ➜ Enter evaluate_request(request_text='{request_text}')")
        request_lower = request_text.lower().strip()

        # Temperature conversion detection
        temp_pattern = r'\b(\d+)\s*([cf])\s+to\s+([cf])\b'
        has_temp_conversion = bool(re.search(temp_pattern, request_lower))

        if self.name == "Researcher":
            confidence = 50
            if any(k in request_lower for k in ['research', 'find', 'search', 'what', 'how', 'why']):
                confidence = 90
            elif any(k in request_lower for k in ['tts', 'text to speech', 'say', 'speak', 'voice', 'audio']):
                confidence = 85  # Grok can handle TTS
            elif 'dm me' in request_lower or request_lower in ['hi', 'hello', 'hey']:
                confidence = 85
            elif has_temp_conversion:
                confidence = 80
            result = confidence >= 60, min(confidence, 95)
            self.logger.debug(f"[{self.name}] ⇦ Exit evaluate_request → {result}")
            return result

        elif self.name == "Writer":
            confidence = 50
            if any(k in request_lower for k in ['write', 'story', 'compose', 'draft', 'poem', 'creative']):
                confidence = 95
            elif any(k in request_lower for k in ['tts', 'text to speech', 'say', 'speak', 'voice', 'audio']):
                confidence = 80  # Writer can also handle TTS
            elif 'dm me' in request_lower or request_lower in ['hi', 'hello', 'hey']:
                confidence = 90
            elif has_temp_conversion:
                confidence = 60
            result = confidence >= 60, min(confidence, 95)
            self.logger.debug(f"[{self.name}] ⇦ Exit evaluate_request → {result}")
            return result

        elif self.name == "Grok":
            confidence = 50
            if any(k in request_lower for k in ['url', 'link', 'website', 'fetch', 'summarize', 'http']):
                confidence = 95
            elif 'dm me' in request_lower or request_lower in ['hi', 'hello', 'hey']:
                confidence = 70
            elif has_temp_conversion:
                confidence = 85
            elif any(k in request_lower for k in ['what', 'how', 'why', 'explain']):
                confidence = 75
            result = confidence >= 60, min(confidence, 95)
            self.logger.debug(f"[{self.name}] ⇦ Exit evaluate_request → {result}")
            return result

        self.logger.debug(f"[{self.name}] ⇦ Exit evaluate_request → (False, 0)")
        return False, 0

    # ---------------------------------------------------------------------
    # Task processing
    # ---------------------------------------------------------------------
    def process_assignment(self, request_text: str, original_user: str, thread_ts: str, context: list[dict] | None = None):
        """Process an assigned task with context awareness."""
        self.logger.info(f"[{self.name}] process_assignment called with:")
        self.logger.info(f"  - request_text: {request_text}")
        self.logger.info(f"  - original_user: {original_user}")
        self.logger.info(f"  - thread_ts: {thread_ts}")
        self.logger.info(f"  - context items: {len(context) if context else 0}")

        try:
            # Simple status update
            status_result = self.client.chat_postMessage(
                channel=self.coordination_channel,
                text=f"{self.name} working on task...",
                thread_ts=thread_ts
            )
            self.logger.debug(f"Status update posted: {status_result['ok']}")

            request_lower = request_text.lower()

            # Temperature conversion pattern
            temp_pattern = r'\b(\d+)\s*([cf])\s+to\s+([cf])\b'
            temp_match = re.search(temp_pattern, request_lower)

            # ------------------------------------------------- Temperature
            if temp_match:
                self.logger.info("Handling temperature conversion")
                value = int(temp_match.group(1))
                from_unit = temp_match.group(2).upper()
                to_unit = temp_match.group(3).upper()

                if from_unit == 'C' and to_unit == 'F':
                    result = (value * 9 / 5) + 32
                    message = f"🌡️ {value}°C = {result:.1f}°F"
                elif from_unit == 'F' and to_unit == 'C':
                    result = (value - 32) * 5 / 9
                    message = f"🌡️ {value}°F = {result:.1f}°C"
                else:
                    message = f"Same unit: {value}°{from_unit}"

                # DM user
                dm_result = self.client.chat_postMessage(
                    channel=original_user,
                    text=f"Here is the conversion you requested:\n\n{message}\n\n— {self.name}"
                )
                self.logger.info(f"DM sent to user: {dm_result['ok']}")

                # Report completion
                self.client.chat_postMessage(
                    channel=self.coordination_channel,
                    text=f"✅ {self.name} completed – result sent to <@{original_user}>",
                    thread_ts=thread_ts
                )
                return

            # ------------------------------------------------- DM me
            elif "dm me" in request_lower:
                self.logger.info("Handling DM request")
                match = re.search(r'dm me\s*["\']?(.*?)["\']?$', request_text, re.IGNORECASE)
                message = match.group(1).strip() if match and match.group(1) else f"Hello from {self.name}!"

                self.client.chat_postMessage(
                    channel=original_user,
                    text=f"👋 {message}\n\n— {self.name}"
                )

                self.client.chat_postMessage(
                    channel=self.coordination_channel,
                    text=f"✅ {self.name} completed – DM sent to <@{original_user}>",
                    thread_ts=thread_ts
                )
                return

            # ------------------------------------------------- Greeting
            elif any(word in request_lower for word in ["hello", "hi", "hey"]):
                self.logger.info("Handling greeting")
                self.client.chat_postMessage(
                    channel=original_user,
                    text=f"👋 Hello! I'm {self.name}, your AI assistant. How can I help you today?\n\n— {self.name}"
                )

                self.client.chat_postMessage(
                    channel=self.coordination_channel,
                    text=f"✅ {self.name} completed – greeting sent to <@{original_user}>",
                    thread_ts=thread_ts
                )
                return

            # ------------------------------------------------- TTS shortcut
            elif request_lower.startswith("tts") or request_lower.startswith("@tts"):
                self.logger.info("Handling TTS request directly")
                # Extract quoted text if present
                m = re.search(r'"(.+?)"', request_text)
                tts_text = m.group(1) if m else request_text[4:].strip()
                if not tts_text:
                    tts_text = "Hello!"

                try:
                    # Call slack_tts_tool directly
                    from src.tools.slack_tools import slack_tts_tool  # local import
                    result_msg = slack_tts_tool(original_user, tts_text)
                    self.client.chat_postMessage(
                        channel=self.coordination_channel,
                        text=f"✅ {self.name} completed TTS: {result_msg}",
                        thread_ts=thread_ts,
                    )
                except Exception as tts_err:
                    self.logger.error("TTS shortcut failed", exc_info=True)
                    self.client.chat_postMessage(
                        channel=self.coordination_channel,
                        text=f"❌ {self.name} TTS error: {tts_err}",
                        thread_ts=thread_ts,
                    )
                return

            # ------------------------------------------------- Complex → AI
            else:
                self.logger.info("Handling complex request with AI agent")

                # Build context string
                context_str = ""
                if context:
                    self.logger.debug("Building context from %d messages", len(context))
                    for m in context[-10:]:
                        if m.get("text") and not m.get("bot_id"):
                            context_str += f"User: {m['text']}\n"

                # Dynamically build tool signatures for prompt
                tool_descriptions: list[str] = []
                tool_names: list[str] = []
                for t in self.ai_agent.tools:
                    if getattr(t, 'name', None):
                        tool_names.append(t.name)
                        inputs = getattr(t, 'inputs', {})
                        params: list[str] = []
                        for p_name, p_info in inputs.items():
                            if p_info.get('default') is not None:
                                params.append(f"{p_name}=None")
                            else:
                                params.append(p_name)
                        sig = f"{t.name}({', '.join(params)})"
                        tool_descriptions.append(f"- {sig}")

                self.logger.info("Available tools: %s", tool_names)

                tools_list = "\n".join(tool_descriptions) if tool_descriptions else (
                    "- slack_dm_tool(user_id, message)\n- slack_channel_tool(channel_id, message, thread_ts=None)"
                )

                thinking_prompt = (
                    f"You are {self.name}, a helpful AI assistant.\n\n"
                    f"User's request: {request_text}\n\n"
                    "Recent conversation context:\n"
                    f"{context_str if context_str else '(No previous context)'}\n\n"
                    "Available tools (call exactly as shown, no markdown, no quotes):\n"
                    f"{tools_list}\n\n"
                    "When you are ready to answer, choose ONE of these actions:\n"
                    "1. If a direct message is appropriate → write a single line that is JUST the function call, e.g.\n"
                    f"   slack_dm_tool('{original_user}', 'Hello! …')\n"
                    "2. If replying in the thread is better → use slack_channel_tool with thread_ts.\n"
                    "3. If the user asks for TTS or text-to-speech → use slack_tts_tool(user_id, text).\n"
                    "4. If no tool is needed, output the plain answer text.\n\n"
                    "Do NOT wrap calls in back-ticks or code blocks. Output nothing else after the call line."
                )

                self.logger.debug(f"Prompt length: {len(thinking_prompt)} chars")
                self.logger.info("Calling AI agent...")

                try:
                    result = self.ai_agent.run(thinking_prompt)
                    self.logger.info(f"AI agent returned: {str(result)[:200]}...")
                except Exception as ai_error:
                    self.logger.error(f"AI agent error: {ai_error}", exc_info=True)
                    result = f"I encountered an error while processing your request: {str(ai_error)}"

                # Check if AI sent a message
                result_str = str(result).lower()
                if not any(phrase in result_str for phrase in ["dm sent", "message sent", "sent to"]):
                    self.logger.info("AI didn't send DM, sending fallback")

                    clean_result = str(result)
                    if "the answer is" in clean_result.lower():
                        clean_result = clean_result.split("the answer is", 1)[1].strip()

                    dm_result = self.client.chat_postMessage(
                        channel=original_user,
                        text=f"Regarding '{request_text}':\n\n{clean_result}\n\n— {self.name}"
                    )
                    self.logger.info(f"Fallback DM sent: {dm_result['ok']}")

                # Report completion
                self.client.chat_postMessage(
                    channel=self.coordination_channel,
                    text=f"✅ {self.name} completed task",
                    thread_ts=thread_ts
                )

        except Exception as e:
            self.logger.error(f"[{self.name}] Error in process_assignment: {e}", exc_info=True)
            try:
                self.client.chat_postMessage(
                    channel=self.coordination_channel,
                    text=f"❌ {self.name} error: {str(e)}",
                    thread_ts=thread_ts
                )
            except:
                pass