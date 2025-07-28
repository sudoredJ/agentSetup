"""Specialized DSPy modules for different agent types using BeautifulSoup search."""

import dspy
import logging
import os
import sys
from typing import List, Dict, Any, Optional

# Global flag to track if DSPy has been configured
_dspy_configured = False

def ensure_dspy_configured(force_reset=False):
    """Ensure DSPy is configured with an LM before creating any modules."""
    global _dspy_configured
    
    logger = logging.getLogger("dspy_modules")
    
    # Always check if LM is actually configured, not just our flag
    if not force_reset and _dspy_configured and hasattr(dspy.settings, 'lm') and dspy.settings.lm:
        logger.debug("DSPy already configured with LM")
        return
    
    logger.info("Configuring DSPy...")
    
    try:
        # Check if LM is already configured
        if hasattr(dspy.settings, 'lm') and dspy.settings.lm:
            logger.info("DSPy LM already configured")
            _dspy_configured = True
            return
        
        # If not configured, try to configure with Claude via LiteLLM
        logger.warning("DSPy LM not configured, attempting to configure...")
        
        # Get API key
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("No ANTHROPIC_API_KEY found for DSPy configuration")
        
        # Configure LiteLLM to use Claude
        os.environ["ANTHROPIC_API_KEY"] = api_key  # Ensure it's set for LiteLLM
        
        # Use dspy.LM with LiteLLM backend
        # DSPy 2.5+ uses dspy.LM class
        try:
            # Try the newer DSPy API first
            # For Claude via litellm, use the anthropic/ prefix
            lm = dspy.LM(
                model="anthropic/claude-3-haiku-20240307",
                api_key=api_key
            )
            dspy.settings.configure(lm=lm)
            logger.info("Configured DSPy with Claude LM using dspy.LM")
            _dspy_configured = True
        except Exception as e1:
            logger.warning(f"Failed with dspy.LM: {e1}, trying legacy approach")
            
            # Fallback to older approach
            try:
                # Create a simple callable that works with DSPy
                class SimpleLM:
                    def __init__(self):
                        import litellm
                        self.litellm = litellm
                    
                    def __call__(self, prompt, **kwargs):
                        response = self.litellm.completion(
                            model="anthropic/claude-3-haiku-20240307",
                            messages=[{"role": "user", "content": prompt}],
                            api_key=api_key
                        )
                        return [response.choices[0].message.content]
                
                lm = SimpleLM()
                dspy.settings.configure(lm=lm)
                logger.info("Configured DSPy with Claude LM using SimpleLM wrapper")
                _dspy_configured = True
            except Exception as e2:
                logger.error(f"Both DSPy configuration attempts failed: {e1}, {e2}")
                raise RuntimeError(f"Failed to configure DSPy: {e2}")
            
    except Exception as e:
        logger.error(f"Failed to configure DSPy: {e}")
        raise RuntimeError(f"DSPy modules require LM configuration: {e}")

class ResearchModule(dspy.Module):
    """DSPy module for research-focused agents using BeautifulSoup search."""
    
    def __init__(self):
        super().__init__()
        ensure_dspy_configured()  # Ensure DSPy is configured before creating modules
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Create DSPy modules
        try:
            self.generate_queries = dspy.ChainOfThought("topic -> query1, query2, query3")
            self.synthesize = dspy.ChainOfThought("results -> summary")
            self.logger.info("Research module initialized successfully with DSPy chains")
        except Exception as e:
            self.logger.error(f"Failed to initialize Research module: {e}")
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
            from search.beautiful_search import beautiful_search
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
            # Double-check LM is still configured
            if not hasattr(dspy.settings, 'lm') or not dspy.settings.lm:
                self.logger.error("DSPy LM lost during ResearchModule.forward() call")
                ensure_dspy_configured()  # Try to reconfigure
            
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
            from search.beautiful_search import beautiful_search
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
        
        # Ensure DSPy is configured
        ensure_dspy_configured()
        
        # Store the model information
        self.model_id = model_id
        
        # Initialize components
        self._init_modules()
        self._init_tool_selector()
        self._init_system_prompt()
    
    
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
            # DSPy signature should be a simple one-line format
            self.tool_selector = dspy.ChainOfThought("request, available_tools, context -> tool_name, tool_args")
            self.logger.info("Tool selector initialized with DSPy ChainOfThought")
        except Exception as e:
            self.logger.error(f"Failed to create tool selector: {e}")
            # Create a fallback tool selector
            self.tool_selector = self._create_mock_tool_selector()
    
    def _create_mock_tool_selector(self):
        """Create a mock tool selector for testing."""
        class MockToolSelector:
            def __init__(self):
                self.logger = logging.getLogger(self.__class__.__name__)
            
            def __call__(self, request, available_tools=None, context=None):
                # This is a fallback when DSPy fails - use simple logic
                request_lower = request.lower()
                
                # Simple keyword-based tool selection
                if any(word in request_lower for word in ['weather', 'temperature', 'forecast', 'rain', 'snow', 'sunny', 'cloudy']):
                    return type('MockDecision', (), {
                        'tool_name': 'get_current_weather',
                        'tool_args': 'location=None'
                    })()
                elif any(word in request_lower for word in ['sunrise', 'sunset', 'dawn', 'dusk']):
                    return type('MockDecision', (), {
                        'tool_name': 'get_sunrise_sunset',
                        'tool_args': 'location=None'
                    })()
                elif 'arxiv' in request_lower or 'paper' in request_lower:
                    return type('MockDecision', (), {
                        'tool_name': 'search_arxiv_papers',
                        'tool_args': f'query={request}'
                    })()
                else:
                    # Default to web search
                    return type('MockDecision', (), {
                        'tool_name': 'web_search_tool',
                        'tool_args': f'query={request}'
                })()
        
        return MockToolSelector()
    
    def _init_system_prompt(self):
        """Initialize system prompt."""
        # System prompt is already stored in __init__
        pass
        
    def forward(self, request: str, context: List[Dict] = None) -> str:
        """Enhanced execution with keyword-based tool routing."""
        request_lower = request.lower()
        
        # Direct keyword-based tool routing
        try:
            # Weather-related queries
            if any(word in request_lower for word in ['weather', 'temperature', 'forecast', 'rain', 'snow', 'sunny', 'cloudy', 'humid', 'wind']):
                if 'forecast' in request_lower or 'next' in request_lower or 'tomorrow' in request_lower or 'week' in request_lower:
                    tool = self._get_tool_by_name('get_weather_forecast')
                else:
                    tool = self._get_tool_by_name('get_current_weather')
                
                if tool:
                    location = self._extract_location(request)
                    result = tool(location=location)
                    return str(result)
            
            # Sunrise/sunset queries
            elif any(word in request_lower for word in ['sunrise', 'sunset', 'dawn', 'dusk', 'golden hour', 'sun rise', 'sun set']):
                tool = self._get_tool_by_name('get_sunrise_sunset')
                if tool:
                    location = self._extract_location(request)
                    result = tool(location=location)
                    return str(result)
            
            # ArXiv/paper queries
            elif 'arxiv' in request_lower or any(phrase in request_lower for phrase in ['academic paper', 'research paper', 'scientific paper', 'journal article']):
                tool = self._get_tool_by_name('search_arxiv_papers')
                if tool:
                    # Extract search query
                    query = request
                    for prefix in ['search arxiv for', 'find arxiv paper on', 'arxiv paper on', 'find papers on']:
                        if prefix in request_lower:
                            query = request.split(prefix, 1)[1].strip()
                            break
                    result = tool(query=query)
                    return str(result)
            
            # University queries
            elif any(word in request_lower for word in ['university', 'universities', 'college', 'edu domain', '.edu']):
                # Check if it's an email verification
                if '@' in request and any(word in request_lower for word in ['verify', 'check', 'validate', 'email']):
                    tool = self._get_tool_by_name('verify_university_email')
                    if tool:
                        # Extract email from request
                        import re
                        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                        emails = re.findall(email_pattern, request)
                        if emails:
                            result = tool(email=emails[0])
                            return str(result)
                
                # Check if listing by country
                elif any(phrase in request_lower for phrase in ['universities in', 'colleges in', 'list universities']):
                    tool = self._get_tool_by_name('list_universities_by_country')
                    if tool:
                        # Extract country
                        country = None
                        if ' in ' in request_lower:
                            country = request.split(' in ', 1)[1].strip().rstrip('?.,!')
                            # Capitalize country name properly
                            country = ' '.join(word.capitalize() for word in country.split())
                            # Handle common variations
                            country_mapping = {
                                'Czechia': 'Czech Republic',
                                'Usa': 'United States',
                                'Uk': 'United Kingdom',
                                'Uae': 'United Arab Emirates'
                            }
                            country = country_mapping.get(country, country)
                        if country:
                            result = tool(country=country)
                            return str(result)
                
                # General university search
                else:
                    tool = self._get_tool_by_name('search_university')
                    if tool:
                        # Extract search parameters
                        kwargs = {}
                        
                        # Extract university name
                        for prefix in ['search for', 'find', 'look up', 'search university']:
                            if prefix in request_lower:
                                name = request.split(prefix, 1)[1].strip().rstrip('?.,!')
                                kwargs['name'] = name
                                break
                        
                        # If no specific search, use the whole request
                        if not kwargs:
                            kwargs['name'] = request.replace('university', '').replace('universities', '').strip()
                        
                        result = tool(**kwargs)
                        return str(result)
            
            # URL fetch requests
            elif any(indicator in request_lower for indicator in ['http://', 'https://', '.com', '.org', '.net', 'fetch url', 'summarize url']):
                tool = self._get_tool_by_name('fetch_and_summarize_tool')
                if tool:
                    # Extract URL from request
                    import re
                    url_pattern = r'https?://[^\s]+'
                    urls = re.findall(url_pattern, request)
                    if urls:
                        result = tool(url=urls[0])
                        return str(result)
            
            # Deep research requests (not weather/arxiv)
            elif any(word in request_lower for word in ['research', 'investigate', 'deep dive']) and not any(word in request_lower for word in ['weather', 'arxiv', 'paper']):
                tool = self._get_tool_by_name('deep_research_tool')
                if tool:
                    topic = self._extract_topic(request)
                    result = tool(topic=topic, num_searches=3)
                    return str(result)
            
            # General web search (including "what is" questions)
            elif any(phrase in request_lower for phrase in ['what is', 'what are', 'who is', 'define', 'explain', 'search for', 'look up']):
                tool = self._get_tool_by_name('web_search_tool')
                if tool:
                    # Clean up the query
                    query = request
                    for prefix in ['what is', 'what are', 'who is', 'define', 'explain', 'search for', 'look up']:
                        if prefix in request_lower:
                            query = request.lower().replace(prefix, '').strip()
                            break
                    result = tool(query=query)
                    return str(result)
            
            # Socratic dialog requests
            elif any(phrase in request_lower for phrase in ['socratic', 'help me think', 'guide me through', 'explore with me', 'let\'s discuss']):
                if hasattr(self, 'socratic_module') and self.socratic_module:
                    self.logger.info("Grok handling Socratic dialog request")
                    user_id = self._extract_user_id(context)
                    return self.socratic_module.forward(request, user_id=user_id, context=context)
            
            # If no keyword match, fall back to DSPy tool selection
            else:
                return self._execute_with_tools(request, context)
                
        except Exception as e:
            self.logger.error(f"Error in keyword-based routing: {e}", exc_info=True)
            # Fall back to DSPy tool selection
            return self._execute_with_tools(request, context)
    
    def _get_tool_by_name(self, tool_name: str):
        """Get a tool by its name from the available tools."""
        for tool in self.tools:
            if hasattr(tool, 'name') and tool.name == tool_name:
                return tool
        self.logger.warning(f"Tool '{tool_name}' not found in available tools")
        return None
    
    def _extract_location(self, request: str) -> Optional[str]:
        """Extract location from request."""
        request_lower = request.lower()
        
        # Common patterns for location extraction
        patterns = [' in ', ' at ', ' for ', ' near ']
        for pattern in patterns:
            if pattern in request_lower:
                parts = request_lower.split(pattern)
                if len(parts) > 1:
                    # Clean up the location
                    location = parts[1].strip()
                    # Remove trailing punctuation and common words
                    location = location.rstrip('?.,!').strip()
                    if location and location not in ['today', 'tomorrow', 'now', 'later']:
                        return location
        
        return None  # Will use default location
    
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
            available_tools = list(tool_map.keys())
            self.logger.info(f"Available tools for selection: {available_tools}")
            
            # Create a more explicit prompt for tool selection
            tool_selection_context = f"""
Available tools (ONLY select from this list):
{chr(10).join(f"- {tool}: {self._extract_tool_signature(tool_map[tool])}" for tool in available_tools[:10])}

Request: {request}
Context: {context_str}

IMPORTANT: You must select a tool name EXACTLY from the available tools list above.
Do NOT invent tool names like 'Wikipedia' or 'Google' - use the actual tool names provided.
"""
            
            # DSPy expects keyword arguments matching the signature
            decision = self.tool_selector(
                request=request, 
                available_tools=tool_selection_context,
                context=context_str
            )
            
            self.logger.info(f"Grok DSPy selected tool: {decision.tool_name}")
            
            # Map common hallucinated tools to real ones
            tool_name_mapping = {
                'wikipedia': 'web_search_tool',
                'Wikipedia': 'web_search_tool',
                'google': 'web_search_tool',
                'Google': 'web_search_tool',
                'search': 'web_search_tool',
                'weather': 'get_current_weather',
                'Weather': 'get_current_weather',
            }
            
            actual_tool_name = decision.tool_name
            if actual_tool_name not in tool_map and actual_tool_name in tool_name_mapping:
                mapped_name = tool_name_mapping[actual_tool_name]
                self.logger.warning(f"Mapping hallucinated tool '{actual_tool_name}' to '{mapped_name}'")
                actual_tool_name = mapped_name
            
            # Execute the selected tool
            if actual_tool_name in tool_map:
                tool = tool_map[actual_tool_name]
                args = self._parse_tool_args(decision.tool_args, actual_tool_name)
                result = tool(**args) if isinstance(args, dict) else tool(*args)
                return str(result)
            else:
                # DSPy selected an invalid tool - use fallback logic
                self.logger.warning(f"DSPy selected invalid tool '{decision.tool_name}', using fallback")
                
                # For general "what is" questions, use web search
                if request_lower.startswith(('what is', 'what are', 'define', 'explain')):
                    if 'web_search_tool' in tool_map:
                        query = request.replace('what is', '').replace('what are', '').strip()
                        result = tool_map['web_search_tool'](query=query)
                        return str(result)
                
                # For weather-related questions, use weather tools
                elif any(word in request_lower for word in ['weather', 'temperature', 'forecast', 'rain', 'snow']):
                    if 'get_current_weather' in tool_map:
                        # Extract location if present
                        location = None
                        if ' in ' in request_lower:
                            location = request.split(' in ', 1)[1].strip()
                        result = tool_map['get_current_weather'](location=location)
                        return str(result)
                
                return f"I couldn't find the right tool to answer your question. Let me try a web search instead.\n{tool_map.get('web_search_tool', lambda q: 'Web search not available')(query=request)}"
                
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
    
    def _parse_tool_args(self, args_str: str, tool_name: str = None) -> Dict[str, Any]:
        """Parse tool arguments from DSPy output."""
        args = {}
        if not args_str:
            return args
            
        # First check if it's key=value format
        if '=' in args_str:
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
        else:
            # If no key=value format, assume it's a single argument
            # Determine the appropriate key based on the tool name
            arg_value = args_str.strip().strip('"\'')
            
            # Choose the parameter name based on the tool
            if tool_name and ('weather' in tool_name or 'sunrise' in tool_name or 'sunset' in tool_name):
                args = {'location': arg_value}
            elif tool_name and 'slack' in tool_name:
                args = {'message': arg_value}
            else:
                # Default to 'query' for search tools
                args = {'query': arg_value}
        
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
            from dialog.socratic_tools import question_generator_tool, dialog_tracker_tool, insight_extractor_tool
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