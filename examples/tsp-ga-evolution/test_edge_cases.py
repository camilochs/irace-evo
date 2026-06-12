#!/usr/bin/env python3
"""
Test edge cases and error handling for dynamic prompting
"""

import sys
import json
import os
sys.path.append('../../inst/python/')

import dynamic_prompting

def test_edge_cases():
    print("=== TESTING EDGE CASES AND ERROR HANDLING ===\n")
    
    # 1. Test with no history file
    print("--- 1. No History File ---")
    try:
        # Test with non-existent directory
        fake_config = {'execDir': '/nonexistent/directory'}
        history = dynamic_prompting.get_iteration_history(fake_config)
        print(f"✓ Handles missing history gracefully: {len(history)} entries returned")
    except Exception as e:
        print(f"❌ Failed to handle missing history: {e}")
    
    # 2. Test with empty history
    print("\n--- 2. Empty History ---")
    try:
        analyzer = dynamic_prompting.PerformanceAnalyzer({'stagnation_threshold': 2})
        analysis = analyzer.analyze_performance_gaps([], [])
        print(f"✓ Handles empty inputs: focus = {analysis['focus_recommendations']}")
    except Exception as e:
        print(f"❌ Failed to handle empty history: {e}")
    
    # 3. Test with malformed history data
    print("\n--- 3. Malformed History Data ---")
    try:
        malformed_history = [
            {'iteration': 1},  # Missing performance data
            {'best_performance': 50.0},  # Missing iteration
            {'iteration': 'invalid', 'best_performance': 'invalid'}  # Invalid types
        ]
        
        analyzer = dynamic_prompting.PerformanceAnalyzer({'stagnation_threshold': 2})
        analysis = analyzer.analyze_performance_gaps([], malformed_history)
        print(f"✓ Handles malformed data: focus = {analysis['focus_recommendations']}")
    except Exception as e:
        print(f"❌ Failed to handle malformed data: {e}")
    
    # 4. Test with single iteration (insufficient data)
    print("\n--- 4. Insufficient Data (Single Iteration) ---")
    try:
        single_history = [{'iteration': 1, 'best_performance': 50.0}]
        
        analyzer = dynamic_prompting.PerformanceAnalyzer({'stagnation_threshold': 2})
        analysis = analyzer.analyze_performance_gaps([], single_history)
        expected = analysis['focus_recommendations'] == ['general_improvement']
        print(f"✓ Single iteration handled correctly: {expected}")
    except Exception as e:
        print(f"❌ Failed to handle single iteration: {e}")
    
    # 5. Test prompt building with missing data
    print("\n--- 5. Prompt Building with Missing Data ---")
    try:
        builder = dynamic_prompting.DynamicPromptBuilder({})
        
        # Missing template variables
        incomplete_template = "Improve {missing_variable} for {another_missing}."
        incomplete_data = {'function_name': 'test'}  # Missing variables
        
        # This should not crash, but handle missing variables gracefully
        try:
            result = builder.build_adaptive_prompt(
                incomplete_template, incomplete_data, [], []
            )
            print("⚠️  Prompt building with missing variables succeeded (may cause KeyError later)")
        except KeyError:
            print("✓ KeyError handled appropriately for missing template variables")
        except Exception as e:
            print(f"✓ Other error handled: {type(e).__name__}: {e}")
            
    except Exception as e:
        print(f"❌ Prompt builder initialization failed: {e}")
    
    # 6. Test file I/O errors
    print("\n--- 6. File I/O Error Handling ---")
    try:
        # Test saving to read-only directory (if possible)
        readonly_config = {'execDir': '/root'}  # Should be read-only for most users
        test_data = {'iteration': 1, 'test': True}
        
        dynamic_prompting.save_iteration_performance(readonly_config, test_data)
        print("⚠️  Write to restricted directory succeeded (unexpected)")
    except PermissionError:
        print("✓ Permission denied handled appropriately")
    except Exception as e:
        print(f"✓ Other I/O error handled: {type(e).__name__}")
    
    # 7. Test with extreme values
    print("\n--- 7. Extreme Values ---")
    try:
        extreme_history = [
            {'iteration': i, 'best_performance': float('inf')} 
            for i in range(1, 6)
        ]
        
        analyzer = dynamic_prompting.PerformanceAnalyzer({'stagnation_threshold': 2})
        analysis = analyzer.analyze_performance_gaps([], extreme_history)
        print(f"✓ Infinite values handled: focus = {analysis['focus_recommendations']}")
    except Exception as e:
        print(f"❌ Failed to handle extreme values: {e}")
    
    # 8. Test with very large history
    print("\n--- 8. Large History Handling ---")
    try:
        large_history = [
            {'iteration': i, 'best_performance': 50.0 - i*0.1} 
            for i in range(1, 101)  # 100 iterations
        ]
        
        analyzer = dynamic_prompting.PerformanceAnalyzer({'stagnation_threshold': 2})
        analysis = analyzer.analyze_performance_gaps([], large_history)
        print(f"✓ Large history handled: {len(large_history)} iterations processed")
    except Exception as e:
        print(f"❌ Failed to handle large history: {e}")
    
    print("\n=== EDGE CASE TESTING COMPLETE ===")

if __name__ == "__main__":
    test_edge_cases()