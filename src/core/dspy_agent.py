"""DSPy-powered agent that integrates with BeautifulSoup search system."""

import dspy
import os
import logging
import sys
from typing import List, Dict, Any, Optional
from dspy.teleprompt import BootstrapFewShot

class DSPyToolSignature(dspy.Signature):
    """Signature for tool execution decisions."""
    request: str = dspy.InputField(desc="The user's request")
    context: str = dspy.InputField(desc="Conversation context")
    available_tools: str = dspy.InputField(desc="List of available tool signatures")
    
    reasoning: str = dspy.OutputField(desc="Step-by-step reasoning about which tool to use")
    tool_name: str = dspy.OutputField(desc="Name of the tool to execute")
    tool_args: str = dspy.OutputField(desc="Arguments for the tool as key=value pairs")

class DSPyAgent(dspy.Module):
    """DSPy-powered agent that replaces FriendlyCodeAgent and uses BeautifulSoup search."""
    
    def __init__(self, tools: List[Any], model_id: str, system_prompt: str):
        super().__init__()
        self.tools = tools
        self.system_prompt = system_prompt  # Store the system prompt
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize DSPy with the model using litellm
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
                api_key = os.environ.get("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY environment variable not set")
                self.lm = DSPyLiteLLMWrapper(
                    model_id=model_id,
                    api_base="https://api.anthropic.com/v1",
                    api_key=api_key
                )
            else:
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY environment variable not set")
                self.lm = DSPyLiteLLMWrapper(
                    model_id=model_id,
                    api_key=api_key
                )
            
            # Configure DSPy to use our LM
            dspy.settings.configure(lm=self.lm)
            self.logger.info(f"DSPy LM initialized with model: {model_id}")
            
            # Test the configuration
            try:
                test_response = self.lm("test")
                self.logger.info(f"DSPy LM test successful")
            except Exception as test_e:
                self.logger.error(f"DSPy LM test failed: {test_e}")
                raise
            
        except Exception as e:
            self.logger.error(f"Failed to initialize DSPy LM: {e}")
            # Create a mock LM for testing when real LM is not available
            self.lm = self._create_mock_lm()
            self.logger.warning("Using mock LM for testing - DSPy features will be limited")
            
            # Still try to configure DSPy with mock LM
            try:
                dspy.settings.configure(lm=self.lm)
                self.logger.info("DSPy configured with mock LM")
            except Exception as config_e:
                self.logger.error(f"Failed to configure DSPy with mock LM: {config_e}")
        
        # Initialize components
        self._init_tool_selector()
        self._init_beautiful_search()
        self._init_system_prompt()
    
    def _create_mock_lm(self):
        """Create a mock LM for testing when real LM is not available."""
        class MockLM:
            def __init__(self):
                self.logger = logging.getLogger(self.__class__.__name__)
            
            def __call__(self, prompt, **kwargs):
                # Simple mock response for testing
                if "tool" in prompt.lower():
                    return "tool_name: web_search_tool, tool_args: query=test"
                else:
                    return "Mock response: This is a test response from the mock LM."
            
            # DSPy compatibility methods
            def basic_request(self, prompt, **kwargs):
                return self.__call__(prompt, **kwargs)
            
            def __repr__(self):
                return "MockLM()"
        
        return MockLM()
    
    
    
    def _init_tool_selector(self):
        """Initialize the tool selector."""
        try:
            self.tool_selector = dspy.ChainOfThought(DSPyToolSignature)
        except Exception as e:
            self.logger.error(f"Failed to create tool selector: {e}")
            # Create a mock tool selector for testing
            self.tool_selector = self._create_mock_tool_selector()
            self.logger.warning("Using mock tool selector for testing")
    
    def _create_mock_tool_selector(self):
        """Create a mock tool selector for testing."""
        class MockToolSelector:
            def __init__(self):
                self.logger = logging.getLogger(self.__class__.__name__)
            
            def __call__(self, request, context, available_tools):
                # Return mock structured output
                return type('MockDecision', (), {
                    'reasoning': 'Mock reasoning about tool selection',
                    'tool_name': 'web_search_tool',
                    'tool_args': 'query=test'
                })()
        
        return MockToolSelector()
    
    def _init_beautiful_search(self):
        """Initialize BeautifulSoup search system."""
        try:
            import sys
            import os
            # Add the tools directory to the path
            tools_path = os.path.join(os.path.dirname(__file__), '..', 'tools')
            if tools_path not in sys.path:
                sys.path.insert(0, tools_path)
            from beautiful_search import beautiful_search
            self.beautiful_search = beautiful_search
            self.logger.info("DSPy agent initialized with BeautifulSoup search system")
        except ImportError as e:
            self.logger.error(f"Failed to import BeautifulSoup search: {e}")
            self.beautiful_search = None
    
    def _init_system_prompt(self):
        """Initialize system prompt."""
        # System prompt is already stored in __init__
        pass
        
    def forward(self, request: str, context: List[Dict] = None) -> str:
        """Execute the request using DSPy reasoning with BeautifulSoup search."""
        # Format available tools
        tool_descriptions = []
        tool_map = {}
        
        for tool in self.tools:
            if hasattr(tool, 'name'):
                tool_map[tool.name] = tool
                # Get tool signature from docstring or metadata
                sig = self._extract_tool_signature(tool)
                tool_descriptions.append(sig)
        
        tools_str = "\n".join(tool_descriptions)
        context_str = self._format_context(context) if context else "No previous context"
        
        # Use DSPy to select and execute tool
        try:
            decision = self.tool_selector(
                request=request,
                context=context_str,
                available_tools=tools_str
            )
            
            self.logger.info(f"DSPy reasoning: {decision.reasoning}")
            self.logger.info(f"Selected tool: {decision.tool_name}")
            
            # Execute the selected tool
            if decision.tool_name in tool_map:
                tool = tool_map[decision.tool_name]
                args = self._parse_tool_args(decision.tool_args)
                result = tool(**args) if isinstance(args, dict) else tool(*args)
                return str(result)
            else:
                return f"Tool '{decision.tool_name}' not found. Available: {list(tool_map.keys())}"
                
        except Exception as e:
            self.logger.error(f"DSPy execution error: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    def _extract_tool_signature(self, tool) -> str:
        """Extract tool signature for DSPy context."""
        if hasattr(tool, '__doc__') and tool.__doc__:
            # Parse docstring to get signature
            lines = tool.__doc__.strip().split('\n')
            desc = lines[0] if lines else ""
            
            # Try to extract args from docstring
            args_section = False
            args = []
            for line in lines:
                if "Args:" in line:
                    args_section = True
                    continue
                if args_section and line.strip() and not line.startswith(' '):
                    break
                if args_section and ':' in line:
                    arg_name = line.strip().split(':')[0].strip()
                    args.append(arg_name)
            
            args_str = ", ".join(args) if args else "..."
            return f"{tool.name}({args_str}): {desc}"
        else:
            return f"{tool.name}(...): No description available"
    
    def _format_context(self, context: List[Dict]) -> str:
        """Format conversation context for DSPy."""
        if not context:
            return ""
        
        formatted = []
        for msg in context[-10:]:  # Last 10 messages
            if msg.get("text") and not msg.get("bot_id"):
                formatted.append(f"User: {msg['text']}")
        
        return "\n".join(formatted)
    
    def _parse_tool_args(self, args_str: str) -> Dict[str, Any]:
        """Parse tool arguments from DSPy output."""
        args = {}
        if not args_str:
            return args
            
        # Parse key=value pairs
        pairs = args_str.split(',')
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                
                # Try to convert to appropriate type
                try:
                    if value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
                    elif value.isdigit():
                        value = int(value)
                    elif '.' in value and value.replace('.', '').isdigit():
                        value = float(value)
                except:
                    pass  # Keep as string
                
                args[key] = value
        
        return args

    def optimize_with_examples(self, examples: List[Dict]):
        """Optimize the DSPy module with examples."""
        # Convert examples to DSPy format
        trainset = []
        for ex in examples:
            trainset.append(dspy.Example(
                request=ex['request'],
                context=ex.get('context', ''),
                available_tools=ex['available_tools'],
                tool_name=ex['expected_tool'],
                tool_args=ex['expected_args']
            ))
        
        # Use BootstrapFewShot to optimize
        optimizer = BootstrapFewShot(metric=self._metric, max_bootstrapped_demos=3)
        optimized = optimizer.compile(self, trainset=trainset)
        
        # Update our module
        self.tool_selector = optimized.tool_selector
        
    def _metric(self, example, prediction, trace=None):
        """Metric for optimization - checks if correct tool was selected."""
        return prediction.tool_name == example.tool_name

    def run(self, prompt: str, *args, **kwargs) -> str:
        """Compatibility method to match FriendlyCodeAgent interface."""
        # Extract the actual request from the prompt
        # This handles the case where the prompt contains the request
        request = self._extract_request_from_prompt(prompt)
        return self.forward(request)
    
    def _extract_request_from_prompt(self, prompt: str) -> str:
        """Extract the actual request from a formatted prompt."""
        # Look for common patterns in the prompt
        lines = prompt.split('\n')
        for line in lines:
            if "User's request:" in line:
                return line.split("User's request:")[1].strip()
            elif "request:" in line.lower():
                return line.split("request:")[1].strip()
        
        # If no pattern found, return the last non-empty line
        for line in reversed(lines):
            if line.strip() and not line.startswith(('You are', 'Available tools', 'When you are ready')):
                return line.strip()
        
        return prompt.strip() 