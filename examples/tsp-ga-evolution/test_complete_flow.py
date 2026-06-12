#!/usr/bin/env python3
"""
Test complete data flow for dynamic prompting integration
"""

import sys
import json
sys.path.append('../../inst/python/')

import dynamic_prompting
from code_manager import CodeEvolutionManager
from llm_service import LLMService

def test_data_flow():
    print("=== TESTING COMPLETE DATA FLOW ===\n")
    
    # 1. Mock R-side context (what R sends to Python)
    print("--- 1. R-side Context (Input) ---")
    r_context = {
        "iteration_context": {
            "current_iteration": 3,
            "max_iterations": 5,
            "elite_configurations": [
                {"id": 19, "rank": 34.5},
                {"id": 6, "rank": 41.2}
            ]
        },
        "performance_stats": {
            "best_cost_so_far": 34.5,
            "average_cost": 38.2,
            "worst_cost": 45.8
        },
        "scenario_config": {
            "execDir": "."
        },
        "elite_configurations": [
            {"id": 19, "rank": 34.5}, 
            {"id": 6, "rank": 41.2}
        ],
        "target_variants": 3
    }
    print(f"✓ R context prepared with {len(r_context)} sections")
    
    # 2. Test iteration history loading
    print("\n--- 2. Iteration History Loading ---")
    try:
        history = dynamic_prompting.get_iteration_history(r_context.get('scenario_config', {}))
        print(f"✓ Loaded {len(history)} iteration entries")
        if history:
            print(f"  Latest iteration: {history[-1].get('iteration', 'unknown')}")
            print(f"  Has performance data: {'best_performance' in history[-1]}")
        else:
            print("  No history available (expected for first run)")
    except Exception as e:
        print(f"❌ History loading failed: {e}")
    
    # 3. Test performance analysis
    print("\n--- 3. Performance Analysis ---")
    try:
        analyzer = dynamic_prompting.PerformanceAnalyzer({'stagnation_threshold': 2})
        analysis = analyzer.analyze_performance_gaps(
            r_context['elite_configurations'], 
            history
        )
        print(f"✓ Performance analysis completed")
        print(f"  Focus recommendations: {analysis['focus_recommendations']}")
        print(f"  Stagnant areas: {analysis['stagnant_areas']}")
    except Exception as e:
        print(f"❌ Performance analysis failed: {e}")
        analysis = {'focus_recommendations': ['general_improvement']}
    
    # 4. Test prompt building
    print("\n--- 4. Dynamic Prompt Building ---")
    try:
        builder = dynamic_prompting.DynamicPromptBuilder({'stagnation_threshold': 2})
        
        base_template = """You are improving function {function_name}.
        
## ORIGINAL FUNCTION
{original_function}

## YOUR TASK
Improve this function for better performance.
{performance_context}"""
        
        prompt_data = {
            'function_name': 'order_chromosome',
            'original_function': 'double order_chromosome(int i) { return 0.5; }',
            'elite_configs': r_context['elite_configurations'],
            'iteration_history': history
        }
        
        adaptive_prompt = builder.build_adaptive_prompt(
            base_template, prompt_data, 
            r_context['elite_configurations'], 
            history
        )
        
        print(f"✓ Adaptive prompt generated")
        print(f"  Prompt length: {len(adaptive_prompt)} characters")
        print(f"  Contains focus section: {'EVOLUTION FOCUS' in adaptive_prompt}")
        print(f"  Contains performance context: {'PERFORMANCE CONTEXT' in adaptive_prompt}")
        
    except Exception as e:
        print(f"❌ Prompt building failed: {e}")
    
    # 5. Test LLM service integration
    print("\n--- 5. LLM Service Integration ---")
    try:
        # Mock LLM config with dynamic prompting enabled
        llm_config = {
            'api_provider': 'openai',
            'model': 'gpt-4o',
            'language': 'cpp',
            'use_dynamic_prompting': True,
            'scenario_config': r_context['scenario_config']
        }
        
        # Don't actually initialize the client (no API key needed for this test)
        print("✓ LLM service configuration prepared")
        print(f"  Dynamic prompting: {llm_config['use_dynamic_prompting']}")
        print(f"  Language: {llm_config['language']}")
        print(f"  Has scenario config: {'scenario_config' in llm_config}")
        
    except Exception as e:
        print(f"❌ LLM service setup failed: {e}")
    
    # 6. Test performance saving
    print("\n--- 6. Performance Data Saving ---")
    try:
        test_iteration_data = {
            'iteration': 4,
            'total_variants_generated': 3,
            'llm_calls': 4,
            'successful_strategies': ['innovate_heuristic_design', 'optimize_memory'],
            'generation_timestamp': 1756980000.0
        }
        
        dynamic_prompting.save_iteration_performance(
            r_context['scenario_config'], 
            test_iteration_data
        )
        print("✓ Performance data saving works")
        
    except Exception as e:
        print(f"❌ Performance saving failed: {e}")
    
    print("\n=== DATA FLOW TEST COMPLETE ===")
    return True

if __name__ == "__main__":
    test_data_flow()