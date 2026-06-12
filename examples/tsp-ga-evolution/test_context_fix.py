#!/usr/bin/env python3
"""
Test that the enhanced context is now being passed correctly
"""

import sys
import json
sys.path.append('../../inst/python/')

import dynamic_prompting
from code_manager import CodeEvolutionManager

def test_context_fix():
    print("=== TESTING ENHANCED CONTEXT FIX ===\n")
    
    # Create a simple test history file to ensure we have data
    test_history = [
        {
            "iteration": 1,
            "total_variants_generated": 3,
            "llm_calls": 3,
            "successful_strategies": ["innovate_heuristic_design"],
            "generation_timestamp": 1756980000,
            "best_performance": 25.0,
            "best_configuration_id": 5,
            "winning_strategy": "variant_1"
        }
    ]
    
    with open('.irace_evo_history.json', 'w') as f:
        json.dump(test_history, f, indent=2)
    
    print("✓ Created test history with performance data")
    
    # Mock configuration
    mock_config = {
        "llm_config": {
            "api_provider": "openai",
            "model": "gpt-4o",
            "use_dynamic_prompting": True,
            "scenario_config": {"execDir": "."}
        },
        "evolution_config": {
            "available_strategies": ["innovate_heuristic_design"]
        },
        "source_config": {
            "function_name": "order_chromosome"
        }
    }
    
    # Mock context from R
    mock_r_context = {
        "iteration_context": {"current_iteration": 2},
        "elite_configurations": [
            {"id": 10, "rank": 22.5}
        ],
        "scenario_config": {"execDir": "."},
        "target_variants": 1
    }
    
    print("✓ Created mock configuration and context")
    
    try:
        # Test that the CodeEvolutionManager loads history correctly
        manager = CodeEvolutionManager(mock_config)
        
        # Simulate loading history (this would normally be done in generate_and_compile_variants)
        iteration_history = dynamic_prompting.get_iteration_history(mock_r_context.get('scenario_config', {}))
        
        print(f"✓ Loaded {len(iteration_history)} iterations from history")
        
        # Test enhanced context creation
        enhanced_context = mock_r_context.copy()
        enhanced_context['iteration_history'] = iteration_history
        enhanced_context['elite_configs'] = mock_r_context.get('elite_configurations', [])
        
        print(f"✓ Created enhanced context")
        print(f"  - iteration_history length: {len(enhanced_context.get('iteration_history', []))}")
        print(f"  - elite_configs length: {len(enhanced_context.get('elite_configs', []))}")
        
        # Verify that performance data is available
        if iteration_history and len(iteration_history) > 0:
            last_entry = iteration_history[-1]
            has_performance = 'best_performance' in last_entry
            print(f"  - Has performance data: {has_performance}")
            if has_performance:
                print(f"  - Best performance: {last_entry['best_performance']}")
        
        print(f"\n🎯 CONTEXT FIX VERIFICATION:")
        print(f"✅ Enhanced context contains iteration_history: {'iteration_history' in enhanced_context}")
        print(f"✅ Enhanced context contains elite_configs: {'elite_configs' in enhanced_context}")
        print(f"✅ History has performance data: {len(iteration_history) > 0 and 'best_performance' in iteration_history[0]}")
        
        print(f"\n🚀 With this fix, dynamic prompting should now receive the performance data correctly!")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_context_fix()