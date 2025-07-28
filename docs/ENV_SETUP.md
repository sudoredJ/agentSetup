# Environment Variables Setup

## Required Environment Variables

### Existing Agents
The following environment variables are already configured in your .env file:
- `ORCHESTRATOR_APP_TOKEN`
- `ORCHESTRATOR_BOT_TOKEN`
- `WRITER_APP_TOKEN`
- `WRITER_BOT_TOKEN`
- `GROK_APP_TOKEN` - Now enhanced with deep research capabilities
- `GROK_BOT_TOKEN` - Now enhanced with deep research capabilities
- `ANTHROPIC_API_KEY`
- `COORDINATION_CHANNEL`

### Optional: Zoom Integration
If using Zoom features:
```
ZOOM_ACCOUNT_ID=...
ZOOM_CLIENT_ID=...
ZOOM_CLIENT_SECRET=...
```

## What's New

### Grok Enhanced as Deep Research Specialist
1. **web_search_tool**: Now uses real DuckDuckGo search instead of placeholder
2. **deep_research_tool**: Performs multi-angle research with compiled reports
3. **Grok agent**: Transformed from simple URL fetcher to comprehensive research specialist
   - Maintains backward compatibility for URL fetching
   - Now handles web searches, deep research, and complex questions
   - No new tokens required!

### Usage Notes
- The DuckDuckGo search has rate limits, so avoid rapid consecutive searches
- Deep research tool searches from multiple angles to provide comprehensive results
- Research results include source citations for verification