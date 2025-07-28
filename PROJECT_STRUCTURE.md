# Project Structure

## Overview
This is a multi-agent Slack system with DSPy integration for collaborative task handling.

## Directory Structure

```
agentSetup/
├── configs/                    # Configuration files
│   ├── agents/                # Agent profiles
│   │   ├── grok_agent.yaml    # Grok specialist configuration
│   │   └── writer_agent.yaml  # Writer specialist configuration
│   └── system_config.yaml     # System-wide configuration
│
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # Current system architecture
│   ├── ARCHITECTURE_COMPREHENSIVE.md  # Detailed architecture guide
│   ├── BEAUTIFULSOUP_MIGRATION.md    # BeautifulSoup search migration
│   ├── DSPY_BEAUTIFULSOUP_INTEGRATION.md  # DSPy integration details
│   ├── DSPY_INTEGRATION.md   # Original DSPy integration plan
│   ├── DSPY_INTEGRATION_SUMMARY.md    # DSPy implementation summary
│   ├── ENV_SETUP.md           # Environment variables guide
│   ├── IMPLEMENTATION_PLAN.md # Overall implementation tracking
│   ├── QUICKSTART_BEAUTIFULSOUP.md    # Quick start guide
│   ├── SEARCH_IMPROVEMENTS.md # Search system improvements
│   ├── SOCRATIC_DIALOG_GUIDE.md       # Socratic dialog implementation
│   ├── zoom_integration_plan.md       # Zoom integration plan
│   └── deprecated/            # Completed/obsolete plans
│       └── GROK_ENHANCEMENT_PLAN.md
│
├── src/                       # Source code
│   ├── agents/                # Agent implementations
│   │   ├── __init__.py
│   │   ├── dspy_modules.py    # DSPy modules and signatures
│   │   ├── negotiation_module.py  # Collaborative evaluation
│   │   └── specialist_agent.py    # Base specialist agent
│   │
│   ├── core/                  # Core system components
│   │   ├── __init__.py
│   │   ├── base_agent.py      # Base Slack agent class
│   │   ├── config_loader.py   # Configuration loading
│   │   ├── friendly_code_agent.py  # Code-friendly agent base
│   │   ├── log_setup.py       # Logging configuration
│   │   └── utils.py           # Utility functions
│   │
│   ├── integrations/          # External integrations
│   │   └── zoom_client.py     # Zoom API client
│   │
│   ├── orchestrator/          # Orchestration logic
│   │   ├── assignment.py      # Task assignment logic
│   │   └── handlers.py        # Event handlers
│   │
│   ├── tools/                 # Agent tools
│   │   ├── __init__.py
│   │   ├── agent_tools.py     # Core agent tools
│   │   ├── arxiv_tools.py     # ArXiv paper search
│   │   ├── beautiful_search.py # BeautifulSoup web search
│   │   ├── slack_tools.py     # Slack interaction tools
│   │   ├── socratic_tools.py  # Socratic dialog tools
│   │   ├── weather_tools.py   # Weather information
│   │   └── zoom_tools.py      # Zoom meeting tools
│   │
│   └── main.py                # Main entry point
│
├── tests/                     # Test files
│   ├── test_beautiful_search.py
│   ├── test_deep_research.py
│   ├── test_dspy_integration.py
│   ├── test_dspy_practical.py
│   ├── test_research_debug.py
│   └── test_search.py
│
├── .env                       # Environment variables (not in repo)
├── requirements.txt           # Python dependencies
├── ARXIV_INTEGRATION.md       # ArXiv integration guide
└── COLLABORATIVE_AGENTS.md    # Collaborative agents guide
```

## Key Components

### Agents
- **Orchestrator**: Routes tasks to appropriate specialists
- **Grok**: Research and analysis specialist with ArXiv, weather, and search tools
- **Writer**: Content creation specialist with Socratic dialog capabilities

### Core Features
- DSPy integration for intelligent task processing
- Collaborative agent negotiation for optimal task assignment
- BeautifulSoup-based web search (replaced DuckDuckGo)
- Slack integration with threaded conversations
- Tool-based architecture for extensibility

### Recent Changes (Cleanup)
- Removed unused files: cli.py, tts_tools.py, slack_helpers.py, benchmark_search.py, import_tree.svg, dspy_agent.py
- Fixed corrupted requirements.txt
- Consolidated redundant test files
- Moved completed plans to deprecated folder
- Removed obsolete notes.md

## Getting Started
See `docs/ENV_SETUP.md` for environment configuration and `docs/QUICKSTART_BEAUTIFULSOUP.md` for usage.