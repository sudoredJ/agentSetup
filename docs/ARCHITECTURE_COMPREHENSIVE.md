# Multi-Agent Slack System - Comprehensive Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Core Components](#core-components)
4. [Detailed Component Documentation](#detailed-component-documentation)
   - [Entry Point](#entry-point-srcmainpy)
   - [Core Framework](#core-framework)
   - [Orchestrator System](#orchestrator-system)
   - [Agent System](#agent-system)
   - [Tool System](#tool-system)
   - [Integration Layer](#integration-layer)
   - [Configuration System](#configuration-system)
5. [Data Flow](#data-flow)
6. [Threading Model](#threading-model)
7. [Key Design Decisions](#key-design-decisions)
8. [Dependencies](#dependencies)
9. [Extension Guide](#extension-guide)

## System Overview

This codebase implements a sophisticated multi-agent Slack bot system where an Orchestrator bot coordinates between specialized AI agents to handle user requests. The system leverages:

- **Slack Socket Mode** for real-time bidirectional communication
- **DSPy (Declarative Self-improving Language Programs)** for enhanced reasoning
- **BeautifulSoup-based web scraping** for search capabilities
- **Modular tool system** for extensible functionality
- **Collaborative evaluation** for improved task assignment

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           SLACK WORKSPACE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  User ──@orchestrator──> Orchestrator Bot                          │
│                              │                                       │
│                              ▼                                       │
│                     Coordination Channel                             │
│                              │                                       │
│                    ┌─────────┴──────────┐                          │
│                    ▼                    ▼                           │
│              Grok Agent           Writer Agent                      │
│              (Research)           (Writing/Socratic)                │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         SYSTEM ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐     ┌──────────────┐     ┌────────────────┐      │
│  │   main.py   │────▶│ Orchestrator │────▶│  Assignment    │      │
│  │  (Entry)    │     │   Handlers   │     │    Logic       │      │
│  └─────────────┘     └──────────────┘     └────────────────┘      │
│         │                                           │                │
│         ▼                                           ▼                │
│  ┌─────────────┐     ┌──────────────┐     ┌────────────────┐      │
│  │ BaseAgent   │────▶│ Specialist   │────▶│ Collaborative  │      │
│  │ Framework   │     │   Agent      │     │  Evaluation    │      │
│  └─────────────┘     └──────────────┘     └────────────────┘      │
│         │                    │                                       │
│         ▼                    ▼                                       │
│  ┌─────────────┐     ┌──────────────┐                             │
│  │DSPy/Friendly│────▶│    Tools     │                             │
│  │CodeAgent    │     │   System     │                             │
│  └─────────────┘     └──────────────┘                             │
│                              │                                       │
│                    ┌─────────┴──────────┐                          │
│                    ▼                    ▼                           │
│             BeautifulSoup         Slack/Zoom                        │
│                Search            Integrations                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Components

### High-Level Component Overview

| Component | Purpose | Location |
|-----------|---------|----------|
| **Entry Point** | System initialization and main loop | `src/main.py` |
| **Core Framework** | Base classes and utilities | `src/core/` |
| **Orchestrator** | Task routing and assignment | `src/orchestrator/` |
| **Agents** | Specialized task processors | `src/agents/` |
| **Tools** | Callable functions for agents | `src/tools/` |
| **Integrations** | External service connectors | `src/integrations/` |
| **Configuration** | System and agent settings | `configs/` |

## Detailed Component Documentation

### Entry Point (`src/main.py`)

The main entry point orchestrates the entire system startup and coordination.

#### Key Functions

**`main()`** - Primary system initialization
- **Environment Setup**
  - Loads `.env` file from project root
  - Initializes Rich-based logging system
  - Loads system configuration from `configs/system_config.yaml`
  - Sets API keys in environment variables

- **Bot Initialization**
  ```python
  # 1. Create Orchestrator bot
  orchestrator = BaseAgent(name="Orchestrator", token=config['slack_tokens']['orchestrator_bot_token'])
  
  # 2. Load all specialist agents from configs/agents/*.yaml
  for each YAML profile:
      spec = SpecialistAgent(agent_profile, slack_token, coordination_channel)
      specialists[agent_name] = spec
  ```

- **Handler Registration**
  - `@orchestrator.app.event("app_mention")` - Handles user mentions
  - `@orchestrator.app.event("message")` - Suppresses channel chatter
  - Registers specialist handlers via `register_specialist_handlers()`

**`check_and_assign(client, thread_ts, request_data)`** - Task assignment logic
- **Parameters**:
  - `timeout`: 15 seconds total wait
  - `check_interval`: 0.5 seconds between polls
  - `min_confidence`: 30% minimum threshold
- **Process**:
  1. Polls coordination channel for specialist evaluations
  2. Parses messages matching: `"🧠 {Name} reporting: Confidence {X}%"`
  3. Handles rate limiting with exponential backoff
  4. Assigns to highest confidence specialist above threshold
  5. Falls back to "no specialist confident enough" message

**`handle_orchestrator_mention(event, client)`** - User request handler
1. Extracts and sanitizes user message
2. Fetches thread context (up to 20 messages)
3. Posts evaluation request to coordination channel
4. Starts assignment thread with `check_and_assign()`

**`register_specialist_handlers(specialist, specialist_name)`** - Event handler registration
- Creates closures for specialist-specific handlers
- Registers three handlers per specialist:
  - Message handler for evaluations and assignments
  - Mention handler to redirect to orchestrator
  - Reaction handler (placeholder)

#### Global State
- `active_requests`: Dict tracking ongoing requests by thread timestamp
- `handlers_to_close`: List of SocketMode handlers for cleanup
- `specialists`: Dict of loaded SpecialistAgent instances

### Core Framework

#### `src/core/base_agent.py`

**Class: `ThreadSafeSocketModeHandler`**
- Extends Slack's SocketModeHandler with thread safety
- **Methods**:
  - `start()`: Connect without signal handlers, auto-reconnect on disconnect
  - `close()`: Clean connection shutdown

**Class: `BaseAgent`**
- Foundation for all Slack bots in the system
- **Constructor**: `__init__(name: str, token: str)`
  - Initializes Slack Bolt App
  - Wraps all API calls with verbose logging
  - Performs auth test to get bot user ID
- **Methods**:
  - `start_in_thread(app_token)`: Starts bot in daemon thread
- **Features**:
  - Automatic API call logging with timing
  - Graceful error handling
  - Thread-safe WebSocket management

#### `src/core/friendly_code_agent.py`

**Class: `FriendlyCodeAgent`**
- Wrapper around smolagents CodeAgent with fallback capabilities
- **Constructor**: `__init__(tools, model, max_steps=3)`
  - Attempts to use real smolagents if available
  - Falls back to manual tool execution
- **Methods**:
  - `run(prompt)`: Execute prompt with model and tools
  - `_execute_tool_calls(response)`: Extract and run tool calls from text
  - `_parse_args(args_str)`: Parse function arguments from various formats
- **Supported Tool Call Formats**:
  - Direct: `function_name(args)`
  - Backticks: `` `function_name(args)` ``
  - Code blocks: ``` ```function_name(args)``` ```

#### `src/core/dspy_agent.py`

**Class: `DSPyToolSignature`**
- DSPy signature for tool execution decisions
- Input fields: `request`, `context`, `available_tools`
- Output fields: `reasoning`, `tool_name`, `tool_args`

**Class: `DSPyAgent`**
- Advanced reasoning agent using DSPy
- **Constructor**: `__init__(tools, model_id, system_prompt)`
  - Initializes DSPy with LiteLLM wrapper
  - Sets up ChainOfThought reasoning
  - Imports BeautifulSoup search system
- **Methods**:
  - `forward(request, context)`: Main execution with DSPy reasoning
  - `optimize_with_examples(examples)`: BootstrapFewShot optimization
  - `run(prompt)`: Compatibility interface
- **Fallback Mechanisms**:
  - Mock LM when API unavailable
  - Mock tool selector for testing
  - Graceful degradation on failures

#### `src/core/config_loader.py`

**Function: `load_config(path='configs/system_config.yaml')`**
- Loads YAML with environment variable substitution
- Supports `${ENV_VAR}` placeholders (quoted or unquoted)
- Exits with error if required variables missing
- Used by all components for configuration

#### `src/core/log_setup.py`

**Function: `init_logging(level=logging.INFO)`**
- Configures Rich console handler for beautiful output
- Silences noisy third-party loggers
- Returns Console instance for additional formatting

#### `src/core/utils.py`

**Function: `sanitize_mentions(text, slack_client)`**
- Converts Slack user IDs to readable usernames
- Uses LRU cache for efficiency (128 entries)
- Handles lookup failures gracefully

**Function: `format_context_for_ai(context_messages, request_data)`**
- Formats Slack messages for LLM consumption
- Includes:
  - Conversation history
  - Current request details
  - User and channel information
  - Participant list

### Orchestrator System

#### `src/orchestrator/assignment.py`

**Function: `check_and_assign(client, thread_ts, request_data, *, specialists, coordination_channel, active_requests)`**

Sophisticated task assignment with collaborative discussion support.

**Parameters**:
- `timeout`: 8 seconds (reduced for faster response)
- `check_interval`: 0.3 seconds between polls
- `min_confidence`: 30% minimum threshold
- `discussion_threshold`: 50% for triggering collaboration

**Process Flow**:
1. **Initial Evaluation Phase**
   - Polls for specialist confidence reports
   - Handles Slack rate limiting gracefully
   - Collects evaluations with pattern matching

2. **Decision Logic**
   ```python
   if max_confidence >= min_confidence:
       if max_confidence < discussion_threshold:
           # Trigger collaborative discussion
           coordinator = AgentDiscussionCoordinator(...)
           final_evaluations = coordinator.facilitate_discussion()
       # Assign to highest confidence agent
   else:
       # No agent confident enough
   ```

3. **Assignment Notification**
   - Posts "ASSIGNED: @{bot_id}" message
   - Updates active_requests tracking
   - Handles errors with user notification

#### `src/orchestrator/handlers.py`

**Function: `register_specialist_handlers(specialist, specialist_name, *, orchestrator, coordination_channel, active_requests)`**

Registers Slack event handlers for each specialist agent.

**Registered Handlers**:

1. **`spec_message_handler`** - Main message processor
   - **Evaluation Phase**: Responds to "please evaluate" requests
     - Extracts task from regex pattern
     - Runs evaluation asynchronously
     - Posts confidence report
   - **Assignment Phase**: Handles "ASSIGNED: @bot" messages
     - Fetches full thread context
     - Retrieves original user context
     - Starts assignment processing thread

2. **`spec_mention_handler`** - Redirect mentions
   - Only responds outside coordination channel
   - Directs users to mention orchestrator

3. **`spec_reaction_handler`** - Placeholder
   - Prevents warning logs for reactions

### Agent System

#### `src/agents/specialist_agent.py`

**Class: `SpecialistAgent(BaseAgent)`**

The core specialist implementation with tool integration and task processing.

**Constructor Parameters**:
- `agent_profile`: YAML configuration dict
- `slack_token`: Bot user OAuth token
- `coordination_channel`: Channel ID for coordination
- `use_dspy`: Whether to use DSPy agent (optional)

**Key Methods**:

**`_initialize_tools()`** - Dynamic tool loading
```python
# For each tool in profile:
1. Import module dynamically
2. Get function references
3. Inject dependencies:
   - module._client = self.client
   - module._bot_name = self.bot_name
   - module._zoom_client = zoom_client
4. Return list of callable tools
```

**`evaluate_request(request_text)`** - Confidence calculation
- Returns: `(can_handle: bool, confidence: int)`
- Agent-specific patterns:
  - **Grok**: Research keywords, URLs → 70-90%
  - **Writer**: Writing/creative keywords → 80-95%
  - **Socratic priority**: Writer gets 95% for Socratic requests
- Special cases:
  - Temperature conversion → 100%
  - Simple greetings → 90%
  - DM requests → 85%

**`collaborative_evaluate(task, discussion_history)`** - Enhanced evaluation
- Uses DSPy CollaborativeEvaluator if available
- Adjusts confidence based on discussion context
- Falls back to standard evaluation

**`process_assignment(request_text, original_user, thread_ts, context)`** - Task execution
1. **Context Extraction**
   - Channel ID and thread timestamp from metadata
   - User ID from context or metadata
   
2. **Simple Request Handling**
   ```python
   # Direct handling without AI:
   - Greetings → Friendly response
   - Temperature conversion → Calculate directly  
   - DM requests → Extract message and send
   - TTS shortcuts (@tts, ^tts) → Generate audio
   ```

3. **Research Optimization (Grok)**
   ```python
   if agent_name == "Grok" and is_research_request:
       # Direct execution bypassing AI
       result = deep_research_tool(topic)
       send_result_as_dm(result)
   ```

4. **Complex Request Processing**
   - Format system prompt with context
   - Add metadata for tools
   - Execute with AI agent (DSPy or FriendlyCode)
   - Send results via DM or channel

**`_check_tts_shortcut(text)`** - TTS detection
- Patterns: `@tts <text>` or `^tts <text>`
- Returns extracted text for TTS generation

#### `src/agents/dspy_modules.py`

Specialized DSPy modules for different agent capabilities.

**Class: `ResearchModule(dspy.Module)`**
- **Purpose**: Multi-angle research with synthesis
- **DSPy Components**:
  - `generate_queries`: ChainOfThought("topic -> query1, query2, query3")
  - `synthesize`: ChainOfThought("results -> summary")
- **Process**:
  1. Generate 3 search queries from topic
  2. Execute searches with BeautifulSoup
  3. Synthesize results into summary
- **Fallback**: Mock chains when LM unavailable

**Class: `WriterModule(dspy.Module)`**
- **Purpose**: Structured writing with Socratic capabilities
- **DSPy Components**:
  - `planner`: ChainOfThought("request -> outline")
  - `writer`: ChainOfThought("outline, style -> content")
  - `editor`: ChainOfThought("content -> edited_content")
- **Integrated Modules**:
  - `socratic_module`: Full Socratic dialog handling
- **Routing Logic**:
  - Socratic keywords → SocraticModule
  - Writing requests → Planning → Writing → Editing pipeline

**Class: `AnalysisModule(dspy.Module)`**
- **Purpose**: Data gathering and analysis
- **Process**:
  1. Extract search terms from request
  2. Gather data via BeautifulSoup
  3. Analyze with ChainOfThought
- **Features**:
  - Stop word filtering
  - Multi-source aggregation

**Class: `GrokDSPyAgent(dspy.Module)`**
- **Purpose**: Enhanced Grok with research and Socratic capabilities
- **Initialization**:
  - Creates LiteLLM wrapper for Claude/OpenAI
  - Initializes research and Socratic modules
  - Sets up tool selector
- **Routing Priority**:
  1. Socratic requests → SocraticModule
  2. Research requests → ResearchModule  
  3. Other → Standard tool selection
- **User ID Extraction**: From context messages

**Class: `SocraticModule(dspy.Module)`**
- **Purpose**: Comprehensive Socratic dialog implementation
- **DSPy Components**:
  - `theme_identifier`: Extract core theme and assumptions
  - `question_generator`: Generate contextual questions
  - `insight_extractor`: Identify key learnings
  - `dialog_router`: Determine dialog progression
- **Dialog Stages**: exploring → clarifying → challenging → reflecting
- **Key Methods**:
  - `_initiate_socratic_dialog()`: Start new conversation
  - `_continue_socratic_dialog()`: Progress existing dialog
  - `_is_dialog_continuation()`: Detect ongoing Socratic conversations
- **Features**:
  - Persistent dialog tracking per user
  - Stage-appropriate question generation
  - Insight extraction and summary

#### `src/agents/negotiation_module.py`

Enables collaborative decision-making between agents.

**Class: `CollaborativeEvaluator(dspy.Module)`**
- **Purpose**: Agent self-evaluation with peer consideration
- **Method**: `evaluate_with_discussion(task, other_evaluations)`
  - Analyzes other agents' evaluations
  - Adjusts own confidence based on discussion
  - Returns (confidence, reasoning)

**Class: `AgentDiscussionCoordinator`**
- **Purpose**: Facilitate multi-agent collaboration
- **Parameters**:
  - `discussion_rounds`: 3 maximum
  - `target_confidence`: 50% threshold
- **Process**:
  1. Initial evaluations below threshold
  2. Agents discuss and re-evaluate
  3. Post updates to Slack thread
  4. Return final evaluations

### Tool System

#### `src/tools/agent_tools.py`

Domain-agnostic tools for research and content processing.

**`analyze_request_tool(request: str) -> str`**
- Classifies user intent for research context
- Categories: greeting, DM request, creative writing, information request

**`web_search_tool(query: str, max_results: int = 5) -> str`**
- BeautifulSoup-based multi-engine search
- Formats results with title, URL, snippet, source
- Handles failures gracefully

**`compose_message_tool(recipient: str, content: str = None, tone: str = "friendly") -> str`**
- Message formatting with tone support
- Tones: friendly, formal, casual, professional
- Includes appropriate prefixes and signatures

**`proofread_tool(text: str) -> str`**
- Simple spelling/grammar corrections
- Dictionary-based replacements
- Returns corrected text

**`deep_research_tool(topic: str, num_searches: int = 3) -> str`**
- Multi-angle research implementation
- Search angles:
  1. Direct topic search
  2. Explanatory search ("what is X explained")
  3. Recent developments ("X 2024 2025")
  4. Best practices (if num_searches > 3)
  5. Common problems
  6. Future trends
- Deduplicates results by URL
- Synthesizes findings into report

**`fetch_and_summarize_tool(url: str) -> str`**
- Webpage content extraction
- Uses BeautifulSoup scraping
- Returns title, summary, word count

#### `src/tools/beautiful_search.py`

Web scraping-based search system replacing API dependencies.

**Class: `BeautifulSearch`**

**Configuration Loading**:
```python
default_config = {
    'enabled': True,
    'engines': ['google', 'bing', 'wikipedia', 'duckduckgo'],
    'timeout': 15,
    'max_results_per_engine': 5
}
# Loads from system_config.yaml if available
```

**Search Methods**:

**`search_google(query, max_results)`**
- Scrapes Google search results
- Extracts: title, URL, snippet
- Handles div.g containers

**`search_bing(query, max_results)`**
- Scrapes Bing results
- Targets li.b_algo elements
- Similar extraction pattern

**`search_wikipedia(query, max_results)`**
- Direct page lookup first
- Falls back to search API
- Extracts first paragraph

**`search_duckduckgo(query, max_results)`**
- Uses HTML interface
- Parses div.result containers
- Handles redirect URLs

**`search_with_fallbacks(query, max_results)`**
- Tries engines in configured order
- Deduplicates by URL
- Adds delays between engines
- Returns combined results

**`scrape_webpage(url)`**
- Full content extraction
- Removes script/style/nav elements
- Returns structured data:
  - title, content, summary, word_count

**Global Instance**: `beautiful_search` - Singleton for all agents

#### `src/tools/slack_tools.py`

Slack interaction tools with TTS support.

**Module-level Dependencies**:
```python
_client: Optional[WebClient] = None  # Injected by SpecialistAgent
_bot_name: Optional[str] = None      # Injected by SpecialistAgent
```

**`slack_dm_tool(user_id: str, message: str, thread_ts: str = None) -> str`**
- Sends direct messages
- IMPORTANT: Never accepts thread_ts (Slack limitation)
- Opens conversation if needed
- Returns success/failure message

**`lookup_user_tool(name: str) -> str`**
- Resolves usernames to Slack user IDs
- Case-insensitive matching
- Searches display names and real names
- Returns formatted user list or "not found"

**`slack_post_tool(channel_id: str, message: str, thread_ts: str = None) -> str`**
- Posts to channels/threads
- Validates inputs
- Returns success confirmation

**`slack_channel_tool(...)`**
- Alias for slack_post_tool
- Maintains backward compatibility

**`slack_tts_tool(channel_id: str, text: str, voice: str = "en-US-AriaNeural", rate: str = "+0%", thread_ts: str = None) -> str`**
- Text-to-speech generation
- Process:
  1. Generate audio with edge-tts
  2. Upload to file.io (primary) or 0x0.st (fallback)
  3. Post audio link to Slack
- Includes "🔊 Listen to audio" button
- Cleans up temp files

**TTS Implementation Details**:
```python
# No Slack file upload - uses external hosting
1. edge_tts.Communicate(text, voice, rate)
2. Save to temp file
3. Upload to file.io (24hr retention)
4. Fallback to 0x0.st if needed
5. Post link with attachment formatting
```

#### `src/tools/socratic_tools.py`

Socratic method conversation tools.

**Module State**:
```python
DIALOG_STATE_FILE = "socratic_dialog_state.json"
dialog_state = {}  # Persistent across sessions
```

**`question_generator_tool(topic: str, question_type: str = "exploring", context: str = None) -> str`**
- Question types with templates:
  - **exploring**: Open-ended discovery questions
  - **clarifying**: Definition and precision questions
  - **challenging**: Assumption-testing questions
  - **reflecting**: Summary and insight questions
- Contextualizes based on previous answers
- Returns 2-3 questions per call

**`dialog_tracker_tool(user_id: str, action: str, data: str = None) -> str`**
- Actions:
  - **add_topic**: Start tracking new topic
  - **add_insight**: Record key insight
  - **get_summary**: Generate dialog summary
  - **reset**: Clear user's dialog history
- Persistent JSON storage
- Per-user dialog management

**`insight_extractor_tool(conversation: str, focus: str = None) -> str`**
- Heuristic-based extraction
- Patterns detected:
  - Realizations ("I realize", "I see that")
  - Understanding ("I understand", "makes sense")
  - Beliefs ("I believe", "I think")
  - Importance ("important to me", "matters")
  - Questions (ending with "?")
- Returns bullet-pointed insights

#### `src/tools/tts_tools.py`

Text-to-speech generation tools using Edge-TTS.

**Class: `TextToSpeechTool(Tool)`**
- **Purpose**: Generate TTS audio files
- **Inputs**: text, voice (default: en-US-AriaNeural), rate (default: +0%)
- **Output**: Local file path
- **Implementation**:
  ```python
  async def _synthesize():
      communicate = edge_tts.Communicate(text, voice, rate)
      await communicate.save(file_path)
  
  # Handle existing event loops gracefully
  try:
      asyncio.run(_run())
  except RuntimeError:
      loop = asyncio.get_event_loop()
      loop.run_until_complete(_run())
  ```

**Class: `SlackTTSTool(Tool)`**
- **Purpose**: Generate TTS and upload to Slack
- **Dependencies**: Requires injected Slack client
- **Process**:
  1. Generate audio via TextToSpeechTool
  2. Upload with `files_upload` API
  3. Clean up temp file
- **Note**: Requires files:write scope

#### `src/tools/zoom_tools.py`

Zoom meeting creation integration.

**Module Dependencies**:
```python
_zoom_client: Optional[ZoomClient] = None  # Injected by SpecialistAgent
```

**`create_zoom_meeting(topic: str, duration: int = 60, start_time: str = None, password: str = None, announce_channel: str = None) -> str`**
- Creates Zoom meeting via injected client
- Optional Slack announcement
- Returns meeting details or error
- Supports scheduled meetings

### Integration Layer

#### `src/integrations/zoom_client.py`

Zoom API client with OAuth support.

**Class: `ZoomClient`**

**Constructor Parameters**:
- `client_id`: OAuth app client ID
- `client_secret`: OAuth app client secret  
- `account_id`: Server-to-Server OAuth account
- `stub`: Use fake data when True

**Initialization**:
```python
# Determines mode based on credentials
if not all([client_id, client_secret, account_id]):
    self.stub = True  # Stub mode
    logger.warning("Missing Zoom credentials - stub mode")
```

**Methods**:

**`create_meeting(...)`**
- Parameters: topic, type, duration, start_time, password, settings
- Meeting types:
  - 1: Instant meeting
  - 2: Scheduled meeting
- Returns: Dict with join_url, start_url, password

**`test_connection()`**
- Validates API access
- Gets current user info
- Returns success boolean

**`_get_token()`** (Private)
- Server-to-Server OAuth flow
- POST to oauth/token endpoint
- Caches token (not implemented)
- Returns access token

**Stub Mode Behavior**:
- Returns realistic fake data
- Allows testing without credentials
- Log warnings for all operations

### Configuration System

#### System Configuration (`configs/system_config.yaml`)

Central configuration with environment variable support.

**Structure**:
```yaml
slack_tokens:
  orchestrator_bot_token: ${ORCHESTRATOR_BOT_TOKEN}
  orchestrator_app_token: ${ORCHESTRATOR_APP_TOKEN}
  grok_bot_token: ${GROK_BOT_TOKEN}
  grok_app_token: ${GROK_APP_TOKEN}
  writer_bot_token: ${WRITER_BOT_TOKEN}
  writer_app_token: ${WRITER_APP_TOKEN}

api_keys:
  anthropic: ${ANTHROPIC_API_KEY}
  openai: ${OPENAI_API_KEY}     # Optional
  zoom_client_id: ${ZOOM_CLIENT_ID}
  zoom_client_secret: ${ZOOM_CLIENT_SECRET}
  zoom_account_id: ${ZOOM_ACCOUNT_ID}

channels:
  coordination: ${COORDINATION_CHANNEL_ID}

features:
  tts:
    enabled: true
    default_voice: "en-US-AriaNeural"
    voices:
      - "en-US-AriaNeural"
      - "en-US-GuyNeural"
      - "en-GB-SoniaNeural"
  
  search:
    enabled: true
    engines: ['google', 'bing', 'wikipedia', 'duckduckgo']
    timeout: 15
    max_results_per_engine: 5
```

#### Agent Configurations

**Grok Agent (`configs/agents/grok_agent.yaml`)**:
```yaml
name: "Grok"
description: "A specialist agent for deep research, web searches, and content analysis."
model_id: "claude-3-haiku-20240307"
use_dspy: true  # Enable DSPy for enhanced reasoning

system_prompt: |
  You are Grok, an expert AI research specialist...
  IMPORTANT: You do NOT handle Socratic dialog requests...
  
tools:
  - module: "src.tools.agent_tools"
    functions: 
      - "analyze_request_tool"
      - "web_search_tool"
      - "deep_research_tool"
      - "fetch_and_summarize_tool"
  - module: "src.tools.slack_tools"
    functions: ["slack_dm_tool", "slack_channel_tool", ...]
  - module: "src.tools.zoom_tools"
    functions: ["create_zoom_meeting"]
```

**Writer Agent (`configs/agents/writer_agent.yaml`)**:
```yaml
name: "Writer"
description: "A specialist agent for creative writing, drafting, message composition, and Socratic dialog."
model_id: "claude-3-haiku-20240307"
use_dspy: true  # Enable DSPy for Socratic dialog

system_prompt: |
  You are Writer, a helpful AI specialist with two core capabilities:
  1. Creative Writing...
  2. Socratic Dialog...

tools:
  - module: "src.tools.slack_tools"
    functions: [...]
  - module: "src.tools.socratic_tools"
    functions: 
      - "question_generator_tool"
      - "dialog_tracker_tool"
      - "insight_extractor_tool"
  - module: "src.tools.agent_tools"
    functions:
      - "compose_message_tool"
      - "proofread_tool"
```

## Data Flow

### Request Processing Flow

1. **User Interaction**
   ```
   User mentions @orchestrator in Slack
   → Orchestrator receives app_mention event
   → Sanitizes text and fetches context
   → Posts to coordination channel
   ```

2. **Specialist Evaluation**
   ```
   All specialists see evaluation request
   → Each evaluates confidence (0-100%)
   → Posts "🧠 {Name} reporting: Confidence X%"
   → Orchestrator polls for responses (15s timeout)
   ```

3. **Assignment Decision**
   ```
   If max_confidence >= 30%:
       If max_confidence < 50%:
           → Trigger collaborative discussion
       → Assign to highest confidence agent
   Else:
       → No agent confident enough
   ```

4. **Task Execution**
   ```
   Assigned specialist sees "ASSIGNED: @bot"
   → Fetches full context
   → Processes request with tools
   → Sends results via DM or channel
   ```

### Collaborative Discussion Flow

When max confidence is between 30-50%:

1. Coordinator posts discussion prompt
2. Agents provide reasoning (Round 1)
3. Agents adjust based on others' input (Rounds 2-3)
4. Final evaluations determine assignment

## Threading Model

```
Main Thread (main.py)
├── Orchestrator Socket Thread
│   └── Event handlers
├── Grok Socket Thread
│   └── Event handlers
├── Writer Socket Thread
│   └── Event handlers
└── Dynamic Assignment Threads
    ├── Evaluation Threads (per request)
    ├── Assignment Threads (per task)
    └── Discussion Threads (when needed)
```

**Thread Safety Considerations**:
- Each bot has independent Socket Mode connection
- `active_requests` dict accessed from multiple threads
- Slack API calls are thread-safe
- Tool execution happens in assignment threads

## Key Design Decisions

### 1. **Hub-and-Spoke Architecture**
- Centralized orchestrator prevents chaos
- Specialists remain independent
- Clear separation of concerns

### 2. **Coordination Channel Pattern**
- All bot-to-bot communication in one place
- Audit trail of all decisions
- Easy debugging and monitoring

### 3. **Dynamic Tool Loading**
- Tools defined in YAML configs
- Dependency injection at runtime
- Easy to add/remove capabilities

### 4. **DSPy Integration**
- Optional per agent via `use_dspy` flag
- Enhances reasoning capabilities
- Graceful fallback to FriendlyCodeAgent

### 5. **BeautifulSoup Search**
- Avoids API rate limits
- Multiple search engines
- Fallback redundancy

### 6. **Collaborative Evaluation**
- Improves assignment accuracy
- Agents learn from each other
- Configurable thresholds

### 7. **Thread-Based Concurrency**
- Non-blocking event processing
- Parallel specialist evaluation
- Responsive user experience

## Dependencies

### Core Dependencies
- `slack-sdk`: Slack API client
- `slack-bolt`: Slack app framework
- `python-dotenv`: Environment management
- `pyyaml`: Configuration parsing
- `rich`: Terminal formatting

### AI/ML Dependencies
- `smolagents`: Tool-calling agent framework
- `dspy-ai`: Declarative reasoning framework
- `litellm`: Unified LLM interface
- `anthropic`: Claude API (primary)

### Tool Dependencies
- `beautifulsoup4`: Web scraping
- `requests`: HTTP client
- `edge-tts`: Text-to-speech
- `duckduckgo-search`: Search fallback

### Utility Dependencies
- `yaspin`: Terminal spinners
- `colorama`: Cross-platform colors

## Extension Guide

### Adding a New Specialist Agent

1. **Create agent profile** in `configs/agents/`:
   ```yaml
   name: "NewAgent"
   description: "Purpose of this agent"
   model_id: "claude-3-haiku-20240307"
   use_dspy: true  # Optional
   system_prompt: |
     Agent instructions...
   tools:
     - module: "src.tools.needed_tools"
       functions: ["tool1", "tool2"]
   ```

2. **Add tokens** to `.env`:
   ```
   NEWAGENT_BOT_TOKEN=xoxb-...
   NEWAGENT_APP_TOKEN=xapp-...
   ```

3. **Update** `system_config.yaml`:
   ```yaml
   slack_tokens:
     newagent_bot_token: ${NEWAGENT_BOT_TOKEN}
     newagent_app_token: ${NEWAGENT_APP_TOKEN}
   ```

4. **Implement evaluation logic** in `specialist_agent.py`:
   ```python
   if self.name == "NewAgent":
       if "keyword" in request_lower:
           return True, 85
   ```

### Adding a New Tool

1. **Create tool function** with decorator:
   ```python
   @tool
   def my_new_tool(param1: str, param2: int = 10) -> str:
       """Brief description for LLM.
       
       Args:
           param1: Description
           param2: Optional description
       """
       # Implementation
       return result
   ```

2. **Add to agent profile**:
   ```yaml
   tools:
     - module: "src.tools.my_tools"
       functions: ["my_new_tool"]
   ```

3. **Handle dependencies** if needed:
   ```python
   # Module-level for injection
   _special_client = None
   
   def my_new_tool(...):
       if _special_client is None:
           return "Error: Client not initialized"
   ```

### Adding a DSPy Module

1. **Create module class**:
   ```python
   class MyModule(dspy.Module):
       def __init__(self):
           super().__init__()
           self.predictor = dspy.ChainOfThought("input -> output")
       
       def forward(self, input_text):
           result = self.predictor(input=input_text)
           return result.output
   ```

2. **Integrate with agent**:
   ```python
   # In GrokDSPyAgent or similar
   self.my_module = MyModule()
   
   # In forward method
   if "trigger" in request:
       return self.my_module(request)
   ```

This architecture provides a robust, extensible foundation for multi-agent collaboration with sophisticated reasoning capabilities and seamless Slack integration.