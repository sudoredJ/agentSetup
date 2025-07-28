#!/usr/bin/env python3
"""Test script to validate DSPy tool selection."""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules
from src.agents.dspy_modules import ensure_dspy_configured, GrokDSPyAgent
from src.tools.search.agent_tools import web_search_tool, deep_research_tool
from src.tools.external.weather_tools import get_current_weather, get_sunrise_sunset

def test_tool_selection():
    """Test DSPy tool selection with various queries."""
    # Ensure DSPy is configured
    ensure_dspy_configured()
    
    # Create a minimal set of tools
    tools = [
        web_search_tool,
        deep_research_tool,
        get_current_weather,
        get_sunrise_sunset
    ]
    
    # Create GrokDSPyAgent
    agent = GrokDSPyAgent(
        tools=tools,
        model_id="claude-3-haiku-20240307",
        system_prompt="You are Grok, a helpful AI assistant."
    )
    
    # Test queries
    test_queries = [
        "what is temperature",
        "what time is the sunset",
        "weather in Boston",
        "research quantum computing"
    ]
    
    print("\n=== Testing Tool Selection ===\n")
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        try:
            result = agent.forward(query)
            print(f"Result: {result[:200]}...")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_tool_selection()