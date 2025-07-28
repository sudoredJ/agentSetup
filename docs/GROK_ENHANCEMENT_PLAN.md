# Plan: Transform Grok into Deep Research Specialist

## Current State Analysis

### Grok's Current Setup
- **Primary function**: Fetching and summarizing content from URLs
- **Tools available**: 
  - fetch_and_summarize_tool
  - Slack communication tools
  - Zoom meeting creation
- **Confidence triggers**: URLs, links, "fetch", "summarize"

### Goal
Transform Grok from a simple URL fetcher into a comprehensive deep research specialist without creating new Slack bot tokens.

## Implementation Plan

### Step 1: Update Grok's Tool Set
**File**: `configs/agents/grok_agent.yaml`
- Add `web_search_tool` to available tools
- Add `deep_research_tool` to available tools
- Keep existing fetch_and_summarize_tool for URL analysis

### Step 2: Enhance Grok's System Prompt
**File**: `configs/agents/grok_agent.yaml`
- Update system prompt to emphasize research capabilities
- Add instructions for when to use each tool
- Maintain backward compatibility for URL fetching

### Step 3: Update Evaluation Logic
**File**: `src/agents/specialist_agent.py`
- Modify Grok's confidence scoring in `evaluate_request()`
- Add triggers for research-related keywords
- Increase confidence for complex questions

### Step 4: Remove Researcher References
- Delete `configs/agents/researcher_agent.yaml`
- Remove Researcher token references from `configs/system_config.yaml`
- Update documentation to reflect Grok as the research specialist

## Verification Checklist

Before implementation:
- [x] Grok already has bot tokens (no new tokens needed)
- [x] Research tools are already implemented and tested
- [x] Grok's current functionality can be preserved
- [x] No breaking changes to existing system

## Implementation Steps

1. **Update Grok's configuration** - Add new tools and enhanced prompt
2. **Modify evaluation logic** - Make Grok respond to research requests
3. **Clean up** - Remove unnecessary Researcher references
4. **Test** - Verify Grok handles both URL fetching AND deep research

## Benefits
- No new Slack app/tokens required
- Leverages existing infrastructure
- Grok becomes more powerful and versatile
- Maintains backward compatibility