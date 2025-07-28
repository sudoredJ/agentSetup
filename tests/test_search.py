#!/usr/bin/env python3
"""Test script for improved search functionality."""

import logging
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

def test_web_search():
    """Test the web search tool."""
    print("🔍 Testing web search tool...")
    try:
        from tools.agent_tools import web_search_tool
        result = web_search_tool("python programming", 2)
        print(f"✅ Web search result: {result[:200]}...")
        return True
    except Exception as e:
        print(f"❌ Web search failed: {e}")
        return False

def test_deep_research():
    """Test the deep research tool."""
    print("🔬 Testing deep research tool...")
    try:
        from tools.agent_tools import deep_research_tool
        result = deep_research_tool("starfish", 2)
        print(f"✅ Deep research result: {result[:200]}...")
        return True
    except Exception as e:
        print(f"❌ Deep research failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing improved search functionality...\n")
    
    web_success = test_web_search()
    print()
    deep_success = test_deep_research()
    
    print(f"\n📊 Test Results:")
    print(f"   Web Search: {'✅ PASS' if web_success else '❌ FAIL'}")
    print(f"   Deep Research: {'✅ PASS' if deep_success else '❌ FAIL'}")
    
    if web_success and deep_success:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed. Check the logs above for details.") 