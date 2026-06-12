#!/usr/bin/env python3
"""
Test dynamic prompting with actual performance data
"""

import sys
import json
sys.path.append('../../inst/python/')

import dynamic_prompting

def test_with_fixed_data():
    print("=== TESTING DYNAMIC PROMPTING WITH FIXED DATA ===\n")
    
    # Load the actual history file (now with performance data)
    try:
        history = dynamic_prompting.get_iteration_history({'execDir': '.'})
        print(f"✓ Loaded {len(history)} iterations from history")
        
        for i, entry in enumerate(history):
            print(f"  Iteration {entry.get('iteration', '?')}: best_performance = {entry.get('best_performance', 'missing')}")
        
        # Test performance analysis
        analyzer = dynamic_prompting.PerformanceAnalyzer({'stagnation_threshold': 2})
        
        # Mock elite configs
        elite_configs = [
            {'id': 10, 'rank': 22.5}, 
            {'id': 6, 'rank': 27.5}
        ]
        
        analysis = analyzer.analyze_performance_gaps(elite_configs, history)
        
        print(f"\n🎯 PERFORMANCE ANALYSIS RESULTS:")
        print(f"  Focus recommendations: {analysis['focus_recommendations']}")
        print(f"  Stagnant areas: {analysis['stagnant_areas']}")
        print(f"  Promising directions: {analysis['promising_directions']}")
        
        # Test prompt building
        builder = dynamic_prompting.DynamicPromptBuilder({'stagnation_threshold': 2})
        
        base_template = """Improve function {function_name}.
        
{performance_context}

## ORIGINAL FUNCTION
{original_function}

Optimize this function."""
        
        prompt_data = {
            'function_name': 'order_chromosome',
            'original_function': 'vector<pair<int,double>> order_chromosome(const vector<double>& chromosome) { return {}; }',
            'performance_context': '',
            'elite_configs': elite_configs,
            'iteration_history': history
        }
        
        adaptive_prompt = builder.build_adaptive_prompt(
            base_template, prompt_data, elite_configs, history
        )
        
        print(f"\n📝 ADAPTIVE PROMPT PREVIEW (first 300 chars):")
        print(adaptive_prompt[:300] + "..." if len(adaptive_prompt) > 300 else adaptive_prompt)
        
        # Check if it contains dynamic elements
        has_focus = "EVOLUTION FOCUS" in adaptive_prompt
        has_context = "PERFORMANCE CONTEXT" in adaptive_prompt
        has_guidance = "PERFORMANCE-DRIVEN GUIDANCE" in adaptive_prompt
        
        print(f"\n✅ DYNAMIC ELEMENTS CHECK:")
        print(f"  Has evolution focus: {has_focus}")
        print(f"  Has performance context: {has_context}")
        print(f"  Has specific guidance: {has_guidance}")
        
        if has_focus and has_context and has_guidance:
            print(f"\n🎉 SUCCESS: Dynamic prompting is fully functional!")
        else:
            print(f"\n⚠️  WARNING: Some dynamic elements missing")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_with_fixed_data()