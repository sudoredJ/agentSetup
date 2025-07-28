"""Specialized DSPy modules for different agent types using BeautifulSoup search."""

import dspy
import logging
import os
import sys
from typing import List, Dict, Any

# Global flag to track if DSPy has been configured
_dspy_configured = False

def ensure_dspy_configured():
    """Ensure DSPy is configured with an LM before creating any modules."""
    global _dspy_configured
    
    if _dspy_configured:
        return
    
    logger = logging.getLogger("dspy_modules")
    
    try:
        # Check if LM is already configured
        if hasattr(dspy.settings, 'lm') and dspy.settings.lm:
            logger.info("DSPy LM already configured")
            _dspy_configured = True
            return
        
        # If not configured, try to configure with Claude
        logger.warning("DSPy LM not configured, attempting to configure...")
        
        # Create LiteLLM wrapper for DSPy
        class DSPyLiteLLMWrapper:
            def __init__(self, model_id, api_base=None, api_key=None):
                from litellm import completion
                self.model_id = model_id
                self.api_base = api_base
                self.api_key = api_key
                self.completion = completion
            
            def __call__(self, prompt, **kwargs):
                messages = [{"role": "user", "content": prompt}]
                response = self.completion(
                    model=self.model_id,
                    messages=messages,
                    api_base=self.api_base,
                    api_key=self.api_key,
                    **kwargs
                )
                return response.choices[0].message.content
            
            def __repr__(self):
                return f"DSPyLiteLLMWrapper(model={self.model_id})"
        
        # Configure with Claude
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            lm = DSPyLiteLLMWrapper(
                model_id="claude-3-haiku-20240307",
                api_base="https://api.anthropic.com/v1",
                api_key=api_key
            )
            dspy.settings.configure(lm=lm)  # Use correct API as per DSPy docs
            logger.info("Configured DSPy with Claude LM")
            _dspy_configured = True
        else:
            raise ValueError("No ANTHROPIC_API_KEY found for DSPy configuration")
            
    except Exception as e:
        logger.error(f"Failed to configure DSPy: {e}")
        raise RuntimeError(f"DSPy modules require LM configuration: {e}")

class ResearchModule(dspy.Module):
    """DSPy module for research-focused agents using BeautifulSoup search."""
    
    def __init__(self):
        super().__init__()
        ensure_dspy_configured()  # Ensure DSPy is configured before creating modules
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize LM for DSPy
        try:
            import litellm
            from litellm import completion
            
            # Create a DSPy-compatible LM wrapper
            class DSPyLiteLLMWrapper:
                def __init__(self):
                    self.logger = logging.getLogger(self.__class__.__name__)
                
                def __call__(self, prompt, **kwargs):
                    try:
                        # Use Claude for research tasks
                        response = completion(
                            model="claude-3-haiku-20240307",
                            messages=[{"role": "user", "content": prompt}],
                            api_base="https://api.anthropic.com/v1",
                            api_key=os.environ.get("ANTHROPIC_API_KEY")
                        )
                        return response.choices[0].message.content
                    except Exception as e:
                        self.logger.error(f"LM call failed: {e}")
                        return f"Error: {str(e)}"
                
                # DSPy compatibility methods
                def basic_request(self, prompt, **kwargs):
                    return self.__call__(prompt, **kwargs)
                
                def __repr__(self):
                    return "DSPyLiteLLMWrapper(model=claude-3-haiku-20240307)"
            
            # Configure DSPy with LM
            lm = DSPyLiteLLMWrapper()
            dspy.settings.configure(lm=lm)  # Use correct API as per DSPy docs
            
            # Create DSPy modules
            self.generate_queries = dspy.ChainOfThought("topic -> query1, query2, query3")
            self.synthesize = dspy.ChainOfThought("results -> summary")
            
            self.logger.info("Research module DSPy LM initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Research module LM: {e}")
            # Create mock DSPy modules for testing
            self.generate_queries = self._create_mock_chain("topic -> query1, query2, query3")
            self.synthesize = self._create_mock_chain("results -> summary")
            self.logger.warning("Using mock DSPy modules for testing")
        
        # Initialize BeautifulSoup search
        self._init_beautiful_search()
    
    def _create_mock_chain(self, signature):
        """Create a mock ChainOfThought for testing."""
        class MockChain:
            def __init__(self, sig):
                self.signature = sig
            
            def __call__(self, **kwargs):
                # Return mock structured output
                if "topic" in kwargs:
                    topic = kwargs["topic"]
                    return type('MockResult', (), {
                        'query1': f"research {topic}",
                        'query2': f"information about {topic}",
                        'query3': f"latest {topic} developments"
                    })()
                elif "results" in kwargs:
                    return type('MockResult', (), {
                        'summary': f"Mock summary of research results"
                    })()
                else:
                    return type('MockResult', (), {'output': 'Mock response'})()
        
        return MockChain(signature)
    
    def _init_beautiful_search(self):
        """Initialize BeautifulSoup search system."""
        try:
            # Add the tools directory to the path
            tools_path = os.path.join(os.path.dirname(__file__), '..', 'tools')
            if tools_path not in sys.path:
                sys.path.insert(0, tools_path)
            from beautiful_search import beautiful_search
            self.beautiful_search = beautiful_search
            self.logger.info("Research module initialized with BeautifulSoup search")
        except ImportError as e:
            self.logger.error(f"Failed to import BeautifulSoup search: {e}")
            self.beautiful_search = None
    
    def forward(self, topic: str) -> str:
        """Execute research using BeautifulSoup search."""
        if not self.beautiful_search:
            return "ERROR: BeautifulSoup search system not available"
        
        try:
            # Generate multiple search queries
            queries = self.generate_queries(topic=topic)
            
            # Execute searches using BeautifulSoup
            results = []
            search_queries = [queries.query1, queries.query2, queries.query3]
            
            for query in search_queries:
                if query and query.strip():
                    self.logger.info(f"Research query: {query}")
                    search_results = self.beautiful_search.search_with_fallbacks(query, 3)
                    
                    if search_results:
                        # Format results
                        formatted_results = []
                        for result in search_results:
                            formatted_results.append(
                                f"Title: {result['title']}\n"
                                f"Source: {result['source']}\n"
                                f"Content: {result['body'][:200]}...\n"
                                f"URL: {result['url']}\n"
                            )
                        results.append(f"Query: {query}\nResults:\n" + "\n".join(formatted_results))
                    else:
                        results.append(f"Query: {query}\nNo results found.")
            
            # Synthesize results
            if results:
                combined_results = "\n\n".join(results)
                summary = self.synthesize(results=combined_results)
                return summary.summary
            else:
                return f"No research results found for topic: {topic}"
                
        except Exception as e:
            self.logger.error(f"Research module error: {e}", exc_info=True)
            return f"Research failed: {str(e)}"

class WriterModule(dspy.Module):
    """DSPy module for writing-focused agents with Socratic capabilities."""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Ensure DSPy is configured before creating modules
        try:
            ensure_dspy_configured()
            
            # Test that LM is actually available
            if not hasattr(dspy.settings, 'lm') or not dspy.settings.lm:
                self.logger.error("DSPy LM not available after ensure_dspy_configured()")
                raise RuntimeError("DSPy LM not properly configured")
                
            self.planner = dspy.ChainOfThought("request -> outline")
            self.writer = dspy.ChainOfThought("outline, style -> content")
            self.editor = dspy.ChainOfThought("content -> edited_content")
            
            # Add Socratic module for dialog capabilities
            self.socratic_module = SocraticModule()
            self.logger.info("WriterModule initialized successfully with DSPy chains")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize WriterModule: {e}")
            raise
    
    
    def forward(self, request: str, style: str = "professional", user_id: str = None, context: List[Dict] = None) -> str:
        """Execute writing task or Socratic dialog using DSPy reasoning."""
        try:
            # Double-check LM is still configured
            if not hasattr(dspy.settings, 'lm') or not dspy.settings.lm:
                self.logger.error("DSPy LM lost during forward() call")
                ensure_dspy_configured()  # Try to reconfigure
            request_lower = request.lower()
            
            # Check if this is a Socratic dialog request
            if any(phrase in request_lower for phrase in ['socratic', 'help me think', 'guide me through', 'explore with me', 'let\'s discuss']):
                return self.socratic_module.forward(request, user_id, context)
            
            # Check if we're in an ongoing Socratic dialog
            elif context and self.socratic_module._is_dialog_continuation(context):
                return self.socratic_module.forward(request, user_id, context)
            
            # Otherwise, proceed with normal writing task
            else:
                # Plan the writing
                outline = self.planner(request=request)
                
                # Write content
                content = self.writer(outline=outline.outline, style=style)
                
                # Edit and refine
                edited = self.editor(content=content.content)
                
                return edited.edited_content
            
        except Exception as e:
            self.logger.error(f"Writer module error: {e}", exc_info=True)
            return f"Writing failed: {str(e)}"

class AnalysisModule(dspy.Module):
    """DSPy module for analysis-focused agents using BeautifulSoup search."""
    
    def __init__(self):
        super().__init__()
        self.analyzer = dspy.ChainOfThought("request, data -> analysis")
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Import BeautifulSoup search system
        try:
            import sys
            import os
            # Add the tools directory to the path
            tools_path = os.path.join(os.path.dirname(__file__), '..', 'tools')
            if tools_path not in sys.path:
                sys.path.insert(0, tools_path)
            from beautiful_search import beautiful_search
            self.beautiful_search = beautiful_search
            self.logger.info("Analysis module initialized with BeautifulSoup search")
        except ImportError as e:
            self.logger.error(f"Failed to import BeautifulSoup search: {e}")
            self.beautiful_search = None
    
    def forward(self, request: str) -> str:
        """Execute analysis using BeautifulSoup search for data gathering."""
        if not self.beautiful_search:
            return "ERROR: BeautifulSoup search system not available"
        
        try:
            # Extract key terms for search
            search_terms = self._extract_search_terms(request)
            
            # Gather data using BeautifulSoup search
            data_points = []
            for term in search_terms:
                self.logger.info(f"Analyzing: {term}")
                search_results = self.beautiful_search.search_with_fallbacks(term, 2)
                
                if search_results:
                    for result in search_results:
                        data_points.append({
                            'term': term,
                            'title': result['title'],
                            'content': result['body'],
                            'source': result['source']
                        })
            
            # Analyze the gathered data
            if data_points:
                # Format data for analysis
                data_str = "\n\n".join([
                    f"Term: {dp['term']}\nTitle: {dp['title']}\nContent: {dp['content'][:300]}...\nSource: {dp['source']}"
                    for dp in data_points
                ])
                
                analysis = self.analyzer(request=request, data=data_str)
                return analysis.analysis
            else:
                return f"No data found to analyze for request: {request}"
                
        except Exception as e:
            self.logger.error(f"Analysis module error: {e}", exc_info=True)
            return f"Analysis failed: {str(e)}"
    
    def _extract_search_terms(self, request: str) -> List[str]:
        """Extract key terms for search from the request."""
        # Simple extraction - in practice, you might use NLP
        words = request.lower().split()
        # Filter out common words and keep meaningful terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
        terms = [word for word in words if word not in stop_words and len(word) > 3]
        return terms[:5]  # Limit to 5 terms

class GrokDSPyAgent(dspy.Module):
    """Enhanced Grok agent using DSPy with BeautifulSoup search and Socratic dialog capabilities."""
    
    def __init__(self, tools: List[Any], model_id: str, system_prompt: str):
        super().__init__()
        self.tools = tools
        self.system_prompt = system_prompt  # Store the system prompt
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize DSPy with the model
        try:
            import litellm
            from litellm import completion
            
            # Create a DSPy-compatible LM wrapper
            class DSPyLiteLLMWrapper:
                def __init__(self, model_id, api_base=None, api_key=None):
                    self.model_id = model_id
                    self.api_base = api_base
                    self.api_key = api_key
                    self.logger = logging.getLogger(self.__class__.__name__)
                
                def __call__(self, prompt, **kwargs):
                    try:
                        response = completion(
                            model=self.model_id,
                            messages=[{"role": "user", "content": prompt}],
                            api_base=self.api_base,
                            api_key=self.api_key,
                            **kwargs
                        )
                        return response.choices[0].message.content
                    except Exception as e:
                        self.logger.error(f"LM call failed: {e}")
                        return f"Error: {str(e)}"
                
                # DSPy compatibility methods
                def basic_request(self, prompt, **kwargs):
                    return self.__call__(prompt, **kwargs)
                
                def __repr__(self):
                    return f"DSPyLiteLLMWrapper(model={self.model_id})"
            
            # Create the LM wrapper
            if "claude" in model_id:
                self.lm = DSPyLiteLLMWrapper(
                    model_id=model_id,
                    api_base="https://api.anthropic.com/v1",
                    api_key=os.environ.get("ANTHROPIC_API_KEY")
                )
            else:
                self.lm = DSPyLiteLLMWrapper(
                    model_id=model_id,
                    api_key=os.environ.get("OPENAI_API_KEY")
                )
            
            # Configure DSPy to use our LM
            dspy.settings.configure(lm=self.lm)  # Use correct API as per DSPy docs
            self.logger.info(f"Grok DSPy LM initialized with model: {model_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize LM: {e}")
            # Create a mock LM for testing
            self.lm = self._create_mock_lm()
            self.logger.warning("Using mock LM for testing - DSPy features will be limited")
        
        # Initialize components
        self._init_modules()
        self._init_tool_selector()
        self._init_system_prompt()
    
    def _create_mock_lm(self):
        """Create a mock LM for testing when real LM is not available."""
        class MockLM:
            def __init__(self):
                self.logger = logging.getLogger(self.__class__.__name__)
            
            def __call__(self, prompt, **kwargs):
                # Simple mock response for testing
                if "research" in prompt.lower():
                    return "Mock research response: Here's some research about the topic."
                elif "tool" in prompt.lower():
                    return "tool_name: web_search_tool, tool_args: query=test"
                else:
                    return "Mock response: This is a test response from the mock LM."
        
        return MockLM()
    
    def _create_mock_research_module(self):
        """Create a mock research module for testing."""
        class MockResearchModule:
            def __init__(self):
                self.logger = logging.getLogger(self.__class__.__name__)
            
            def __call__(self, topic):
                return f"Mock research results for topic: {topic}"
        
        return MockResearchModule()
    
    def _init_modules(self):
        """Initialize specialized modules."""
        # Add specialized modules
        try:
            self.research_module = ResearchModule()
        except Exception as e:
            self.logger.error(f"Failed to create research module: {e}")
            self.research_module = self._create_mock_research_module()
            
        try:
            self.socratic_module = SocraticModule()
        except Exception as e:
            self.logger.error(f"Failed to create socratic module: {e}")
            self.socratic_module = None
        
        # Ensure research_module exists
        if not hasattr(self, 'research_module') or self.research_module is None:
            self.research_module = self._create_mock_research_module()
    
    def _init_tool_selector(self):
        """Initialize tool selector."""
        try:
            self.tool_selector = dspy.ChainOfThought("request, context -> tool_name, tool_args")
        except Exception as e:
            self.logger.error(f"Failed to create tool selector: {e}")
            # Create a mock tool selector
            self.tool_selector = self._create_mock_tool_selector()
    
    def _create_mock_tool_selector(self):
        """Create a mock tool selector for testing."""
        class MockToolSelector:
            def __init__(self):
                self.logger = logging.getLogger(self.__class__.__name__)
            
            def __call__(self, request, context):
                # Return mock structured output
                return type('MockDecision', (), {
                    'tool_name': 'web_search_tool',
                    'tool_args': 'query=test'
                })()
        
        return MockToolSelector()
    
    def _init_system_prompt(self):
        """Initialize system prompt."""
        # System prompt is already stored in __init__
        pass
        
    def forward(self, request: str, context: List[Dict] = None) -> str:
        """Enhanced execution with research and Socratic capabilities."""
        request_lower = request.lower()
        
        # First check if this is a Socratic dialog request - PRIORITY
        if any(phrase in request_lower for phrase in ['socratic', 'help me think', 'guide me through', 'explore with me', 'let\'s discuss']):
            # Check if we have Socratic module
            if hasattr(self, 'socratic_module') and self.socratic_module:
                self.logger.info("Grok handling Socratic dialog request")
                # Extract user_id from context if available
                user_id = self._extract_user_id(context)
                return self.socratic_module.forward(request, user_id=user_id, context=context)
            else:
                return "I'd love to engage in Socratic dialog, but I need the Socratic module to be properly initialized first."
        
        # Check if we're continuing a Socratic dialog
        elif context and hasattr(self, 'socratic_module') and self.socratic_module and self.socratic_module._is_dialog_continuation(context):
            self.logger.info("Grok continuing Socratic dialog")
            user_id = self._extract_user_id(context)
            return self.socratic_module.forward(request, user_id=user_id, context=context)
        
        # Then check if this is a research request
        elif any(word in request_lower for word in ['research', 'investigate', 'deep dive', 'search', 'find']):
            # Extract topic
            topic = self._extract_topic(request)
            
            # Use DSPy research module with BeautifulSoup
            result = self.research_module(topic=topic)
            return result
        else:
            # Fall back to standard tool selection
            return self._execute_with_tools(request, context)
    
    def _extract_topic(self, request: str) -> str:
        """Extract research topic from request."""
        request_lower = request.lower()
        for prefix in ['research on', 'investigate', 'deep dive on', 'search for', 'find information about']:
            if prefix in request_lower:
                return request_lower.split(prefix)[-1].strip()
        return request
    
    def _execute_with_tools(self, request: str, context: List[Dict] = None) -> str:
        """Execute request using available tools."""
        try:
            # Format available tools
            tool_descriptions = []
            tool_map = {}
            
            for tool in self.tools:
                if hasattr(tool, 'name'):
                    tool_map[tool.name] = tool
                    sig = self._extract_tool_signature(tool)
                    tool_descriptions.append(sig)
            
            tools_str = "\n".join(tool_descriptions)
            context_str = self._format_context(context) if context else "No previous context"
            
            # Use DSPy to select tool
            decision = self.tool_selector(request=request, context=context_str)
            
            self.logger.info(f"Grok DSPy selected tool: {decision.tool_name}")
            
            # Execute the selected tool
            if decision.tool_name in tool_map:
                tool = tool_map[decision.tool_name]
                args = self._parse_tool_args(decision.tool_args)
                result = tool(**args) if isinstance(args, dict) else tool(*args)
                return str(result)
            else:
                return f"Tool '{decision.tool_name}' not found. Available: {list(tool_map.keys())}"
                
        except Exception as e:
            self.logger.error(f"Grok DSPy execution error: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    def _extract_tool_signature(self, tool) -> str:
        """Extract tool signature for DSPy context."""
        if hasattr(tool, '__doc__') and tool.__doc__:
            lines = tool.__doc__.strip().split('\n')
            desc = lines[0] if lines else ""
            return f"{tool.name}: {desc}"
        else:
            return f"{tool.name}: No description available"
    
    def _format_context(self, context: List[Dict]) -> str:
        """Format conversation context for DSPy."""
        if not context:
            return ""
        
        formatted = []
        for msg in context[-10:]:
            if msg.get("text") and not msg.get("bot_id"):
                formatted.append(f"User: {msg['text']}")
        
        return "\n".join(formatted)
    
    def _parse_tool_args(self, args_str: str) -> Dict[str, Any]:
        """Parse tool arguments from DSPy output."""
        args = {}
        if not args_str:
            return args
            
        pairs = args_str.split(',')
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                
                try:
                    if value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
                    elif value.isdigit():
                        value = int(value)
                    elif '.' in value and value.replace('.', '').isdigit():
                        value = float(value)
                except:
                    pass
                
                args[key] = value
        
        return args

    def run(self, prompt: str, *args, **kwargs) -> str:
        """Compatibility method to match existing interface."""
        request = self._extract_request_from_prompt(prompt)
        return self.forward(request)
    
    def _extract_request_from_prompt(self, prompt: str) -> str:
        """Extract the actual request from a formatted prompt."""
        lines = prompt.split('\n')
        for line in lines:
            if "User's request:" in line:
                return line.split("User's request:")[1].strip()
            elif "request:" in line.lower():
                return line.split("request:")[1].strip()
        
        for line in reversed(lines):
            if line.strip() and not line.startswith(('You are', 'Available tools', 'When you are ready')):
                return line.strip()
        
        return prompt.strip()
    
    def _extract_user_id(self, context: List[Dict] = None) -> str:
        """Extract user ID from context messages."""
        if not context:
            return None
        
        # Look for user messages in context
        for msg in context:
            if msg.get("user") and not msg.get("bot_id"):
                return msg.get("user")
        
        # If no user found in context, check if we have user info in message
        for msg in reversed(context):
            if msg.get("user"):
                return msg.get("user")
        
        return None


class SocraticModule(dspy.Module):
    """DSPy module for Socratic dialog capabilities."""
    
    def __init__(self):
        super().__init__()
        ensure_dspy_configured()  # Ensure DSPy is configured before creating modules
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # DSPy components for Socratic method
        self.theme_identifier = dspy.ChainOfThought("statement -> core_theme, assumptions")
        self.question_generator = dspy.ChainOfThought("theme, stage, previous_answers -> next_question")
        self.insight_extractor = dspy.ChainOfThought("conversation -> key_insights")
        self.dialog_router = dspy.ChainOfThought("user_response, stage -> next_stage, response_type")
        
        # Dialog stages
        self.stages = ["exploring", "clarifying", "challenging", "reflecting"]
        self.current_stage_idx = 0
        
        # Import socratic tools
        try:
            import sys
            import os
            tools_path = os.path.join(os.path.dirname(__file__), '..', 'tools')
            if tools_path not in sys.path:
                sys.path.insert(0, tools_path)
            from socratic_tools import question_generator_tool, dialog_tracker_tool, insight_extractor_tool
            self.socratic_tools = {
                'question_generator': question_generator_tool,
                'dialog_tracker': dialog_tracker_tool,
                'insight_extractor': insight_extractor_tool
            }
            self.logger.info("Socratic module initialized with tools")
        except ImportError as e:
            self.logger.error(f"Failed to import Socratic tools: {e}")
            self.socratic_tools = None
    
    def forward(self, request: str, user_id: str = None, context: List[Dict] = None) -> str:
        """Execute Socratic dialog based on request."""
        try:
            request_lower = request.lower()
            
            # Check if this is a Socratic dialog request
            if any(phrase in request_lower for phrase in ['socratic', 'help me think', 'guide me through', 'explore with me', 'let\'s discuss']):
                return self._initiate_socratic_dialog(request, user_id)
            
            # Check if we're continuing an existing dialog
            elif context and self._is_dialog_continuation(context):
                return self._continue_socratic_dialog(request, user_id, context)
            
            # Otherwise, generate a thoughtful question about the topic
            else:
                return self._generate_thoughtful_question(request)
                
        except Exception as e:
            self.logger.error(f"Socratic module error: {e}", exc_info=True)
            return f"I apologize, I encountered an error in my Socratic reasoning: {str(e)}"
    
    def _initiate_socratic_dialog(self, request: str, user_id: str) -> str:
        """Start a new Socratic dialog."""
        if not self.socratic_tools:
            return "I'd love to guide you through Socratic questioning, but my dialog tools aren't available right now."
        
        try:
            # Extract the theme from the request
            theme_analysis = self.theme_identifier(statement=request)
            core_theme = theme_analysis.core_theme
            
            # Track the dialog
            if user_id:
                self.socratic_tools['dialog_tracker'](user_id, "add_topic", core_theme)
            
            # Generate initial exploring questions
            questions = self.socratic_tools['question_generator'](
                topic=core_theme, 
                question_type="exploring"
            )
            
            # Format response
            response = [
                f"I'd be happy to explore '{core_theme}' with you through Socratic dialog! 🤔",
                "",
                "Let's begin by understanding your perspective:",
                "",
                questions,
                "",
                "*Please share your thoughts on any of these questions, and we'll dive deeper together.*"
            ]
            
            return "\n".join(response)
            
        except Exception as e:
            self.logger.error(f"Error initiating Socratic dialog: {e}")
            return "Let me help you explore this topic. What aspect would you like to examine first?"
    
    def _continue_socratic_dialog(self, response: str, user_id: str, context: List[Dict]) -> str:
        """Continue an ongoing Socratic dialog."""
        if not self.socratic_tools:
            return self._generate_thoughtful_question(response)
        
        try:
            # Analyze the user's response to determine next stage
            dialog_analysis = self.dialog_router(
                user_response=response,
                stage=self.stages[self.current_stage_idx]
            )
            
            # Extract insights from the response
            if len(response) > 50:  # Meaningful response
                insights = self.socratic_tools['insight_extractor'](response)
                if user_id and "No specific insights" not in insights:
                    self.socratic_tools['dialog_tracker'](user_id, "add_insight", response[:200])
            
            # Determine next question type
            next_stage = dialog_analysis.next_stage
            if next_stage in self.stages:
                self.current_stage_idx = self.stages.index(next_stage)
            else:
                # Progress through stages
                self.current_stage_idx = min(self.current_stage_idx + 1, len(self.stages) - 1)
            
            # Generate next question based on stage
            current_stage = self.stages[self.current_stage_idx]
            
            # Get conversation history
            conv_history = self._format_conversation_history(context)
            
            # Generate contextual question
            next_question_analysis = self.question_generator(
                theme=self._extract_theme_from_context(context),
                stage=current_stage,
                previous_answers=conv_history
            )
            
            # Use tool to generate actual questions
            questions = self.socratic_tools['question_generator'](
                topic=next_question_analysis.next_question,
                question_type=current_stage,
                context=response[:200]
            )
            
            # Format response based on stage
            stage_intros = {
                "exploring": "Interesting perspective! Let's explore further:",
                "clarifying": "Thank you for sharing. Let me help clarify some aspects:",
                "challenging": "I appreciate your thoughts. Let's examine this from another angle:",
                "reflecting": "We've covered a lot of ground. Let's reflect on what we've discovered:"
            }
            
            intro = stage_intros.get(current_stage, "Let's continue our exploration:")
            
            response_parts = [intro, "", questions]
            
            # Add stage-specific elements
            if current_stage == "reflecting" and user_id:
                summary = self.socratic_tools['dialog_tracker'](user_id, "get_summary")
                response_parts.extend(["", summary])
            
            return "\n".join(response_parts)
            
        except Exception as e:
            self.logger.error(f"Error continuing Socratic dialog: {e}")
            return self._generate_thoughtful_question(response)
    
    def _generate_thoughtful_question(self, topic: str) -> str:
        """Generate a single thoughtful question about any topic."""
        try:
            # Use DSPy to generate a Socratic-style question
            question_analysis = self.question_generator(
                theme=topic,
                stage="exploring",
                previous_answers=""
            )
            
            question = question_analysis.next_question
            
            return f"Here's a thought-provoking question to consider:\n\n{question}\n\n*What are your initial thoughts on this?*"
            
        except:
            # Fallback to simple question
            return f"That's an interesting topic. What aspects of '{topic}' are most important to you, and why?"
    
    def _is_dialog_continuation(self, context: List[Dict]) -> bool:
        """Check if we're in an ongoing Socratic dialog."""
        if not context:
            return False
        
        # Look for Socratic indicators in recent messages
        recent_messages = context[-5:] if len(context) >= 5 else context
        
        socratic_indicators = [
            'socratic', 'let\'s explore', 'thoughtful question',
            'what do you think', 'why do you believe', 'can you explain',
            'interesting perspective', 'let\'s examine', 'reflect on'
        ]
        
        for msg in recent_messages:
            if msg.get('text'):
                text_lower = msg['text'].lower()
                if any(indicator in text_lower for indicator in socratic_indicators):
                    return True
        
        return False
    
    def _format_conversation_history(self, context: List[Dict]) -> str:
        """Format conversation history for DSPy analysis."""
        if not context:
            return ""
        
        history = []
        for msg in context[-10:]:  # Last 10 messages
            if msg.get('text'):
                role = "User" if not msg.get('bot_id') else "Assistant"
                history.append(f"{role}: {msg['text'][:100]}...")
        
        return "\n".join(history)
    
    def _extract_theme_from_context(self, context: List[Dict]) -> str:
        """Extract the main theme from conversation context."""
        if not context:
            return "general topic"
        
        # Look for the original topic in the conversation
        for msg in context:
            text = msg.get('text', '')
            if any(phrase in text.lower() for phrase in ['explore', 'discuss', 'think about', 'socratic']):
                # Extract topic after these phrases
                for phrase in ['explore', 'discuss', 'think about']:
                    if phrase in text.lower():
                        parts = text.lower().split(phrase)
                        if len(parts) > 1:
                            return parts[1].strip().split('.')[0].strip()
        
        # Default to last user message
        for msg in reversed(context):
            if not msg.get('bot_id') and msg.get('text'):
                return msg['text'][:50]
        
        return "the topic at hand" 