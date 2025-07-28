#!/usr/bin/env python3
"""Benchmark script for BeautifulSoup search system performance."""

import time
import logging
import sys
import os
from statistics import mean, median

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce logging noise during benchmarks
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

def benchmark_search_method(method_name, method_func, query, max_results=3):
    """Benchmark a single search method."""
    times = []
    result_counts = []
    
    print(f"  Benchmarking {method_name}...")
    
    for i in range(3):  # Run 3 times for average
        try:
            start_time = time.time()
            results = method_func(query, max_results)
            end_time = time.time()
            
            duration = end_time - start_time
            times.append(duration)
            result_counts.append(len(results))
            
            print(f"    Run {i+1}: {duration:.2f}s, {len(results)} results")
            
            # Small delay between runs
            time.sleep(1)
            
        except Exception as e:
            print(f"    Run {i+1}: ERROR - {e}")
            times.append(float('inf'))
            result_counts.append(0)
    
    return {
        'method': method_name,
        'avg_time': mean(times) if times else 0,
        'median_time': median(times) if times else 0,
        'min_time': min(times) if times else 0,
        'max_time': max(times) if times else 0,
        'avg_results': mean(result_counts) if result_counts else 0,
        'success_rate': len([t for t in times if t != float('inf')]) / len(times) if times else 0
    }

def run_benchmarks():
    """Run comprehensive benchmarks."""
    print("🚀 BeautifulSoup Search System Benchmark\n")
    
    try:
        from tools.beautiful_search import beautiful_search
        
        # Test queries
        test_queries = [
            "python programming",
            "machine learning",
            "artificial intelligence"
        ]
        
        all_results = []
        
        for query in test_queries:
            print(f"📊 Testing query: '{query}'\n")
            
            # Test individual engines
            engines = {
                'Google': beautiful_search.search_google,
                'Bing': beautiful_search.search_bing,
                'Wikipedia': beautiful_search.search_wikipedia,
                'DuckDuckGo': beautiful_search.search_duckduckgo
            }
            
            query_results = []
            
            for engine_name, engine_func in engines.items():
                result = benchmark_search_method(engine_name, engine_func, query, 3)
                query_results.append(result)
                print()
            
            # Test combined search
            print("  Benchmarking Combined Search...")
            combined_result = benchmark_search_method("Combined", beautiful_search.search_with_fallbacks, query, 5)
            query_results.append(combined_result)
            
            all_results.extend(query_results)
            print(f"  {'='*50}\n")
        
        # Print summary
        print("📈 BENCHMARK SUMMARY\n")
        print(f"{'Method':<15} {'Avg Time':<10} {'Success Rate':<12} {'Avg Results':<12}")
        print("-" * 55)
        
        # Group by method
        method_stats = {}
        for result in all_results:
            method = result['method']
            if method not in method_stats:
                method_stats[method] = []
            method_stats[method].append(result)
        
        for method, results in method_stats.items():
            avg_time = mean([r['avg_time'] for r in results])
            avg_success = mean([r['success_rate'] for r in results])
            avg_results = mean([r['avg_results'] for r in results])
            
            print(f"{method:<15} {avg_time:<10.2f} {avg_success:<12.1%} {avg_results:<12.1f}")
        
        print(f"\n✅ Benchmark completed successfully!")
        print(f"📊 Total tests: {len(all_results)}")
        print(f"🎯 Average success rate: {mean([r['success_rate'] for r in all_results]):.1%}")
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")

if __name__ == "__main__":
    run_benchmarks() 