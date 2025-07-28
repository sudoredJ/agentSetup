# DSPy Integration Guide for Multi-Agent Slack System

## Overview

DSPy (Declarative Self-improving Language Programs) can significantly enhance the current multi-agent system by providing:
- Automatic prompt optimization
- Structured reasoning chains
- Self-improving agent behaviors
- Declarative tool definitions

This guide explains how to integrate DSPy into the existing codebase while maintaining full compatibility with the current Slack integration.

## Table of Contents
1. [Why DSPy?](#why-dspy)
2. [Installation](#installation)
3. [Converting FriendlyCodeAgent to DSPy](#converting-friendlycodeagent-to-dspy)
4. [Tool Conversion](#tool-conversion)
5. [Specialist Agent Enhancement](#specialist-agent-enhancement)
6. [Optimization Strategies](#optimization-strategies)
7. [Maintaining Slack Compatibility](#maintaining-slack-compatibility)
8. [Implementation Roadmap](#implementation-roadmap)

## Why DSPy?

DSPy offers several advantages over the current implementation:

1. **Automatic Prompt Engineering**: Instead of manually crafting prompts, DSPy learns optimal prompts through examples
2. **Modular Reasoning**: Chain-of-Thought, ReAct, and other reasoning patterns as reusable modules
3. **Type Safety**: Structured inputs/outputs with validation
4. **Performance Tracking**: Built-in metrics and optimization loops

## Installation

Add DSPy to your requirements:

```bash
pip install dspy-ai
```

## Converting FriendlyCodeAgent to DSPy

### Current Implementation
The current `FriendlyCodeAgent` wraps smolagents with fallback parsing. We can replace this with a DSPy module that provides better reliability.

### DSPy Implementation

Create `src/core/dspy_agent.py`:

```python
import dspy
from typing import List, Dict, Any, Optional
import logging
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
    """DSPy-powered agent that replaces FriendlyCodeAgent."""
    
    def __init__(self, tools: List[Any], model_id: str, system_prompt: str):
        super().__init__()
        self.tools = tools
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize DSPy with the model
        self.lm = dspy.OpenAI(
            model=model_id,
            api_base="https://api.anthropic.com/v1" if "claude" in model_id else None,
            api_key=os.environ.get("ANTHROPIC_API_KEY" if "claude" in model_id else "OPENAI_API_KEY")
        )
        dspy.settings.configure(lm=self.lm)
        
        # Create reasoning chain
        self.tool_selector = dspy.ChainOfThought(DSPyToolSignature)
        
        # Store system prompt for context
        self.system_prompt = system_prompt
        
    def forward(self, request: str, context: List[Dict] = None) -> str:
        """Execute the request using DSPy reasoning."""
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
```

## Tool Conversion

Convert existing tools to be DSPy-compatible while maintaining backward compatibility:

### Enhanced Tool Wrapper

Create `src/tools/dspy_tools.py`:

```python
import dspy
from typing import Any, Callable
from smolagents import tool

class DSPyTool(dspy.Module):
    """Wrapper to make tools DSPy-compatible while maintaining smolagents compatibility."""
    
    def __init__(self, original_tool: Callable, signature: dspy.Signature = None):
        super().__init__()
        self.original_tool = original_tool
        self.name = original_tool.name if hasattr(original_tool, 'name') else original_tool.__name__
        
        # Create signature if not provided
        if signature is None:
            signature = self._create_signature_from_tool()
        
        self.predictor = dspy.Predict(signature)
        
    def _create_signature_from_tool(self):
        """Create a DSPy signature from tool metadata."""
        # Extract from docstring or annotations
        import inspect
        
        class ToolSignature(dspy.Signature):
            pass
        
        # Add input fields based on function signature
        sig = inspect.signature(self.original_tool)
        for param_name, param in sig.parameters.items():
            if param_name != 'self':
                # Add as InputField
                setattr(ToolSignature, param_name, 
                       dspy.InputField(desc=f"Parameter {param_name}"))
        
        # Add output field
        setattr(ToolSignature, 'result', 
               dspy.OutputField(desc="Tool execution result"))
        
        return ToolSignature
    
    def forward(self, **kwargs):
        """Execute tool with DSPy tracing."""
        # Execute original tool
        result = self.original_tool(**kwargs)
        
        # Return with DSPy tracing
        return dspy.Prediction(result=result)

def convert_tools_to_dspy(tools: List[Any]) -> List[DSPyTool]:
    """Convert existing tools to DSPy-compatible versions."""
    dspy_tools = []
    
    for tool in tools:
        if isinstance(tool, DSPyTool):
            dspy_tools.append(tool)
        else:
            dspy_tools.append(DSPyTool(tool))
    
    return dspy_tools
```

## Specialist Agent Enhancement

Update `SpecialistAgent` to support both modes:

```python
# In src/agents/specialist_agent.py, add:

def __init__(self, agent_profile: dict, slack_token: str, coordination_channel: str, use_dspy: bool = False):
    # ... existing init code ...
    
    self.use_dspy = use_dspy or agent_profile.get('use_dspy', False)
    
    if self.use_dspy:
        from src.core.dspy_agent import DSPyAgent
        self.ai_agent = DSPyAgent(
            tools=initialized_tools,
            model_id=self.agent_profile['model_id'],
            system_prompt=self.agent_profile['system_prompt']
        )
    else:
        # Existing FriendlyCodeAgent initialization
        self.ai_agent = FriendlyCodeAgent(
            tools=initialized_tools,
            model=LiteLLMModel(
                model_id=self.agent_profile['model_id'],
                system=self.agent_profile['system_prompt']
            ),
            max_steps=3
        )

def process_assignment(self, request_text: str, original_user: str, thread_ts: str, context: list[dict] | None = None):
    # ... existing code ...
    
    if self.use_dspy:
        # DSPy execution
        result = self.ai_agent.forward(request_text, context)
    else:
        # Existing execution with thinking_prompt
        result = self.ai_agent.run(thinking_prompt)
    
    # ... rest of processing ...
```

## Optimization Strategies

### 1. Collect Training Data

Create a data collection mechanism:

```python
# In src/core/training_collector.py

import json
import os
from datetime import datetime

class TrainingDataCollector:
    """Collect successful agent interactions for DSPy optimization."""
    
    def __init__(self, data_dir: str = "training_data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def record_interaction(self, agent_name: str, request: str, 
                          context: List[Dict], tool_used: str, 
                          tool_args: Dict, success: bool):
        """Record an interaction for later training."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "request": request,
            "context": context,
            "tool_used": tool_used,
            "tool_args": tool_args,
            "success": success
        }
        
        filename = f"{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
```

### 2. Periodic Optimization

Add optimization command to CLI:

```python
# In src/cli.py, add:

@click.command()
@click.option('--agent', help='Agent name to optimize')
def optimize(agent):
    """Optimize DSPy agents with collected training data."""
    from src.core.dspy_optimizer import optimize_agent
    
    if agent:
        optimize_agent(agent)
    else:
        # Optimize all agents
        for agent_file in os.listdir('configs/agents'):
            if agent_file.endswith('.yaml'):
                agent_name = agent_file.replace('_agent.yaml', '')
                optimize_agent(agent_name)
```

### 3. DSPy Modules for Specialist Behaviors

Create specialized DSPy modules for each agent type:

```python
# In src/agents/dspy_modules.py

class ResearchModule(dspy.Module):
    """DSPy module for research-focused agents."""
    
    def __init__(self):
        super().__init__()
        self.generate_queries = dspy.ChainOfThought("topic -> query1, query2, query3")
        self.synthesize = dspy.ChainOfThought("results -> summary")
    
    def forward(self, topic: str) -> str:
        # Generate multiple search queries
        queries = self.generate_queries(topic=topic)
        
        # Execute searches (integrate with existing tools)
        results = []
        for query in [queries.query1, queries.query2, queries.query3]:
            # Use existing search tools
            result = web_search_tool(query)
            results.append(result)
        
        # Synthesize results
        summary = self.synthesize(results="\n".join(results))
        return summary.summary

class WriterModule(dspy.Module):
    """DSPy module for writing-focused agents."""
    
    def __init__(self):
        super().__init__()
        self.planner = dspy.ChainOfThought("request -> outline")
        self.writer = dspy.ChainOfThought("outline, style -> content")
        self.editor = dspy.ChainOfThought("content -> edited_content")
    
    def forward(self, request: str, style: str = "professional") -> str:
        # Plan the writing
        outline = self.planner(request=request)
        
        # Write content
        content = self.writer(outline=outline.outline, style=style)
        
        # Edit and refine
        edited = self.editor(content=content.content)
        
        return edited.edited_content
```

## Maintaining Slack Compatibility

The DSPy integration maintains full compatibility with the existing Slack integration:

1. **Gradual Migration**: Use the `use_dspy` flag in agent profiles to migrate agents one at a time
2. **Backward Compatible**: All existing tools continue to work
3. **Same Interface**: The `process_assignment` method remains unchanged
4. **Preserved Features**: All Slack-specific features (DMs, threads, reactions) work identically

### Configuration Example

Update agent YAML to enable DSPy:

```yaml
# configs/agents/grok_agent.yaml
name: "Grok"
model_id: "claude-3-haiku-20240307"
use_dspy: true  # Enable DSPy for this agent
system_prompt: |
  You are Grok, a research specialist...
tools:
  - module: "src.tools.agent_tools"
    functions: ["deep_research_tool", "web_search_tool", "fetch_and_summarize_tool"]
```

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
1. Install DSPy and dependencies
2. Implement `DSPyAgent` class
3. Create tool conversion utilities
4. Test with one agent (e.g., Grok)

### Phase 2: Integration (Week 2)
1. Add training data collection
2. Update `SpecialistAgent` to support both modes
3. Create agent-specific DSPy modules
4. Implement gradual rollout mechanism

### Phase 3: Optimization (Week 3)
1. Collect interaction data
2. Implement optimization pipeline
3. Create evaluation metrics
4. Add CLI commands for optimization

### Phase 4: Advanced Features (Week 4)
1. Implement multi-step reasoning chains
2. Add cross-agent learning
3. Create performance dashboards
4. Document best practices

## Example: Converting Grok to DSPy

Here's a complete example of converting the Grok agent:

```python
# src/agents/grok_dspy.py

from src.agents.dspy_modules import ResearchModule
from src.core.dspy_agent import DSPyAgent

class GrokDSPyAgent(DSPyAgent):
    """Enhanced Grok agent using DSPy."""
    
    def __init__(self, tools, model_id, system_prompt):
        super().__init__(tools, model_id, system_prompt)
        
        # Add specialized research module
        self.research_module = ResearchModule()
        
    def forward(self, request: str, context: List[Dict] = None) -> str:
        """Enhanced execution with research capabilities."""
        request_lower = request.lower()
        
        # Check if this is a research request
        if any(word in request_lower for word in ['research', 'investigate', 'deep dive']):
            # Extract topic
            topic = self._extract_topic(request)
            
            # Use DSPy research module
            result = self.research_module(topic=topic)
            return result
        else:
            # Fall back to standard DSPy execution
            return super().forward(request, context)
    
    def _extract_topic(self, request: str) -> str:
        """Extract research topic from request."""
        # Use existing logic from specialist_agent.py
        request_lower = request.lower()
        for prefix in ['research on', 'investigate', 'deep dive on']:
            if prefix in request_lower:
                return request_lower.split(prefix)[-1].strip()
        return request
```

## Benefits of DSPy Integration

1. **Self-Improving**: Agents get better over time through optimization
2. **Declarative**: Define what agents should do, not how
3. **Interpretable**: Clear reasoning chains for debugging
4. **Modular**: Reusable components across agents
5. **Type-Safe**: Structured inputs/outputs reduce errors
6. **Performance**: Optimized prompts improve accuracy and reduce costs

## Conclusion

DSPy integration enhances the multi-agent system while maintaining full backward compatibility. The modular approach allows gradual migration and testing, ensuring system stability while gaining the benefits of declarative, self-improving language programs.

The integration points are designed to work seamlessly with the existing Slack infrastructure, requiring minimal changes to the core orchestration logic while providing significant improvements in agent reliability and performance.