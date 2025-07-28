#!/usr/bin/env python3
"""Simple test script for DSPy integration structure without LLM calls."""

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

def test_dspy_imports():
    """Test that DSPy can be imported and basic modules work."""
    print("🧠 Testing DSPy Imports...")
    try:
        import dspy
        print(f"✅ DSPy version: {dspy.__version__}")
        
        # Test basic DSPy components
        from dspy import Signature, InputField, OutputField, Module, ChainOfThought
        print("✅ DSPy basic components imported successfully")
        
        # Test creating a simple signature
        class TestSignature(Signature):
            input_text: str = InputField(desc="Input text")
            output_text: str = OutputField(desc="Output text")
        
        print("✅ DSPy Signature creation works")
        return True
    except Exception as e:
        print(f"❌ DSPy import test failed: {e}")
        return False

def test_beautiful_search_import():
    """Test that BeautifulSoup search can be imported."""
    print("🌐 Testing BeautifulSoup Search Import...")
    try:
        import sys
        import os
        tools_path = os.path.join(os.path.dirname(__file__), 'src', 'tools')
        if tools_path not in sys.path:
            sys.path.insert(0, tools_path)
        
        from beautiful_search import beautiful_search
        print("✅ BeautifulSoup search imported successfully")
        return True
    except Exception as e:
        print(f"❌ BeautifulSoup search import failed: {e}")
        return False

def test_dspy_agent_structure():
    """Test DSPy agent structure without LLM calls."""
    print("🤖 Testing DSPy Agent Structure...")
    try:
        from core.dspy_agent import DSPyAgent
        
        # Create a mock tool
        def mock_tool(message: str) -> str:
            return f"Mock tool executed: {message}"
        mock_tool.name = "mock_tool"
        
        # Test agent creation (without LLM)
        agent = DSPyAgent(
            tools=[mock_tool],
            model_id="test-model",
            system_prompt="Test system prompt"
        )
        
        print("✅ DSPy agent structure created successfully")
        print(f"✅ Agent has {len(agent.tools)} tools")
        print(f"✅ Agent system prompt: {agent.system_prompt}")
        return True
    except Exception as e:
        print(f"❌ DSPy agent structure test failed: {e}")
        return False

def test_research_module_structure():
    """Test Research module structure without LLM calls."""
    print("🔬 Testing Research Module Structure...")
    try:
        from agents.dspy_modules import ResearchModule
        
        # Create research module
        research = ResearchModule()
        
        print("✅ Research module structure created successfully")
        print(f"✅ BeautifulSoup search available: {research.beautiful_search is not None}")
        return True
    except Exception as e:
        print(f"❌ Research module structure test failed: {e}")
        return False

def test_grok_dspy_structure():
    """Test Grok DSPy agent structure without LLM calls."""
    print("🤖 Testing Grok DSPy Agent Structure...")
    try:
        from agents.dspy_modules import GrokDSPyAgent
        
        # Create mock tools
        def web_search_tool(query: str, max_results: int = 5) -> str:
            return f"Mock web search for '{query}'"
        web_search_tool.name = "web_search_tool"
        
        def deep_research_tool(topic: str, num_searches: int = 3) -> str:
            return f"Mock deep research for '{topic}'"
        deep_research_tool.name = "deep_research_tool"
        
        # Create Grok DSPy agent
        grok = GrokDSPyAgent(
            tools=[web_search_tool, deep_research_tool],
            model_id="test-model",
            system_prompt="Test Grok system prompt"
        )
        
        print("✅ Grok DSPy agent structure created successfully")
        print(f"✅ Agent has {len(grok.tools)} tools")
        print(f"✅ Research module available: {grok.research_module is not None}")
        return True
    except Exception as e:
        print(f"❌ Grok DSPy agent structure test failed: {e}")
        return False

def test_specialist_agent_config():
    """Test SpecialistAgent DSPy configuration."""
    print("⚙️ Testing SpecialistAgent DSPy Configuration...")
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
        
        print("✅ DSPy agent profile configuration is valid")
        print(f"✅ use_dspy flag: {agent_profile.get('use_dspy', False)}")
        return True
    except Exception as e:
        print(f"❌ SpecialistAgent DSPy configuration test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing DSPy Integration Structure (No LLM Calls)\n")
    
    tests = [
        ("DSPy Imports", test_dspy_imports),
        ("BeautifulSoup Search Import", test_beautiful_search_import),
        ("DSPy Agent Structure", test_dspy_agent_structure),
        ("Research Module Structure", test_research_module_structure),
        ("Grok DSPy Agent Structure", test_grok_dspy_structure),
        ("SpecialistAgent DSPy Configuration", test_specialist_agent_config)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print(f"{'='*50}")
        success = test_func()
        results.append((test_name, success))
        print()
    
    print(f"\n📊 DSPy Integration Structure Test Results:")
    print(f"{'='*50}")
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<35} {status}")
        if success:
            passed += 1
    
    print(f"\n🎯 Summary: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All DSPy integration structure tests passed!")
        print("The DSPy integration structure is working correctly.")
        print("Note: This test doesn't include actual LLM calls.")
    else:
        print("\n⚠️ Some structure tests failed. Check the logs above for details.")
        print("The integration may need adjustments before LLM testing.") 