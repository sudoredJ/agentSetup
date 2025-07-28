#!/usr/bin/env python3
"""Debug script to test deep research tool functionality."""

import sys
import os
import traceback

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_direct_import():
    """Test importing duckduckgo_search directly."""
    print("1. Testing direct import of duckduckgo_search...")
    try:
        from duckduckgo_search import DDGS
        print("✓ Successfully imported DDGS")
        
        # Test basic search
        print("\n2. Testing basic search...")
        with DDGS() as ddgs:
            results = list(ddgs.text("starfish", max_results=2))
            print(f"✓ Found {len(results)} results")
            for i, r in enumerate(results):
                print(f"   Result {i+1}: {r.get('title', 'No title')}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        traceback.print_exc()
        return False


def test_deep_research_tool():
    """Test the deep_research_tool function."""
    print("\n3. Testing deep_research_tool...")
    try:
        from src.tools.agent_tools import deep_research_tool
        print("✓ Successfully imported deep_research_tool")
        
        print("\n4. Executing deep research on 'starfish'...")
        result = deep_research_tool("starfish", num_searches=2)
        
        if "ERROR" in result:
            print(f"✗ Tool returned error: {result}")
            return False
        else:
            print("✓ Deep research completed successfully")
            print(f"   Result length: {len(result)} characters")
            print(f"   First 200 chars: {result[:200]}...")
            return True
            
    except Exception as e:
        print(f"✗ Error in deep_research_tool: {e}")
        traceback.print_exc()
        return False


def test_web_search_tool():
    """Test the web_search_tool function."""
    print("\n5. Testing web_search_tool...")
    try:
        from src.tools.agent_tools import web_search_tool
        print("✓ Successfully imported web_search_tool")
        
        result = web_search_tool("starfish", max_results=2)
        
        if "ERROR" in result:
            print(f"✗ Tool returned error: {result}")
            return False
        else:
            print("✓ Web search completed successfully")
            print(f"   Result length: {len(result)} characters")
            return True
            
    except Exception as e:
        print(f"✗ Error in web_search_tool: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Deep Research Tool Debug")
    print("=" * 60)
    
    # Check Python version
    print(f"\nPython version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    
    tests = [
        test_direct_import,
        test_deep_research_tool,
        test_web_search_tool
    ]
    
    passed = 0
    for test in tests:
        print("\n" + "-" * 40)
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"Tests passed: {passed}/{len(tests)}")
    
    if passed < len(tests):
        print("\n⚠️  Some tests failed. Check the error messages above.")
        print("\nPossible solutions:")
        print("1. Ensure duckduckgo-search is installed: pip install duckduckgo-search")
        print("2. Check for version conflicts")
        print("3. Try upgrading: pip install --upgrade duckduckgo-search")


if __name__ == "__main__":
    main()