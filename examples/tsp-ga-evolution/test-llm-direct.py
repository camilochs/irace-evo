#!/usr/bin/env python3
"""
Test script to directly test LLM functionality without running irace
"""

import sys
import os
import json

# Add the irace Python modules to path
sys.path.insert(0, '/home/camilocs/R/x86_64-pc-linux-gnu-library/4.1/irace/python')

from code_manager import CodeEvolutionManager

def test_llm_generation():
    """Test LLM generation directly"""
    
    # Load configuration
    with open('code-evolution.json', 'r') as f:
        config = json.load(f)
    
    # Set API key
    if config.get('llm_config', {}).get('api_key'):
        os.environ['OPENAI_API_KEY'] = config['llm_config']['api_key']
    
    # Create manager
    manager = CodeEvolutionManager(config)
    
    # Create a simple test context (simulating iteration 2 with some performance data)
    test_context = {
        'target_variants': 2,
        'iteration_context': {
            'current_iteration': 2,
            'total_iterations': 5,
            'previous_best_cost': 1500.0
        },
        'performance_stats': {
            'best_configuration_cost': 1500.0,
            'worst_configuration_cost': 2000.0,
            'median_cost': 1750.0,
            'cost_improvement': 0.15
        },
        'improvement_guidance': {
            'focus_areas': ['efficiency', 'heuristics'],
            'bottlenecks': ['decode_solution function complexity']
        }
    }
    
    print("="*60)
    print("TESTING LLM CODE GENERATION")
    print("="*60)
    print(f"Using strategy: {list(manager.strategies.keys())}")
    print(f"Target variants: {test_context['target_variants']}")
    print()
    
    try:
        # Generate variants
        variants, metrics = manager.generate_and_compile_variants(test_context)
        
        print("="*60)
        print("RESULTS")
        print("="*60)
        print(f"Generated variants: {len(variants)}")
        print(f"LLM calls: {metrics['total_calls']}")
        print(f"Total cost: ${metrics['total_cost_estimate']:.3f}")
        print()
        
        for i, variant in enumerate(variants):
            print(f"Variant {i+1}:")
            print(f"  - ID: {variant['variant_id']}")
            print(f"  - Strategy: {variant['strategy']}")
            print(f"  - Compiled: {variant['compilation_success']}")
            if variant['compilation_success']:
                print(f"  - Executable: {variant['executable']}")
            else:
                print(f"  - Errors: {variant['compilation_errors']}")
            print()
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm_generation()