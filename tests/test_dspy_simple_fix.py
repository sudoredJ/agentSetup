#!/usr/bin/env python3
"""Simple test to verify DSPy is working with LM fixes."""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_dspy_basic():
    """Test basic DSPy functionality."""
    print("🧠 Testing basic DSPy functionality...")
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
        
        # Check if components are initialized
        checks = []
        checks.append(("LM initialized", agent.lm is not None))
        checks.append(("Tool selector exists", hasattr(agent, 'tool_selector')))
        checks.append(("System prompt set", hasattr(agent, 'system_prompt')))
        checks.append(("Beautiful search available", hasattr(agent, 'beautiful_search')))
        
        print("✅ DSPy Agent Components:")
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"  {status} {check_name}: {result}")
        
        # Test forward method
        try:
            result = agent.forward("Hello, can you help me?")
            print(f"✅ Forward method works: {str(result)[:100]}...")
            checks.append(("Forward method", True))
        except Exception as e:
            print(f"❌ Forward method failed: {e}")
            checks.append(("Forward method", False))
        
        # Summary
        passed = sum(1 for _, result in checks if result)
        total = len(checks)
        print(f"\n🎯 DSPy Basic Test: {passed}/{total} checks passed")
        
        return passed == total
        
    except Exception as e:
        print(f"❌ DSPy basic test failed: {e}")
        return False

def test_grok_dspy_basic():
    """Test basic Grok DSPy functionality."""
    print("\n🤖 Testing basic Grok DSPy functionality...")
    try:
        from agents.dspy_modules import GrokDSPyAgent
        
        # Create test tools
        def web_search_tool(query: str, max_results: int = 5) -> str:
            return f"Web search results for '{query}' (simulated)"
        web_search_tool.name = "web_search_tool"
        
        # Initialize Grok DSPy agent
        grok = GrokDSPyAgent(
            tools=[web_search_tool],
            model_id="claude-3-haiku-20240307",
            system_prompt="You are Grok, a research specialist."
        )
        
        # Check if components are initialized
        checks = []
        checks.append(("LM initialized", grok.lm is not None))
        checks.append(("Research module exists", hasattr(grok, 'research_module')))
        checks.append(("Tool selector exists", hasattr(grok, 'tool_selector')))
        checks.append(("System prompt set", hasattr(grok, 'system_prompt')))
        
        print("✅ Grok DSPy Agent Components:")
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"  {status} {check_name}: {result}")
        
        # Test forward method
        try:
            result = grok.forward("Research artificial intelligence")
            print(f"✅ Grok forward method works: {str(result)[:100]}...")
            checks.append(("Forward method", True))
        except Exception as e:
            print(f"❌ Grok forward method failed: {e}")
            checks.append(("Forward method", False))
        
        # Summary
        passed = sum(1 for _, result in checks if result)
        total = len(checks)
        print(f"\n🎯 Grok DSPy Basic Test: {passed}/{total} checks passed")
        
        return passed == total
        
    except Exception as e:
        print(f"❌ Grok DSPy basic test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Simple DSPy Integration Test\n")
    
    test1 = test_dspy_basic()
    test2 = test_grok_dspy_basic()
    
    print(f"\n📊 Final Results:")
    print(f"{'='*50}")
    print(f"DSPy Basic Test:     {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Grok DSPy Basic Test: {'✅ PASS' if test2 else '❌ FAIL'}")
    
    if test1 and test2:
        print(f"\n🎉 All tests passed! DSPy is working correctly.")
        print("The system should now use DSPy reasoning instead of falling back.")
    else:
        print(f"\n⚠️ Some tests failed. DSPy may still have issues.") 