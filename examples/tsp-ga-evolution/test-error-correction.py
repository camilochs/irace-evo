#!/usr/bin/env python3
"""
Test script to specifically test LLM error correction functionality
"""

import sys
import os
import json

# Add the irace Python modules to path
sys.path.insert(0, '/home/camilocs/R/x86_64-pc-linux-gnu-library/4.1/irace/python')

from llm_service import LLMService

def test_error_correction():
    """Test LLM error correction functionality"""
    
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
    
    # Create a faulty C++ function with compilation error
    faulty_code = """set<int> decode_solution(const vector<double>& chromosome) {
    set<int> selected_runs;
    
    // Missing include for vector - this will cause compilation error
    std::vector<pair<double, int>> sorted_pairs;
    
    for (int i = 0; i < chromosome.size(); i++) {
        sorted_pairs.push_back(make_pair(chromosome[i], i));
    }
    
    sort(sorted_pairs.begin(), sorted_pairs.end());
    
    for (const auto& p : sorted_pairs) {
        if (p.first > 0.5) {
            selected_runs.insert(p.second);
        }
    }
    
    return selected_runs;
}"""
    
    # Simulate a typical compilation error
    compilation_error = """error: 'vector' is not a member of 'std'
error: template argument 1 is invalid
error: template argument 2 is invalid
error: 'make_pair' was not declared in this scope
error: 'sort' was not declared in this scope"""
    
    # Create context for error correction
    original_context = {
        'problem_context': config.get('problem_context', {}),
        'function_purpose': 'BRKGA chromosome decoding for run selection',
        'variant_info': {
            'variant_id': 'test_error_correction',
            'original_strategy': 'innovate_heuristic_design',
            'compilation_errors': [compilation_error]
        },
        'error_correction_attempt': True
    }
    
    print("="*60)
    print("TESTING LLM ERROR CORRECTION")
    print("="*60)
    print("Faulty code:")
    print("-" * 40)
    print(faulty_code)
    print("-" * 40)
    print()
    print("Compilation error:")
    print("-" * 40)
    print(compilation_error)
    print("-" * 40)
    print()
    
    try:
        print("Calling LLM for error correction...")
        corrected_code = llm_service.fix_compilation_error(
            faulty_code=faulty_code,
            compilation_error=compilation_error,
            original_context=original_context
        )
        
        print("="*60)
        print("LLM CORRECTION RESULT")
        print("="*60)
        print("Corrected code:")
        print("-" * 40)
        print(corrected_code)
        print("-" * 40)
        print()
        
        # Get metrics
        metrics = llm_service.get_metrics()
        print(f"LLM calls: {metrics['total_calls']}")
        print(f"Total cost: ${metrics['total_cost_estimate']:.3f}")
        
        # Basic validation - check if common issues are fixed
        corrections_found = []
        if '#include <vector>' in corrected_code or 'vector' in corrected_code:
            corrections_found.append("✅ Added vector include/usage")
        if 'std::make_pair' in corrected_code or 'make_pair' in corrected_code:
            corrections_found.append("✅ Fixed make_pair")
        if 'std::sort' in corrected_code or '#include <algorithm>' in corrected_code:
            corrections_found.append("✅ Fixed sort function")
            
        if corrections_found:
            print("\nDetected corrections:")
            for correction in corrections_found:
                print(f"  {correction}")
        else:
            print("\n⚠️  Could not detect specific corrections in the output")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_error_correction()