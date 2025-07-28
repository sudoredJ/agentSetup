"""Enhanced FriendlyCodeAgent that properly integrates with smolagents.

This implementation extends the original stub to provide proper tool execution
and result handling for the specialist agents.
"""

from __future__ import annotations

from typing import Any, Callable, List
import re
import logging

try:
    from smolagents import CodeAgent
    SMOLAGENTS_AVAILABLE = True
except ImportError:
    SMOLAGENTS_AVAILABLE = False


class FriendlyCodeAgent:
    """A wrapper around smolagents CodeAgent that handles tool execution gracefully."""
    
    def __init__(self, tools: List[Callable] | None = None, model: Any | None = None, max_steps: int = 3):
        self.tools = tools or []
        self.model = model
        self.max_steps = max_steps
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # If smolagents is available, use the real CodeAgent
        if SMOLAGENTS_AVAILABLE and model is not None:
            try:
                from smolagents import CodeAgent
                self.agent = CodeAgent(
                    tools=self.tools,
                    model=self.model,
                    max_steps=self.max_steps
                )
                self.logger.info("Using smolagents CodeAgent")
            except Exception as e:
                self.logger.warning(f"Failed to initialize CodeAgent: {e}")
                self.agent = None
        else:
            self.agent = None
            self.logger.info("Using fallback implementation")

    def run(self, prompt: str, *args, **kwargs):
        """Execute the prompt and return results."""
        if self.agent is not None:
            try:
                # Use the real smolagents agent
                return self.agent.run(prompt, *args, **kwargs)
            except Exception as e:
                self.logger.error(f"CodeAgent execution failed: {e}", exc_info=True)
                # Fall through to manual execution
        
        # Fallback: Try to parse and execute tool calls manually
        try:
            # First try to get a response from the model
            if self.model is None:
                raise RuntimeError("FriendlyCodeAgent was created without a model.")
            
            response = None
            if callable(getattr(self.model, "run", None)):
                response = self.model.run(prompt, *args, **kwargs)
            elif callable(self.model):
                response = self.model(prompt, *args, **kwargs)
            else:
                raise TypeError("Model provided to FriendlyCodeAgent is not callable.")
            
            # If response is a string, try to extract and execute tool calls
            if isinstance(response, str):
                self.logger.debug(f"Model response: {response[:500]}...")
                
                # Look for tool calls in the response
                tool_results = self._execute_tool_calls(response)
                if tool_results:
                    return tool_results
                else:
                    return response
            else:
                return str(response)
                
        except Exception as exc:
            self.logger.error(f"FriendlyCodeAgent execution error: {exc}", exc_info=True)
            return f"ModelError: {str(exc)}"
    
    def _execute_tool_calls(self, response: str) -> str | None:
        """Extract and execute tool calls from the model response."""
        # Look for function calls in various formats
        patterns = [
            r'(\w+)\((.*?)\)',  # function_name(args)
            r'`(\w+)\((.*?)\)`',  # `function_name(args)`
            r'```\n?(\w+)\((.*?)\)\n?```',  # code block
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                tool_name = match[0]
                args_str = match[1] if len(match) > 1 else ""
                
                # Find the tool
                tool = None
                for t in self.tools:
                    if hasattr(t, 'name') and t.name == tool_name:
                        tool = t
                        break
                
                if tool:
                    try:
                        # Parse arguments
                        args = self._parse_args(args_str)
                        self.logger.info(f"Executing tool: {tool_name} with args: {args}")
                        
                        # Execute the tool
                        if callable(tool):
                            result = tool(**args) if isinstance(args, dict) else tool(*args)
                        else:
                            result = tool
                        
                        return str(result)
                    except Exception as e:
                        self.logger.error(f"Tool execution failed: {e}", exc_info=True)
                        return f"Tool execution error: {str(e)}"
        
        return None
    
    def _parse_args(self, args_str: str) -> dict | list:
        """Parse function arguments from a string."""
        args_str = args_str.strip()
        if not args_str:
            return {}
        
        # Try to parse as Python literals
        try:
            # Handle quoted strings and basic types
            import ast
            # Wrap in parentheses to make it a tuple
            parsed = ast.literal_eval(f"({args_str},)")
            if len(parsed) == 1 and isinstance(parsed[0], dict):
                return parsed[0]
            return list(parsed)
        except:
            # Fallback: parse key=value pairs
            args = {}
            # Match key="value" or key=value patterns
            pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\s]+))'
            matches = re.findall(pattern, args_str)
            for match in matches:
                key = match[0]
                value = match[1] or match[2] or match[3]
                args[key] = value
            
            if args:
                return args
            
            # If no key-value pairs, treat as positional arguments
            parts = [p.strip().strip('"\'') for p in args_str.split(',')]
            return parts if len(parts) > 1 else parts[0] if parts else {} 