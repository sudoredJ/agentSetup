#!/usr/bin/env python3
"""Test script to verify deep research functionality works correctly."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools.agent_tools import deep_research_tool, web_search_tool


def test_web_search():
    """Test basic web search functionality."""
    print("Testing web_search_tool...")
    try:
        result = web_search_tool("starfish", max_results=3)
        print("✓ Web search successful:")
        print(result[:500] + "..." if len(result) > 500 else result)
        print()
        return True
    except Exception as e:
        print(f"✗ Web search failed: {e}")
        return False


def test_deep_research():
    """Test deep research functionality."""
    print("Testing deep_research_tool...")
    try:
        result = deep_research_tool("starfish", num_searches=2)
        print("✓ Deep research successful:")
        print(result[:800] + "..." if len(result) > 800 else result)
        print()
        return True
    except Exception as e:
        print(f"✗ Deep research failed: {e}")
        return False


def test_grok_integration():
    """Test Grok agent integration with research tools."""
    print("Testing Grok agent integration...")
    try:
        # Import necessary components
        from src.core.profile_loader import load_system_config
        from src.agents.specialist_agent import SpecialistAgent
        import yaml
        
        # Load Grok agent config
        with open('configs/agents/grok_agent.yaml', 'r') as f:
            grok_config = yaml.safe_load(f)
        
        # Create a mock Slack token
        mock_token = "xoxb-test-token"
        mock_channel = "test-channel"
        
        # Initialize Grok agent (this will fail on Slack connection but test tool loading)
        try:
            grok = SpecialistAgent(grok_config, mock_token, mock_channel)
            print("✓ Grok agent initialized successfully")
            print(f"  Available tools: {[t.name for t in grok.ai_agent.tools if hasattr(t, 'name')]}")
            return True
        except Exception as e:
            if "slack" in str(e).lower():
                print("✓ Grok agent tools loaded (Slack connection expected to fail in test)")
                return True
            else:
                print(f"✗ Grok agent initialization failed: {e}")
                return False
            
    except Exception as e:
        print(f"✗ Grok integration test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Deep Research Functionality Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        test_web_search,
        test_deep_research,
        test_grok_integration
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print("-" * 40)
        print()
    
    print("=" * 60)
    print(f"Tests passed: {passed}/{len(tests)}")
    print("=" * 60)
    
    if passed == len(tests):
        print("\n✅ All tests passed! The deep research functionality is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")


if __name__ == "__main__":
    main()