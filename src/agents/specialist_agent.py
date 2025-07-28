import re
import importlib
import logging
from typing import Dict, Any, List, Callable

from smolagents import LiteLLMModel
from src.core.friendly_code_agent import FriendlyCodeAgent
from src.core.base_agent import BaseAgent
from src.integrations.zoom_client import ZoomClient


class SpecialistAgent(BaseAgent):
    """An intelligent agent initialized from a profile."""

    def __init__(self, agent_profile: dict, slack_token: str, coordination_channel: str, use_dspy: bool = False):
        self.agent_profile = agent_profile
        super().__init__(name=self.agent_profile['name'], token=slack_token)

        self.coordination_channel = coordination_channel
        self.thinking_step = 0
        self.pending_requests: Dict[str, Dict[str, Any]] = {}

        initialized_tools = self._initialize_tools()

        # Check if DSPy should be used (make it optional)
        self.use_dspy = use_dspy or agent_profile.get('use_dspy', False)
        self.dspy_available = False
        
        if self.use_dspy:
            # Try to use DSPy agent, but fall back gracefully
            try:
                if self.name == "Grok":
                    # Use specialized Grok DSPy agent
                    from .dspy_modules import GrokDSPyAgent
                    self.ai_agent = GrokDSPyAgent(
                        tools=initialized_tools,
                        model_id=self.agent_profile['model_id'],
                        system_prompt=self.agent_profile['system_prompt']
                    )
                    self.logger.info(f"[{self.name}] 🧠 Initialized with Grok DSPy agent")
                    self.dspy_available = True
                elif self.name == "Writer":
                    # Use specialized Writer DSPy module with Socratic capabilities
                    from .dspy_modules import WriterModule
                    # Create a wrapper that has the expected interface
                    class WriterDSPyAgent:
                        def __init__(self, tools, model_id, system_prompt):
                            self.module = WriterModule()
                            self.tools = tools
                            self.logger = logging.getLogger("WriterDSPyAgent")
                        
                        def forward(self, request: str, user_id: str = None, context: List[Dict] = None):
                            return self.module.forward(request, user_id=user_id, context=context)
                        
                        def run(self, prompt: str):
                            # Extract request from prompt for compatibility
                            request = prompt.split("User's request:")[-1].strip() if "User's request:" in prompt else prompt
                            return self.forward(request)
                
                    self.ai_agent = WriterDSPyAgent(
                        tools=initialized_tools,
                        model_id=self.agent_profile['model_id'],
                        system_prompt=self.agent_profile['system_prompt']
                    )
                    self.logger.info(f"[{self.name}] 🧠 Initialized with Writer DSPy module (with Socratic capabilities)")
                    self.dspy_available = True
                else:
                    # Use standard DSPy agent
                    from ..core.dspy_agent import DSPyAgent
                    self.ai_agent = DSPyAgent(
                        tools=initialized_tools,
                        model_id=self.agent_profile['model_id'],
                        system_prompt=self.agent_profile['system_prompt']
                    )
                    self.logger.info(f"[{self.name}] 🧠 Initialized with DSPy agent")
                    self.dspy_available = True
                    
            except Exception as e:
                self.logger.warning(f"[{self.name}] Failed to initialize DSPy: {e}. Falling back to standard agent.")
                self.use_dspy = False
                self.dspy_available = False
                # Fall through to FriendlyCodeAgent initialization
        
        if not self.use_dspy or not self.dspy_available:
            # Use existing FriendlyCodeAgent
            self.ai_agent = FriendlyCodeAgent(
                tools=initialized_tools,
                model=LiteLLMModel(
                    model_id=self.agent_profile['model_id'],
                    system=self.agent_profile['system_prompt']
                ),
                max_steps=3
            )
            self.logger.info(f"[{self.name}] 🤖 Initialized with FriendlyCodeAgent")

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

        if self.name == "Writer":
            confidence = 50
            # Socratic dialog requests - highest priority for Writer
            if any(k in request_lower for k in ['socratic', 'help me think', 'guide me through', 'explore with me', 'let\'s discuss']):
                confidence = 98  # Very high confidence for Socratic dialog
                self.logger.debug(f"[{self.name}] Detected Socratic dialog request")
            elif any(k in request_lower for k in ['write', 'story', 'compose', 'draft', 'poem', 'creative']):
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
            
            # Check if this is a Socratic dialog request - Grok should NOT handle these
            if any(k in request_lower for k in ['socratic', 'help me think', 'guide me through', 'explore with me', 'let\'s discuss']):
                # Grok should have low confidence for Socratic requests - let Writer handle them
                confidence = 20
                self.logger.debug(f"[{self.name}] Detected Socratic request, deferring to Writer")
            # Weather and astronomical requests - very high priority
            elif any(k in request_lower for k in ['weather', 'temperature', 'forecast', 'rain', 'snow', 'sunny', 'cloudy', 
                                                   'sunrise', 'sunset', 'dawn', 'dusk', 'golden hour', 'sun rise', 'sun set',
                                                   'what time is sunset', 'what time is sunrise', 'when does the sun']):
                confidence = 96
                self.logger.debug(f"[{self.name}] Detected weather/astronomical request")
            # arXiv/academic paper requests - very high priority
            elif ('arxiv' in request_lower or 
                  ('paper' in request_lower and any(word in request_lower for word in ['find', 'search', 'get', 'download', 'look'])) or
                  any(k in request_lower for k in ['academic paper', 'research paper', 'publication', 'journal', 'preprint'])):
                confidence = 94
                self.logger.debug(f"[{self.name}] Detected arXiv/academic paper request")
            # URL fetching - highest priority for backward compatibility
            elif any(k in request_lower for k in ['url', 'link', 'website', 'fetch', 'http://', 'https://']):
                confidence = 95
            # Deep research keywords (but not if combined with Socratic)
            elif any(k in request_lower for k in ['research', 'investigate', 'deep dive', 'comprehensive', 'analysis']) and not any(k in request_lower for k in ['socratic', 'help me think']):
                confidence = 92
            # Question words that suggest research (but not Socratic exploration)
            elif any(k in request_lower for k in ['what is', 'how does', 'why does', 'explain', 'tell me about']) and not any(k in request_lower for k in ['socratic', 'explore with me']):
                confidence = 88
            # General search keywords
            elif any(k in request_lower for k in ['search', 'find', 'look up', 'information about']):
                confidence = 85
            elif has_temp_conversion:
                confidence = 85
            elif 'dm me' in request_lower or request_lower in ['hi', 'hello', 'hey']:
                confidence = 70
            # Any question mark suggests a research task (unless it's Socratic)
            elif '?' in request_lower and not any(k in request_lower for k in ['socratic', 'help me think']):
                confidence = 80
            result = confidence >= 60, min(confidence, 95)
            self.logger.debug(f"[{self.name}] ⇦ Exit evaluate_request → {result}")
            return result

        self.logger.debug(f"[{self.name}] ⇦ Exit evaluate_request → (False, 0)")
        return False, 0

    # ---------------------------------------------------------------------
    # Collaborative evaluation
    # ---------------------------------------------------------------------
    def collaborative_evaluate(self, task: str, discussion_history: List[Dict]) -> tuple[int, str]:
        """Evaluate task collaboratively, considering other agents' evaluations."""
        # First get base evaluation
        can_handle, base_confidence = self.evaluate_request(task)
        
        if not can_handle:
            return base_confidence, f"{self.name} cannot handle this type of request"
        
        # If we have DSPy negotiation capabilities, use them
        if self.use_dspy:
            try:
                from src.agents.negotiation_module import CollaborativeEvaluator
                
                # Create evaluator with agent's capabilities
                capabilities = self.agent_profile.get('description', f'{self.name} specialist agent')
                evaluator = CollaborativeEvaluator(self.name, capabilities)
                
                # Get adjustment based on discussion
                adjustment, reasoning = evaluator.evaluate_with_discussion(task, discussion_history)
                
                # Apply adjustment to base confidence
                new_confidence = max(0, min(100, base_confidence + adjustment))
                
                self.logger.info(f"[{self.name}] Collaborative evaluation: base={base_confidence}%, adjustment={adjustment}, final={new_confidence}%")
                
                return new_confidence, reasoning
                
            except Exception as e:
                self.logger.error(f"[{self.name}] Failed to use collaborative evaluator: {e}")
                # Fall back to base evaluation
        
        # Default: return base evaluation with simple reasoning
        reasoning = f"{self.name} has {base_confidence}% confidence based on capabilities"
        return base_confidence, reasoning

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
            elif request_lower in ["hello", "hi", "hey", "hello!", "hi!", "hey!"]:
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
                        # Handle both old-style inputs dict and new-style parameters
                        if hasattr(t, 'inputs') and isinstance(t.inputs, dict):
                            inputs = t.inputs
                            params: list[str] = []
                            for p_name, p_info in inputs.items():
                                if isinstance(p_info, dict) and p_info.get('default') is not None:
                                    params.append(f"{p_name}=None")
                                else:
                                    params.append(p_name)
                            sig = f"{t.name}({', '.join(params)})"
                        else:
                            # For tools without inputs metadata, show simple signature
                            sig = f"{t.name}(...)"
                        tool_descriptions.append(f"- {sig}")

                self.logger.info(f"[{self.name}] 🛠️ Available tools: {tool_names}")

                tools_list = "\n".join(tool_descriptions) if tool_descriptions else (
                    "- slack_dm_tool(user_id, message)\n- slack_channel_tool(channel_id, message, thread_ts=None)"
                )

                # Check for Socratic dialog request first
                is_socratic_request = any(word in request_lower for word in ['socratic', 'help me think', 'guide me through', 'explore with me', 'let\'s discuss'])
                
                # Check for arXiv-specific requests first
                is_arxiv_request = ('arxiv' in request_lower or 
                                   ('paper' in request_lower and any(word in request_lower for word in ['find', 'search', 'get', 'download', 'look'])) or
                                   any(word in request_lower for word in ['academic paper', 'research paper', 'publication', 'journal', 'preprint']))
                
                # Special handling for arXiv requests
                if self.name == "Grok" and is_arxiv_request:
                    self.logger.info(f"[{self.name}] 📚 Detected arXiv request")
                    
                    # Parse the request to determine what to search for
                    search_query = request_text
                    # Remove common prefixes and clean up the query
                    for prefix in ['find an arxiv paper on', 'find arxiv paper on', 'search arxiv for', 'arxiv paper on', 'arxiv papers on', 'find me ai papers from', 'find me papers from']:
                        if prefix in request_lower:
                            search_query = request_text[len(prefix):].strip()
                            break
                    
                    # Clean up the query - remove question marks, extra words, etc.
                    search_query = search_query.replace('?', '').replace('please', '').strip()
                    # Remove common filler words
                    filler_words = ['please', 'can you', 'could you', 'would you', 'will you', 'i need', 'i want']
                    for word in filler_words:
                        search_query = search_query.replace(word, '').strip()
                    
                    # Extract key terms for better search
                    if 'harvard' in search_query.lower() and 'berkman' in search_query.lower():
                        # For Harvard Berkman Klein Center queries, focus on the key terms
                        search_query = 'harvard berkman klein center ai papers'
                    elif 'ai' in search_query.lower() and 'papers' in search_query.lower():
                        # For general AI papers queries, clean up
                        search_query = search_query.replace('ai papers', 'artificial intelligence').replace('papers', 'research')
                    
                    # Execute arXiv search directly
                    try:
                        from src.tools.arxiv_tools import search_arxiv_papers
                        self.logger.info(f"[{self.name}] 🔍 Searching arXiv for: '{search_query}'")
                        search_results = search_arxiv_papers(query=search_query)
                        
                        # Send results to user
                        dm_message = f"Here are arXiv papers on '{search_query}':\n\n{search_results}\n\n— {self.name}"
                        dm_result = self.client.chat_postMessage(
                            channel=original_user,
                            text=dm_message
                        )
                        self.logger.info(f"[{self.name}] ✅ arXiv results sent via DM: {dm_result['ok']}")
                        
                        # Report completion
                        self.client.chat_postMessage(
                            channel=self.coordination_channel,
                            text=f"✅ {self.name} completed – arXiv search results sent to <@{original_user}>",
                            thread_ts=thread_ts
                        )
                        return
                    except Exception as e:
                        self.logger.error(f"[{self.name}] ❌ arXiv search failed: {e}", exc_info=True)
                        # Send error message to user
                        error_msg = f"I encountered an error searching arXiv: {str(e)}\n\nPlease try rephrasing your request.\n\n— {self.name}"
                        self.client.chat_postMessage(channel=original_user, text=error_msg)
                        self.client.chat_postMessage(
                            channel=self.coordination_channel,
                            text=f"❌ {self.name} error: arXiv search failed - {str(e)}",
                            thread_ts=thread_ts
                        )
                        return
                
                # Weather queries - handle directly
                elif any(word in request_lower for word in ['weather', 'temperature', 'forecast', 'sunrise', 'sunset']) and self.name == "Grok":
                    self.logger.info(f"[{self.name}] 🌤️ Handling weather request directly")
                    try:
                        # Extract location from request
                        location = None
                        if ' in ' in request_lower:
                            location = request_text.split(' in ', 1)[1].strip().rstrip('?').rstrip('.')
                        elif ' for ' in request_lower:
                            location = request_text.split(' for ', 1)[1].strip().rstrip('?').rstrip('.')
                        
                        # Determine which weather function to use
                        if 'sunrise' in request_lower or 'sunset' in request_lower:
                            from src.tools.weather_tools import get_sunrise_sunset
                            result = get_sunrise_sunset(location=location)
                        elif 'forecast' in request_lower:
                            from src.tools.weather_tools import get_weather_forecast
                            result = get_weather_forecast(location=location)
                        else:
                            from src.tools.weather_tools import get_current_weather
                            result = get_current_weather(location=location)
                        
                        # Send results
                        dm_message = f"{result}\n\n— {self.name}"
                        self.client.chat_postMessage(channel=original_user, text=dm_message)
                        self.client.chat_postMessage(
                            channel=self.coordination_channel,
                            text=f"✅ {self.name} completed – weather info sent to <@{original_user}>",
                            thread_ts=thread_ts
                        )
                        return
                    except Exception as e:
                        self.logger.error(f"[{self.name}] Weather request failed: {e}")
                        # Fall through to AI agent
                
                # Special handling for research queries (but not if it's a Socratic request)
                elif (not is_socratic_request and 
                      any(word in request_lower for word in ['research', 'search', 'find', 'investigate', 'deep dive', 'deep research', 'how starfish', 'starfish'])
                      and self.name == "Grok"):
                    # Extract the research topic from the request
                    topic = request_text
                    for prefix in ['do deep research query on', 'do deep research qeury on', 'can you do a deep research task on', 'research on', 'search for', 'find information about', 'tell me about']:
                        if prefix in request_lower:
                            topic = request_text.lower().split(prefix)[-1].strip()
                            break
                    topic = topic.replace('how ', '').replace('?', '').strip()
                    
                    # Directly execute the deep research tool instead of going through the AI agent
                    self.logger.info(f"[{self.name}] 🔍 Directly executing deep research on topic: '{topic}'")
                    try:
                        from src.tools.agent_tools import deep_research_tool
                        research_result = deep_research_tool(topic, 3)
                        
                        # Send results to user
                        dm_message = f"Here's my research on '{topic}':\n\n{research_result}\n\n— {self.name}"
                        dm_result = self.client.chat_postMessage(
                            channel=original_user,
                            text=dm_message
                        )
                        self.logger.info(f"[{self.name}] ✅ Research results sent via DM: {dm_result['ok']}")
                        
                        # Report completion
                        self.client.chat_postMessage(
                            channel=self.coordination_channel,
                            text=f"✅ {self.name} completed – deep research results sent to <@{original_user}>",
                            thread_ts=thread_ts
                        )
                        return
                    except Exception as e:
                        self.logger.error(f"[{self.name}] ❌ Deep research execution failed: {e}", exc_info=True)
                        # Fall through to normal processing
                        
                    thinking_prompt = (
                        f"You are {self.name}, an expert research specialist.\n\n"
                        f"The user wants research on: {topic}\n\n"
                        "You must call the deep_research_tool to gather comprehensive information.\n"
                        f"Execute this exact command:\n"
                        f"deep_research_tool('{topic}', 3)\n\n"
                        "That's it. Just output that single line, nothing else."
                    )
                else:
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
                
                # Determine if we really need DSPy for this task
                needs_complex_reasoning = (
                    is_socratic_request or
                    'analyze' in request_lower or
                    'explain' in request_lower or
                    'compare' in request_lower or
                    'evaluate' in request_lower or
                    len(request_text) > 100  # Long, complex requests
                )
                
                # Only use DSPy if it's available AND we need complex reasoning
                use_dspy_for_this_request = self.dspy_available and needs_complex_reasoning
                
                self.logger.info(f"Calling AI agent... (DSPy: {use_dspy_for_this_request})")

                try:
                    if use_dspy_for_this_request:
                        # DSPy execution - pass request directly with user_id and context
                        if hasattr(self.ai_agent, 'forward'):
                            # Check if the module accepts user_id and context
                            import inspect
                            sig = inspect.signature(self.ai_agent.forward)
                            params = sig.parameters
                            
                            if 'user_id' in params and 'context' in params:
                                result = self.ai_agent.forward(request_text, user_id=original_user, context=context)
                            elif 'context' in params:
                                result = self.ai_agent.forward(request_text, context=context)
                            else:
                                result = self.ai_agent.forward(request_text)
                        else:
                            result = self.ai_agent.run(thinking_prompt)
                        self.logger.info(f"[{self.name}] 🧠 DSPy agent returned: {str(result)[:200]}...")
                    else:
                        # Existing execution with thinking_prompt
                        result = self.ai_agent.run(thinking_prompt)
                        self.logger.info(f"[{self.name}] 🤖 AI agent returned: {str(result)[:200]}...")
                    
                    # Special handling for Grok research results
                            # The result should be the output of deep_research_tool
                        # Send it directly to the user
                        if isinstance(result, str) and "Deep Research Report" in result:
                            # Format the message nicely
                            dm_message = f"Here's my research on '{topic}':\n\n{result}\n\n— {self.name}"
                            dm_result = self.client.chat_postMessage(
                                channel=original_user,
                                text=dm_message
                            )
                            self.logger.info(f"Research results sent via DM: {dm_result['ok']}")
                            
                            # Report completion
                            self.client.chat_postMessage(
                                channel=self.coordination_channel,
                                text=f"✅ {self.name} completed – research results sent to <@{original_user}>",
                                thread_ts=thread_ts
                            )
                            return
                    
                    # If the result contains an error, handle it gracefully
                    if isinstance(result, str) and "ModelError:" in result:
                        # Extract the actual error message
                        error_msg = result.split("ModelError:", 1)[1].strip()
                        self.logger.error(f"Model error occurred: {error_msg}")
                        
                        # Try to provide a helpful response
                        if "string indices must be integers" in error_msg:
                            result = "I encountered an issue processing the research results. Let me try a simpler approach."
                            # Fallback to web search
                            from src.tools.agent_tools import web_search_tool
                            search_result = web_search_tool(request_text)
                            result = f"Here's what I found:\n\n{search_result}"
                        else:
                            result = f"I encountered an error: {error_msg}. Please try rephrasing your request."
                            
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