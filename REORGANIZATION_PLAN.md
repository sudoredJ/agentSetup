# Codebase Reorganization Plan

## Overview
This document outlines a safe, surgical reorganization of the agentSetup codebase to improve structure without breaking any functionality.

## Key Principles
1. **No Logic Changes**: Only move files and update imports
2. **Backward Compatibility**: Maintain all existing import paths
3. **Incremental Changes**: Can be done step-by-step
4. **Verification**: Test after each change

## Phase 1: Add Missing __init__.py Files

### Step 1.1: Create src/__init__.py
```python
"""Multi-agent Slack system package."""
__version__ = "1.0.0"
```

### Step 1.2: Create data directory
```bash
mkdir src/data
touch src/data/.gitkeep
```

## Phase 2: Reorganize Tools (Most Complex)

### Step 2.1: Create Tool Subdirectories
```bash
mkdir -p src/tools/search
mkdir -p src/tools/communication
mkdir -p src/tools/dialog
mkdir -p src/tools/external
```

### Step 2.2: Create __init__.py files for each subdirectory

**src/tools/search/__init__.py:**
```python
from .beautiful_search import BeautifulSearch, beautiful_search
from .arxiv_tools import (
    search_arxiv_papers, get_arxiv_details, download_arxiv_paper,
    load_arxiv_to_context, get_arxiv_url
)
from .agent_tools import (
    analyze_request_tool, web_search_tool, 
    deep_research_tool, fetch_and_summarize_tool
)

__all__ = [
    'BeautifulSearch', 'beautiful_search',
    'search_arxiv_papers', 'get_arxiv_details', 'download_arxiv_paper',
    'load_arxiv_to_context', 'get_arxiv_url',
    'analyze_request_tool', 'web_search_tool',
    'deep_research_tool', 'fetch_and_summarize_tool'
]
```

**src/tools/communication/__init__.py:**
```python
from .slack_tools import (
    slack_dm_tool, slack_channel_tool, slack_post_tool,
    slack_tts_tool, lookup_user_tool
)
from .slack_helpers import post_slack_message
from .tts_tools import TextToSpeechTool, SlackTTSTool

__all__ = [
    'slack_dm_tool', 'slack_channel_tool', 'slack_post_tool',
    'slack_tts_tool', 'lookup_user_tool',
    'post_slack_message',
    'TextToSpeechTool', 'SlackTTSTool'
]
```

**src/tools/dialog/__init__.py:**
```python
from .socratic_tools import (
    question_generator_tool, dialog_tracker_tool, insight_extractor_tool
)

__all__ = [
    'question_generator_tool', 'dialog_tracker_tool', 'insight_extractor_tool'
]
```

**src/tools/external/__init__.py:**
```python
from .weather_tools import (
    get_weather_forecast, get_current_weather, get_sunrise_sunset
)
from .zoom_tools import create_zoom_meeting

__all__ = [
    'get_weather_forecast', 'get_current_weather', 'get_sunrise_sunset',
    'create_zoom_meeting'
]
```

### Step 2.3: Update main tools/__init__.py for backward compatibility
**src/tools/__init__.py:**
```python
"""
Tools package - maintains backward compatibility while organizing tools into categories.
"""

# Re-export all tools from subdirectories to maintain backward compatibility
from .search import *
from .communication import *
from .dialog import *
from .external import *

# Also support old direct imports
from .search.agent_tools import *
from .search.arxiv_tools import *
from .search.beautiful_search import *
from .communication.slack_tools import *
from .communication.slack_helpers import *
from .communication.tts_tools import *
from .dialog.socratic_tools import *
from .external.weather_tools import *
from .external.zoom_tools import *
```

## Phase 3: Move Files (Carefully)

### Step 3.1: Move Search Tools
```bash
# Move files
mv src/tools/beautiful_search.py src/tools/search/
mv src/tools/arxiv_tools.py src/tools/search/
mv src/tools/agent_tools.py src/tools/search/

# Update imports in agent_tools.py
# Change: from .beautiful_search import beautiful_search
# To: from ..search.beautiful_search import beautiful_search
# OR: from . import beautiful_search (since they're in same directory now)
```

### Step 3.2: Move Communication Tools
```bash
mv src/tools/slack_tools.py src/tools/communication/
mv src/tools/slack_helpers.py src/tools/communication/
mv src/tools/tts_tools.py src/tools/communication/
```

### Step 3.3: Move Dialog Tools
```bash
mv src/tools/socratic_tools.py src/tools/dialog/
```

### Step 3.4: Move External Tools
```bash
mv src/tools/weather_tools.py src/tools/external/
mv src/tools/zoom_tools.py src/tools/external/

# Update import in zoom_tools.py
# Change: from src.integrations.zoom_client import ZoomClient
# No change needed - absolute import still works
```

## Phase 4: Update Import Statements

### Files that need import updates:

1. **src/tools/search/agent_tools.py**
   - Line 26: `from .beautiful_search import beautiful_search` (no change needed)

2. **configs/agents/grok_agent.yaml**
   - Change: `module: "src.tools.agent_tools"`
   - To: `module: "src.tools.search.agent_tools"`
   - OR keep as-is since we re-export in tools/__init__.py

3. **configs/agents/writer_agent.yaml**
   - Similar updates for tool modules
   - OR keep as-is due to re-exports

## Phase 5: Add Project Documentation

### Step 5.1: Create README.md
```markdown
# AgentSetup - Multi-Agent Slack System

A sophisticated multi-agent system for Slack featuring intelligent task routing, specialized AI agents, and comprehensive tool integration.

## Features
- **Orchestrator Bot**: Coordinates task assignment between specialists
- **Specialist Agents**: Writer (creative + Socratic dialog) and Grok (research + arXiv)
- **DSPy Integration**: Enhanced reasoning with self-improving language programs
- **Rich Tool Ecosystem**: Search, TTS, weather, Zoom, and more

## Quick Start
1. Copy `.env.example` to `.env` and add your tokens
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python -m src.main`

## Architecture
See `docs/ARCHITECTURE.md` for detailed system design.

## Directory Structure
- `src/` - Source code
  - `core/` - Foundation classes and utilities
  - `agents/` - Agent implementations
  - `orchestrator/` - Coordination logic
  - `tools/` - LLM-callable tools organized by category
  - `integrations/` - External service clients
- `configs/` - YAML configuration files
- `docs/` - Documentation
- `tests/` - Test suite
```

## Phase 6: Verification Steps

### Step 6.1: Test imports
```python
# Create test_imports.py
import sys
sys.path.append('.')

# Test old import paths still work
from src.tools import web_search_tool, slack_dm_tool, create_zoom_meeting
print("✓ Backward compatibility maintained")

# Test new organized imports
from src.tools.search import web_search_tool
from src.tools.communication import slack_dm_tool
from src.tools.external import create_zoom_meeting
print("✓ New organized imports work")
```

### Step 6.2: Run the system
```bash
python -m src.main
# Verify all agents load correctly
# Test a few commands
```

## Rollback Plan
If anything breaks:
1. Move files back to original locations
2. Revert __init__.py changes
3. System will work as before

## Benefits
1. **Better Organization**: Tools grouped by functionality
2. **Easier Navigation**: Clear categories for different tool types
3. **Maintainability**: Easier to find and modify related tools
4. **Extensibility**: Clear where to add new tools
5. **No Breaking Changes**: All existing imports continue to work