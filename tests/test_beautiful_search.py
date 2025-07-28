#!/usr/bin/env python3
"""Test script for BeautifulSoup-based search system."""

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
    print("🔍 Testing BeautifulSoup web search tool...")
    try:
        from tools.agent_tools import web_search_tool
        result = web_search_tool("python programming", 3)
        print(f"✅ Web search result: {result[:300]}...")
        return True
    except Exception as e:
        print(f"❌ Web search failed: {e}")
        return False

def test_deep_research():
    """Test the deep research tool."""
    print("🔬 Testing BeautifulSoup deep research tool...")
    try:
        from tools.agent_tools import deep_research_tool
        result = deep_research_tool("starfish", 2)
        print(f"✅ Deep research result: {result[:300]}...")
        return True
    except Exception as e:
        print(f"❌ Deep research failed: {e}")
        return False

def test_fetch_summarize():
    """Test the fetch and summarize tool."""
    print("📄 Testing fetch and summarize tool...")
    try:
        from tools.agent_tools import fetch_and_summarize_tool
        result = fetch_and_summarize_tool("https://en.wikipedia.org/wiki/Python_(programming_language)")
        print(f"✅ Fetch and summarize result: {result[:300]}...")
        return True
    except Exception as e:
        print(f"❌ Fetch and summarize failed: {e}")
        return False

def test_beautiful_search_direct():
    """Test the BeautifulSearch class directly."""
    print("🌐 Testing BeautifulSearch class directly...")
    try:
        from tools.beautiful_search import beautiful_search
        
        # Test Google search
        print("  Testing Google search...")
        google_results = beautiful_search.search_google("python programming", 2)
        print(f"    Google found {len(google_results)} results")
        
        # Test Wikipedia search
        print("  Testing Wikipedia search...")
        wiki_results = beautiful_search.search_wikipedia("python programming", 2)
        print(f"    Wikipedia found {len(wiki_results)} results")
        
        # Test combined search
        print("  Testing combined search...")
        combined_results = beautiful_search.search_with_fallbacks("python programming", 3)
        print(f"    Combined search found {len(combined_results)} results")
        
        return True
    except Exception as e:
        print(f"❌ BeautifulSearch direct test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing BeautifulSoup-based search system...\n")
    
    web_success = test_web_search()
    print()
    deep_success = test_deep_research()
    print()
    fetch_success = test_fetch_summarize()
    print()
    direct_success = test_beautiful_search_direct()
    
    print(f"\n📊 Test Results:")
    print(f"   Web Search: {'✅ PASS' if web_success else '❌ FAIL'}")
    print(f"   Deep Research: {'✅ PASS' if deep_success else '❌ FAIL'}")
    print(f"   Fetch & Summarize: {'✅ PASS' if fetch_success else '❌ FAIL'}")
    print(f"   Direct BeautifulSearch: {'✅ PASS' if direct_success else '❌ FAIL'}")
    
    all_passed = web_success and deep_success and fetch_success and direct_success
    if all_passed:
        print("\n🎉 All tests passed! BeautifulSoup system is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the logs above for details.") 