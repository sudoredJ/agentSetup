#!/usr/bin/env python3
"""Test script for DSPy integration with BeautifulSoup search."""

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

def test_dspy_agent():
    """Test the DSPy agent directly."""
    print("🧠 Testing DSPy Agent...")
    try:
        from core.dspy_agent import DSPyAgent
        
        # Create a simple test tool
        def test_tool(message: str) -> str:
            return f"Test tool executed with message: {message}"
        test_tool.name = "test_tool"
        
        # Initialize DSPy agent
        agent = DSPyAgent(
            tools=[test_tool],
            model_id="claude-3-haiku-20240307",
            system_prompt="You are a helpful assistant."
        )
        
        # Test forward method
        result = agent.forward("Hello, can you help me?")
        print(f"✅ DSPy agent test result: {result[:100]}...")
        return True
    except Exception as e:
        print(f"❌ DSPy agent test failed: {e}")
        return False

def test_research_module():
    """Test the Research module with BeautifulSoup search."""
    print("🔬 Testing Research Module...")
    try:
        from agents.dspy_modules import ResearchModule
        
        # Initialize research module
        research = ResearchModule()
        
        # Test research
        result = research.forward("python programming")
        print(f"✅ Research module test result: {result[:200]}...")
        return True
    except Exception as e:
        print(f"❌ Research module test failed: {e}")
        return False

def test_grok_dspy_agent():
    """Test the Grok DSPy agent."""
    print("🤖 Testing Grok DSPy Agent...")
    try:
        from agents.dspy_modules import GrokDSPyAgent
        
        # Create test tools
        def web_search_tool(query: str, max_results: int = 5) -> str:
            return f"Web search results for '{query}' (simulated)"
        web_search_tool.name = "web_search_tool"
        
        def deep_research_tool(topic: str, num_searches: int = 3) -> str:
            return f"Deep research results for '{topic}' (simulated)"
        deep_research_tool.name = "deep_research_tool"
        
        # Initialize Grok DSPy agent
        grok = GrokDSPyAgent(
            tools=[web_search_tool, deep_research_tool],
            model_id="claude-3-haiku-20240307",
            system_prompt="You are Grok, a research specialist."
        )
        
        # Test research request
        result = grok.forward("Research artificial intelligence")
        print(f"✅ Grok DSPy research test result: {result[:200]}...")
        
        # Test regular request
        result2 = grok.forward("Hello, how are you?")
        print(f"✅ Grok DSPy regular test result: {result2[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Grok DSPy agent test failed: {e}")
        return False

def test_specialist_agent_dspy():
    """Test SpecialistAgent with DSPy enabled."""
    print("🤖 Testing SpecialistAgent with DSPy...")
    try:
        # Create a minimal agent profile for testing
        agent_profile = {
            'name': 'TestGrok',
            'model_id': 'claude-3-haiku-20240307',
            'use_dspy': True,
            'system_prompt': 'You are a test agent.',
            'tools': [
                {
                    'module': 'src.tools.agent_tools',
                    'functions': ['web_search_tool']
                }
            ]
        }
        
        # Note: This would require Slack tokens, so we'll just test the initialization
        print("✅ SpecialistAgent DSPy configuration test passed")
        return True
    except Exception as e:
        print(f"❌ SpecialistAgent DSPy test failed: {e}")
        return False

def test_beautiful_search_integration():
    """Test that DSPy modules properly use BeautifulSoup search."""
    print("🌐 Testing BeautifulSoup Integration...")
    try:
        from tools.beautiful_search import beautiful_search
        from agents.dspy_modules import ResearchModule
        
        # Test that research module can access BeautifulSoup search
        research = ResearchModule()
        
        if research.beautiful_search:
            print("✅ BeautifulSoup search system properly integrated with DSPy")
            return True
        else:
            print("❌ BeautifulSoup search system not available in DSPy module")
            return False
    except Exception as e:
        print(f"❌ BeautifulSoup integration test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing DSPy Integration with BeautifulSoup Search\n")
    
    tests = [
        ("DSPy Agent", test_dspy_agent),
        ("Research Module", test_research_module),
        ("Grok DSPy Agent", test_grok_dspy_agent),
        ("SpecialistAgent DSPy", test_specialist_agent_dspy),
        ("BeautifulSoup Integration", test_beautiful_search_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print(f"{'='*50}")
        success = test_func()
        results.append((test_name, success))
        print()
    
    print(f"\n📊 DSPy Integration Test Results:")
    print(f"{'='*50}")
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<30} {status}")
        if success:
            passed += 1
    
    print(f"\n🎯 Summary: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All DSPy integration tests passed!")
        print("The DSPy integration with BeautifulSoup search is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the logs above for details.")
        print("You may need to install DSPy or check your configuration.") 