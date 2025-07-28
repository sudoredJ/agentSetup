# DSPy Integration with BeautifulSoup Search - Complete Guide

## 🎉 Overview

The system now supports **DSPy (Declarative Self-improving Language Programs)** integrated with our **BeautifulSoup search system**. This provides:

- **Enhanced Reasoning**: Chain-of-Thought reasoning for better decision making
- **BeautifulSoup Search**: No rate limits, multiple search engines
- **Self-Improving**: Agents can optimize their behavior over time
- **Backward Compatible**: Existing agents continue to work

## 🚀 What's New

### 1. **DSPy Agent System**
- `src/core/dspy_agent.py`: Base DSPy agent implementation
- `src/agents/dspy_modules.py`: Specialized modules for different agent types
- Integration with existing `SpecialistAgent` class

### 2. **BeautifulSoup Integration**
- All DSPy modules use BeautifulSoup search instead of DuckDuckGo
- Multiple search engines: Google, Bing, Wikipedia, DuckDuckGo
- No rate limiting issues
- Automatic fallback between engines

### 3. **Enhanced Grok Agent**
- Specialized `GrokDSPyAgent` for research tasks
- Automatic research query generation
- Multi-source synthesis
- BeautifulSoup-powered search

## 📦 Installation

### 1. **Install DSPy**
```bash
pip install dspy-ai==2.4.8
```

### 2. **Verify Dependencies**
All required packages are already in `requirements.txt`:
- `dspy-ai==2.4.8`
- `requests==2.32.4`
- `beautifulsoup4==4.12.3`
- `lxml==5.4.0`

## 🧪 Testing

### Quick Test
```bash
python test_dspy_integration.py
```

### Individual Tests
```bash
# Test BeautifulSoup search
python test_beautiful_search.py

# Test DSPy integration
python test_dspy_integration.py
```

## ⚙️ Configuration

### Enable DSPy for an Agent

Edit the agent's YAML configuration:

```yaml
# configs/agents/grok_agent.yaml
name: "Grok"
model_id: "claude-3-haiku-20240307"
use_dspy: true  # Enable DSPy for this agent
system_prompt: |
  You are Grok, a research specialist...
```

### Available DSPy Modules

1. **ResearchModule**: Multi-query research with synthesis
2. **WriterModule**: Structured writing with planning and editing
3. **AnalysisModule**: Data gathering and analysis
4. **GrokDSPyAgent**: Specialized research agent

## 🔧 Usage Examples

### 1. **Basic DSPy Agent**
```python
from src.core.dspy_agent import DSPyAgent

# Initialize DSPy agent
agent = DSPyAgent(
    tools=[your_tools],
    model_id="claude-3-haiku-20240307",
    system_prompt="You are a helpful assistant."
)

# Execute request
result = agent.forward("Research artificial intelligence")
```

### 2. **Research Module**
```python
from src.agents.dspy_modules import ResearchModule

# Initialize research module
research = ResearchModule()

# Execute research (uses BeautifulSoup search)
result = research.forward("python programming")
```

### 3. **Grok DSPy Agent**
```python
from src.agents.dspy_modules import GrokDSPyAgent

# Initialize Grok DSPy agent
grok = GrokDSPyAgent(
    tools=[web_search_tool, deep_research_tool],
    model_id="claude-3-haiku-20240307",
    system_prompt="You are Grok, a research specialist."
)

# Research request (uses BeautifulSoup)
result = grok.forward("Research machine learning")

# Regular request (uses tools)
result2 = grok.forward("Hello, how are you?")
```

### 4. **SpecialistAgent with DSPy**
```python
# The SpecialistAgent automatically uses DSPy when configured
agent_profile = {
    'name': 'Grok',
    'model_id': 'claude-3-haiku-20240307',
    'use_dspy': True,  # Enable DSPy
    'system_prompt': 'You are a research specialist...'
}

# DSPy agent is automatically initialized
specialist = SpecialistAgent(agent_profile, slack_token, coordination_channel)
```

## 🧠 DSPy Features

### 1. **Chain-of-Thought Reasoning**
```python
# DSPy automatically generates reasoning chains
decision = self.tool_selector(
    request="Research AI",
    context="Previous conversation...",
    available_tools="web_search_tool, deep_research_tool"
)

# Output includes reasoning
print(decision.reasoning)  # "The user wants research on AI..."
print(decision.tool_name)  # "deep_research_tool"
```

### 2. **Automatic Optimization**
```python
# DSPy can optimize with examples
examples = [
    {
        'request': 'Research AI',
        'expected_tool': 'deep_research_tool',
        'expected_args': 'topic=AI, num_searches=3'
    }
]

agent.optimize_with_examples(examples)
```

### 3. **Structured Outputs**
```python
# DSPy provides structured, validated outputs
class ToolSignature(dspy.Signature):
    request: str = dspy.InputField(desc="User request")
    tool_name: str = dspy.OutputField(desc="Selected tool")
    tool_args: str = dspy.OutputField(desc="Tool arguments")
```

## 🌐 BeautifulSoup Integration

### 1. **Multiple Search Engines**
- **Google**: Primary search engine
- **Bing**: Secondary search engine
- **Wikipedia**: Direct API + scraping
- **DuckDuckGo**: HTML scraping (fallback)

### 2. **Automatic Fallbacks**
```python
# If one engine fails, others continue
results = beautiful_search.search_with_fallbacks("query", 5)
# Returns results from multiple engines
```

### 3. **No Rate Limits**
- Direct HTML scraping
- No API cooldowns
- Continuous searching capability

## 🔄 Migration Guide

### From FriendlyCodeAgent to DSPy

1. **Enable DSPy in Agent Config**
```yaml
use_dspy: true
```

2. **No Code Changes Required**
- All existing interfaces work
- Same tool definitions
- Same Slack integration

3. **Enhanced Capabilities**
- Better reasoning
- Self-improvement
- BeautifulSoup search

### Backward Compatibility

- **Existing agents**: Continue to work unchanged
- **Existing tools**: All tools work with DSPy
- **Existing configurations**: Add `use_dspy: true` to enable

## 📊 Performance Comparison

| Feature | FriendlyCodeAgent | DSPy Agent |
|---------|------------------|------------|
| **Search Engine** | DuckDuckGo API | BeautifulSoup (Multiple) |
| **Rate Limits** | Yes (API limits) | No (HTML scraping) |
| **Reasoning** | Basic prompt parsing | Chain-of-Thought |
| **Self-Improvement** | No | Yes (optimization) |
| **Search Reliability** | Medium (API dependent) | High (multiple engines) |
| **Speed** | Fast (API calls) | Medium (HTML parsing) |

## 🛠️ Advanced Features

### 1. **Custom DSPy Modules**
```python
class CustomModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought("input -> output")
    
    def forward(self, input_text: str) -> str:
        result = self.predictor(input=input_text)
        return result.output
```

### 2. **Training Data Collection**
```python
# DSPy can learn from examples
training_data = [
    {
        'request': 'Research topic X',
        'context': 'Previous conversation...',
        'expected_tool': 'deep_research_tool',
        'expected_args': 'topic=X, num_searches=3'
    }
]

agent.optimize_with_examples(training_data)
```

### 3. **Multi-Step Reasoning**
```python
# DSPy supports complex reasoning chains
class MultiStepModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.step1 = dspy.ChainOfThought("input -> intermediate")
        self.step2 = dspy.ChainOfThought("intermediate -> output")
    
    def forward(self, input_text: str) -> str:
        intermediate = self.step1(input=input_text)
        output = self.step2(intermediate=intermediate.intermediate)
        return output.output
```

## 🔧 Troubleshooting

### Common Issues

1. **DSPy Import Error**
   ```bash
   pip install dspy-ai==2.4.8
   ```

2. **BeautifulSoup Search Fails**
   - Check internet connectivity
   - Verify search engines are accessible
   - Check logs for specific errors

3. **Agent Not Using DSPy**
   - Ensure `use_dspy: true` in agent config
   - Check agent initialization logs
   - Verify DSPy agent is being created

### Debugging

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🎯 Benefits

### 1. **Enhanced Reasoning**
- Chain-of-Thought reasoning
- Better decision making
- Structured outputs

### 2. **Reliable Search**
- No rate limits
- Multiple search engines
- Automatic fallbacks

### 3. **Self-Improvement**
- Learning from examples
- Optimization over time
- Better performance

### 4. **Future-Proof**
- Easy to add new modules
- Extensible architecture
- Modern AI techniques

## 🚀 Next Steps

1. **Test the Integration**
   ```bash
   python test_dspy_integration.py
   ```

2. **Enable DSPy for Agents**
   - Add `use_dspy: true` to agent configs
   - Test with one agent first

3. **Collect Training Data**
   - Monitor agent interactions
   - Gather optimization examples

4. **Optimize Performance**
   - Run optimization cycles
   - Monitor improvements

## 📚 Documentation

- **`DSPY_INTEGRATION.md`**: Original integration guide
- **`BEAUTIFULSOUP_MIGRATION.md`**: BeautifulSoup migration details
- **`SEARCH_IMPROVEMENTS.md`**: Search system improvements
- **`ARCHITECTURE.md`**: System architecture overview

## 🎉 Conclusion

The DSPy integration with BeautifulSoup search provides a powerful, reliable, and self-improving agent system that eliminates rate limiting issues while providing enhanced reasoning capabilities. The system is fully backward compatible and ready for production use.