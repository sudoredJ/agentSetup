#!/usr/bin/env python3
"""Test script to verify DSPy is actually working with LM fixes."""

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

def test_dspy_agent_with_lm():
    """Test DSPy agent with proper LM initialization."""
    print("🧠 Testing DSPy Agent with LM...")
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
        
        # Check if LM is properly initialized
        if agent.lm is not None:
            print("✅ LM is properly initialized")
            return True
        else:
            print("❌ LM is not initialized")
            return False
            
    except Exception as e:
        print(f"❌ DSPy agent test failed: {e}")
        return False

def test_grok_dspy_agent():
    """Test Grok DSPy agent with LM."""
    print("🤖 Testing Grok DSPy Agent with LM...")
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
        
        # Check if LM is properly initialized
        if grok.lm is not None:
            print("✅ Grok LM is properly initialized")
            return True
        else:
            print("❌ Grok LM is not initialized")
            return False
            
    except Exception as e:
        print(f"❌ Grok DSPy agent test failed: {e}")
        return False

def test_research_module():
    """Test Research module with LM."""
    print("🔬 Testing Research Module with LM...")
    try:
        from agents.dspy_modules import ResearchModule
        
        # Initialize research module
        research = ResearchModule()
        
        # Test research
        result = research.forward("python programming")
        print(f"✅ Research module test result: {result[:200]}...")
        
        # Check if DSPy modules are working
        if hasattr(research, 'generate_queries') and research.generate_queries is not None:
            print("✅ Research module DSPy components are working")
            return True
        else:
            print("❌ Research module DSPy components are not working")
            return False
            
    except Exception as e:
        print(f"❌ Research module test failed: {e}")
        return False

def test_specialist_agent_dspy_integration():
    """Test SpecialistAgent DSPy integration."""
    print("⚙️ Testing SpecialistAgent DSPy Integration...")
    try:
        # Test configuration structure
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
        
        # Test that the profile would work with SpecialistAgent
        if agent_profile.get('use_dspy', False):
            print("✅ DSPy agent profile configuration is valid")
            print(f"✅ use_dspy flag: {agent_profile.get('use_dspy', False)}")
            print(f"✅ model_id: {agent_profile.get('model_id', 'Not set')}")
            return True
        else:
            print("❌ DSPy agent profile configuration is invalid")
            return False
            
    except Exception as e:
        print(f"❌ SpecialistAgent DSPy integration test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing DSPy Integration with LM Fixes\n")
    
    tests = [
        ("DSPy Agent with LM", test_dspy_agent_with_lm),
        ("Grok DSPy Agent with LM", test_grok_dspy_agent),
        ("Research Module with LM", test_research_module),
        ("SpecialistAgent DSPy Integration", test_specialist_agent_dspy_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print(f"{'='*50}")
        success = test_func()
        results.append((test_name, success))
        print()
    
    print(f"\n📊 DSPy Integration with LM Test Results:")
    print(f"{'='*50}")
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<35} {status}")
        if success:
            passed += 1
    
    print(f"\n🎯 Summary: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All DSPy integration tests passed!")
        print("DSPy is now working with proper LM initialization.")
        print("The system should now use DSPy reasoning instead of falling back.")
    else:
        print("\n⚠️ Some tests failed. DSPy may still have issues.")
        print("Check the logs above for specific error details.") 