#!/usr/bin/env python3
"""
Test only the LLM strategy without compilation
"""

import sys
import os
import json

# Add the irace Python modules to path
sys.path.insert(0, '/home/camilocs/R/x86_64-pc-linux-gnu-library/4.1/irace/python')

from llm_service import LLMService

def test_strategy_only():
    """Test only the LLM strategy generation"""
    
    # Load configuration
    with open('code-evolution.json', 'r') as f:
        config = json.load(f)
    
    # Set API key
    if config.get('llm_config', {}).get('api_key'):
        os.environ['OPENAI_API_KEY'] = config['llm_config']['api_key']
    
    # Create LLM service
    llm_config = config.get('llm_config', {})
    llm_config['language'] = 'cpp'
    llm_service = LLMService(llm_config)
    
    # Read original function
    with open('./src/brkga.cpp', 'r') as f:
        source_code = f.read()
    
    # Extract decode_solution function (simple extraction for test)
    start = source_code.find('set<int> decode_solution')
    if start == -1:
        print("ERROR: Could not find decode_solution function")
        return
    
    # Find the opening brace and count braces to get full function
    brace_start = source_code.find('{', start)
    if brace_start == -1:
        print("ERROR: Could not find function body")
        return
    
    brace_count = 1
    pos = brace_start + 1
    while pos < len(source_code) and brace_count > 0:
        if source_code[pos] == '{':
            brace_count += 1
        elif source_code[pos] == '}':
            brace_count -= 1
        pos += 1
    
    original_function = source_code[start:pos]
    
    print("="*60)
    print("TESTING LLM STRATEGY")
    print("="*60)
    print(f"Original function length: {len(original_function)} chars")
    print(f"Strategy: innovate_heuristic_design")
    print()
    
    # Extract context information (simulate)
    context_code = """// Data structures used in the algorithm:
struct Run {
    int start;
    int length;  // Use 'length', not 'end'
    double value;
};

// Global variables and constants:
vector<Run> runs;
int n_runs;
double threshold = 0.5;

// Required includes:
#include <vector>
#include <set>
#include <algorithm>"""
    
    # Create test prompt data
    prompt_data = {
        'original_function': original_function,
        'context_code': context_code,
        'full_context_mode': False,  # Test function-only mode
        'function_name': 'decode_solution',
        'strategy': 'innovate_heuristic_design',
        'strategy_context': {
            'name': 'innovate_heuristic_design',
            'description': 'Conceptualize and develop a novel heuristic for optimization',
            'prompt_context': 'Create innovative heuristics for better solution exploration'
        },
        'iteration_context': {
            'current_iteration': 2,
            'total_iterations': 5
        },
        'performance_stats': {
            'best_configuration_cost': 1500.0,
            'median_cost': 1750.0
        },
        'improvement_guidance': {
            'performance_gap': 0.15,
            'focus_areas': ['efficiency', 'heuristics'],
            'bottlenecks': ['decode_solution function complexity'],
            'suggestions': ['optimize run selection', 'reduce O(n²) operations']
        },
        'problem_context': config.get('problem_context', {}),
        'variant_number': 1,
        'previous_variants': []
    }
    
    try:
        print("Calling LLM service...")
        new_function = llm_service.generate_function_variant(prompt_data)
        
        print("="*60)
        print("LLM RESPONSE")
        print("="*60)
        print("Generated function:")
        print("-" * 40)
        print(new_function)
        print("-" * 40)
        print()
        print(f"New function length: {len(new_function)} chars")
        
        # Get metrics
        metrics = llm_service.get_metrics()
        print(f"LLM calls: {metrics['total_calls']}")
        print(f"Total cost: ${metrics['total_cost_estimate']:.3f}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_strategy_only()