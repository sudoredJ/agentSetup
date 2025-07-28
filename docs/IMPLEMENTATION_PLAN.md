# Implementation Plan: Enhanced Agent Capabilities

## Overview
This document outlines the implementation plan for enhancing the multi-agent Slack system with new capabilities:
1. Chatbot agentic-style Q&A/retrieval
2. Deep research tasks
3. Socratic dialog agent
4. Toy tasks with open web interaction

## Current State Analysis

### Existing Capabilities
- ✅ Basic Q&A through Writer/Grok/Researcher agents
- ✅ Web fetching (fetch_and_summarize_tool)
- ✅ Slack interaction tools
- ✅ Multi-agent coordination
- ⚠️ Limited web search (placeholder only)
- ❌ No persistent memory/retrieval
- ❌ No deep research workflows
- ❌ No Socratic dialog patterns

## Task Breakdown

### Task 1: Enhanced Q&A with Retrieval (Priority: HIGH)
**Goal**: Upgrade existing agents to support context-aware Q&A with memory retrieval

#### Subtasks:
1. **Implement Working Web Search Tool** ✓ Verified
   - Replace placeholder web_search_tool with DuckDuckGo integration
   - Add search result parsing and ranking
   - Test with various query types
   
2. **Add Memory/Context Storage** ✓ Verified
   - Create simple file-based storage for conversation history
   - Implement retrieval based on semantic similarity
   - Add memory management to SpecialistAgent base class

3. **Enhance Researcher Agent** ✓ Verified
   - Add multi-step research capability
   - Implement source citation
   - Add fact verification workflow

**Estimated effort**: 2-3 hours

### Task 2: Deep Research Capabilities (Priority: MEDIUM)
**Goal**: Enable multi-step, thorough research workflows

#### Subtasks:
1. **Create Research Plan Generator** ✓ Verified
   - Tool to break down research questions into sub-queries
   - Dependency tracking between research steps
   - Progress tracking and reporting

2. **Implement Research Execution Engine** ✓ Verified
   - Sequential/parallel query execution
   - Result aggregation and synthesis
   - Automatic source documentation

3. **Add Research Summary Tool** ✓ Verified
   - Structured output formats (bullet points, reports)
   - Citation management
   - Confidence scoring for findings

**Estimated effort**: 3-4 hours

### Task 3: Socratic Dialog Agent (Priority: MEDIUM) ✅ COMPLETED
**Goal**: Create an agent that guides users through thoughtful questioning

#### Implementation Summary:
- **Integrated into Writer Agent** - No new agent needed, enhanced existing Writer
- **DSPy-Powered** - Leverages DSPy ChainOfThought for intelligent dialog management
- **Full Tool Suite** - All three Socratic tools implemented and integrated
- **State Management** - Persistent dialog tracking per user
- **Natural Progression** - Four-stage dialog flow (exploring → clarifying → challenging → reflecting)

#### Completed Subtasks:
1. **Enhanced Writer Agent Profile** ✅
   - Updated writer_agent.yaml with Socratic capabilities
   - Added DSPy integration (`use_dspy: true`)
   - Included Socratic system prompts

2. **Implemented Socratic Tools** ✅
   - `question_generator_tool`: Creates contextual probing questions
   - `dialog_tracker_tool`: Maintains conversation state with JSON persistence
   - `insight_extractor_tool`: Identifies and tracks key learnings

3. **Added Dialog Management** ✅
   - DSPy SocraticModule with intelligent stage progression
   - Question type variation based on dialog stage
   - Context-aware question generation
   - Graceful topic transitions and insight tracking

**Actual effort**: 2 hours
**Documentation**: See SOCRATIC_DIALOG_GUIDE.md for complete usage guide

### Task 4: Open Web Interaction Tasks (Priority: LOW)
**Goal**: Enable fun, interactive web-based capabilities

#### Subtasks:
1. **Weather Fetching Tool** ✓ Verified
   - Integration with weather API
   - Location parsing
   - Formatted weather reports

2. **News Summary Tool** ✓ Verified
   - RSS/news API integration
   - Topic-based filtering
   - Daily digest generation

3. **Wikipedia Explorer Tool** ✓ Verified
   - Random article fetching
   - Topic exploration
   - Fun fact extraction

**Estimated effort**: 2 hours

## Implementation Order

Based on dependencies and value, recommended order:
1. **Web Search Tool** (enables everything else)
2. **Memory/Context Storage** (foundation for better Q&A)
3. **Enhanced Researcher Agent** (immediate value)
4. **Socratic Agent** (new capability)
5. **Deep Research Engine** (builds on 1-3)
6. **Web Interaction Tools** (fun additions)

## Technical Considerations

### For Web Search Implementation:
- Use `duckduckgo-search` Python package
- Implement rate limiting
- Add result caching
- Handle search failures gracefully

### For Memory Storage:
- Start with JSON file storage
- Use embeddings for semantic search (sentence-transformers)
- Implement TTL for old memories
- Add privacy controls

### For Socratic Dialog:
- Maintain conversation state in memory
- Use LLM to generate contextual questions
- Track user engagement metrics
- Implement fallback strategies

## Success Criteria

### Task 1 Success:
- Agents can search the web and cite sources
- Previous conversations influence responses
- Research quality improves measurably

### Task 2 Success:
- Complex research tasks completed autonomously
- Multi-source synthesis works correctly
- Clear, well-structured research outputs

### Task 3 Success:
- Natural Socratic conversations
- Users report deeper insights
- Appropriate question progression

### Task 4 Success:
- Reliable web data fetching
- Engaging user interactions
- Low latency responses

## Risk Mitigation

1. **API Rate Limits**: Implement caching and queuing
2. **Memory Growth**: Set storage limits and cleanup policies
3. **Response Time**: Use async operations where possible
4. **Error Handling**: Graceful degradation for all features

## Next Steps

1. Review and approve this plan
2. Start with Task 1, Subtask 1: Web Search Tool
3. Test each component thoroughly before moving on
4. Document new tools and capabilities
5. Update agent profiles as needed

---

**Ready to proceed?** We'll start with implementing a proper web search tool to replace the placeholder.