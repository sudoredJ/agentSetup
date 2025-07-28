# AgentSetup - Multi-Agent Slack System

A sophisticated multi-agent system for Slack featuring intelligent task routing, specialized AI agents, and comprehensive tool integration.

## Features

- **Orchestrator Bot**: Intelligently coordinates task assignment between specialist agents
- **Specialist Agents**: 
  - **Writer**: Creative writing, drafting, and Socratic dialog capabilities
  - **Grok**: Deep research, web searches, arXiv papers, and weather information
- **DSPy Integration**: Enhanced reasoning with self-improving language programs
- **BeautifulSoup Search**: Multi-engine web search (Google, Bing, Wikipedia, DuckDuckGo) without rate limits
- **Rich Tool Ecosystem**: 
  - Search and research tools
  - Slack communication (DMs, channels, TTS)
  - External services (weather, Zoom meetings)
  - Socratic dialog system

## Quick Start

1. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your Slack tokens and API keys
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the system**:
   ```bash
   python -m src.main
   ```

## Architecture

The system uses a modular architecture with clear separation of concerns:

- **Orchestrator**: Receives requests and assigns them to the most suitable specialist
- **Specialists**: Execute assigned tasks using their configured tools
- **Tools**: Modular, reusable functions that agents can call
- **DSPy Modules**: Enhanced reasoning capabilities for complex tasks

See `docs/ARCHITECTURE.md` for detailed system design and `docs/ARCHITECTURE_COMPREHENSIVE.md` for complete technical documentation.

## Directory Structure

```
agentSetup/
├── src/                    # Source code
│   ├── core/              # Foundation classes and utilities
│   ├── agents/            # Agent implementations
│   ├── orchestrator/      # Coordination logic
│   ├── tools/             # LLM-callable tools organized by category
│   │   ├── search/        # Web search, arXiv, research tools
│   │   ├── communication/ # Slack messaging and TTS
│   │   ├── dialog/        # Socratic dialog tools
│   │   └── external/      # Weather, Zoom, etc.
│   └── integrations/      # External service clients
├── configs/               # YAML configuration files
├── docs/                  # Documentation
├── tests/                 # Test suite
└── requirements.txt       # Python dependencies
```

## Configuration

The system uses YAML configuration files in the `configs/` directory:

- `system_config.yaml`: System-wide settings and API keys
- `agents/*.yaml`: Individual agent profiles and tool configurations

Environment variables are loaded from `.env` and substituted into configurations using `${VAR_NAME}` syntax.

## Development

### Adding a New Agent

1. Create a YAML profile in `configs/agents/`
2. Add bot tokens to `.env` and `system_config.yaml`
3. The agent will be automatically discovered on startup

### Adding New Tools

1. Create a `@tool` decorated function in the appropriate `src/tools/` subdirectory
2. Add to the agent's profile tool list
3. The tool is immediately available to the agent

### Testing

Run tests with:
```bash
python -m pytest tests/
```

## Documentation

- `docs/ARCHITECTURE.md` - System architecture overview
- `docs/IMPLEMENTATION_PLAN.md` - Feature implementation roadmap
- `docs/DSPY_INTEGRATION.md` - DSPy integration guide
- `docs/SOCRATIC_DIALOG_GUIDE.md` - Socratic dialog implementation
- `docs/ENV_SETUP.md` - Environment setup instructions

## License

[Add your license here]

## Contributing

[Add contributing guidelines here]