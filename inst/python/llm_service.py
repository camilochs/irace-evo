"""
LLM Service for irace-evo

Handles interaction with Large Language Models for code generation.
Supports multiple providers (OpenAI, Anthropic, etc.) and multiple programming languages.

Author: Camilo Chacón Sartori
"""

import json
import logging
import time
import os
import random
from typing import Dict, Any, List, Optional
import re

from dynamic_prompting import DynamicPromptBuilder, get_iteration_history, save_iteration_performance

# Global system prompt for optimization expertise
OPTIMIZATION_SYSTEM_PROMPT = """You are a world-class algorithm optimization expert with deep expertise in computational complexity analysis and performance optimization, specializing in metaheuristic algorithm enhancement and automated code evolution. Your primary mission is
  to generate high-performance algorithm variants that outperform existing implementations through intelligent optimizations.
  
CRITICAL CONSTRAINT: Prioritize THROUGHPUT over sophistication. More iterations beats complex heuristics.

CORE OPTIMIZATION PRINCIPLES:
  1. COMPUTATIONAL EFFICIENCY FIRST: 
     - Minimize overhead in hot paths (functions called millions of times)
     - O(n) often beats O(n log n) when constants matter under time pressure
     - Cache frequently accessed values, eliminate redundant computations

  2. TIME-AWARE HEURISTIC DESIGN: 
     - Optimize for solution quality PER ITERATION, not just final optimality
     - LOW computational overhead relative to benefit gained
     - Fast convergence to good solutions > slow convergence to optimal

  3. PRAGMATIC METAHEURISTIC IMPROVEMENTS:
     - Simple selection biases: exploit problem structure without complex logic
     - Precompute static values once, reuse across iterations
     - Early plateau detection and restart mechanisms

  4. CRITICAL ANTI-PATTERNS TO AVOID:
     - Multi-criteria optimization with expensive composite scoring
     - Dynamic memory allocation in evaluation functions
     - Thread-local storage, random number generation in hot paths
     - Complex statistical computations in inner optimization loops
     - Complex constraint handling that costs more than it saves
     - Multiple normalization factors computed on every call
     - Precomputed static caches that get rebuilt frequently

  5. TIME-CONSTRAINED ALGORITHM PATTERNS:
     - Greedy with smart tie-breaking over exhaustive search
     - Cached lookup tables for repeated computations
     - Incremental updates vs full recalculation
     - Adaptive parameter tuning based on time remaining
     - Precomputed lookup tables for expensive functions

  7. EVOLUTIONARY CODE PATTERNS: When modifying existing code:
     - Preserve functional correctness while enhancing performance
     - Make surgical changes that maximize impact
     - Consider parameter interdependencies
     - Maintain code readability for future iterations

  8. PERFORMANCE MEASUREMENT: Focus on metrics that matter:
     - Solution quality vs computation time trade-offs
     - Scalability across different problem sizes
     - Robustness across diverse instance types
     - Memory usage patterns under load

  RESPONSE FORMAT:
  - Lead with the KEY OPTIMIZATION insight and computational cost
  - Explain why this simple approach beats complex alternatives
  - Provide implementation rationale focused on speed
  - Justify simplicity over sophistication

  Your goal is to generate SIMPLE, FAST algorithm variants that win through speed and efficiency."""


class LanguageTemplate:
    """Base class for language-specific templates and validation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def get_prompt_template(self) -> str:
        """Get language-specific prompt template"""
        raise NotImplementedError
    
    def extract_code(self, response: str) -> str:
        """Extract code from LLM response for this language"""
        raise NotImplementedError
    
    def validate_code(self, code: str, prompt_data: Dict[str, Any]) -> bool:
        """Validate generated code for this language"""
        raise NotImplementedError
    
    def get_forbidden_patterns(self) -> List[str]:
        """Get forbidden patterns for security"""
        raise NotImplementedError


class CppTemplate(LanguageTemplate):
    """Template for C++ code generation"""
    
    def get_prompt_template(self) -> str:
        return """You are an expert C++ algorithm designer tasked with improving a heuristic function.

## PROBLEM CONTEXT
**Problem**: {problem_name}
**Description**: {problem_description}
**Algorithm Approach**: {algorithm_approach}
**Optimization Objective**: {optimization_objective}
**Key Challenges**: {key_challenges}
**Performance Considerations**: {performance_considerations}
**Domain Knowledge**: {domain_knowledge}

## CURRENT SITUATION
- Iteration: {current_iteration} of {max_iterations}
- Current best ranking: {best_cost} (lower is better)  
- Performance trend: {convergence_trend}
- Performance gap: {performance_gap:.2f} units from average
- Configurations tested: {num_configurations}

## CONTEXT: DATA STRUCTURES & ENVIRONMENT
{context_code}

{function_section}

## PERFORMANCE ANALYSIS & STRATEGY GUIDANCE
- Best ranking so far: {best_cost}
- Average ranking: {average_cost:.2f}
- Worst ranking: {worst_cost}
- Performance range: {performance_range:.2f}
- Ranking pressure: {ranking_pressure:.2f} (closer to 1.0 = more room for improvement)
- Strategy focus: {strategy_description}
- **Improvement intensity needed**: {improvement_intensity}

## REQUIREMENTS FOR NEW VARIANT #{variant_number}
1. Must maintain the same function signature
2. Must be syntactically valid C++17
3. Can use STL containers (<vector>, <algorithm>, <memory>, etc.)
4. Follow RAII principles and modern C++ best practices
5. Must be DIFFERENT from these already generated variants:
{previous_variants_info}

## IMPROVEMENT STRATEGY: {strategy}
{strategy_description}

## TASK
Generate a NEW and DIFFERENT C++ function implementation that:
1. Improves algorithmic performance
2. Is distinctly different from previous variants
3. Uses the strategy: {strategy}
4. Follows C++ best practices

Provide ONLY the C++ function implementation, no explanations.

```cpp"""
    
    def extract_code(self, response: str) -> str:
        """Extract C++ code from LLM response"""
        # Look for code blocks
        code_block_pattern = r'```(?:cpp|c\+\+)?\s*(.*?)```'
        matches = re.findall(code_block_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if matches:
            return matches[0].strip()
        
        # Look for function pattern
        function_pattern = r'(\w+\s+\w+\s*\([^)]*\)\s*\{.*?\})'
        matches = re.findall(function_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        return response.strip()
    
    def validate_code(self, code: str, prompt_data: Dict[str, Any]) -> bool:
        """Validate C++ function code"""
        if not code or '{' not in code or '}' not in code:
            return False
        
        # Check for balanced braces
        brace_count = code.count('{') - code.count('}')
        if brace_count != 0:
            return False
        
        return True
    
    def get_forbidden_patterns(self) -> List[str]:
        return [
            'system(', 'exec(', 'fork(', 'popen(',
            '#include <cstdlib>', 'delete ', 'free(',
            'malloc(', 'new ', 'goto '
        ]


class PythonTemplate(LanguageTemplate):
    """Template for Python code generation"""
    
    def get_prompt_template(self) -> str:
        return """You are an expert Python algorithm designer tasked with improving a heuristic function.

## PROBLEM CONTEXT
**Problem**: {problem_name}
**Description**: {problem_description}
**Algorithm Approach**: {algorithm_approach}
**Optimization Objective**: {optimization_objective}
**Key Challenges**: {key_challenges}
**Performance Considerations**: {performance_considerations}
**Domain Knowledge**: {domain_knowledge}

## CURRENT SITUATION
- Iteration: {current_iteration} of {max_iterations}
- Current best ranking: {best_cost} (lower is better)  
- Performance trend: {convergence_trend}
- Performance gap: {performance_gap:.2f} units from average
- Configurations tested: {num_configurations}

## CONTEXT: DATA STRUCTURES & ENVIRONMENT
{context_code}

{function_section}

## PERFORMANCE ANALYSIS & STRATEGY GUIDANCE
- Best ranking so far: {best_cost}
- Average ranking: {average_cost:.2f}
- Worst ranking: {worst_cost}
- Performance range: {performance_range:.2f}
- Ranking pressure: {ranking_pressure:.2f} (closer to 1.0 = more room for improvement)
- Strategy focus: {strategy_description}
- **Improvement intensity needed**: {improvement_intensity}

## REQUIREMENTS FOR NEW VARIANT #{variant_number}
1. Must maintain the same function signature
2. Must be syntactically valid Python 3.8+
3. Can use standard libraries (itertools, collections, heapq, etc.)
4. Follow Pythonic patterns and PEP 8
5. Use type hints where appropriate
6. Must be DIFFERENT from these already generated variants:
{previous_variants_info}

## IMPROVEMENT STRATEGY: {strategy}
{strategy_description}

## TASK
Generate a NEW and DIFFERENT Python function implementation that:
1. Improves algorithmic performance
2. Is distinctly different from previous variants
3. Uses the strategy: {strategy}
4. Follows Python best practices

Provide ONLY the Python function implementation, no explanations.

```python"""
    
    def extract_code(self, response: str) -> str:
        """Extract Python code from LLM response"""
        code_block_pattern = r'```python\s*(.*?)```'
        matches = re.findall(code_block_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if matches:
            return matches[0].strip()
        
        # Look for function pattern
        function_pattern = r'(def\s+\w+\s*\([^)]*\):.*?)(?=\n\S|\Z)'
        matches = re.findall(function_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        return response.strip()
    
    def validate_code(self, code: str, prompt_data: Dict[str, Any]) -> bool:
        """Validate Python function code"""
        if not code or 'def ' not in code:
            return False
        
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError:
            return False
    
    def get_forbidden_patterns(self) -> List[str]:
        return [
            'import os', 'import subprocess', 'import sys',
            'exec(', 'eval(', '__import__(',
            'open(', 'file(', 'input('
        ]


class JavaTemplate(LanguageTemplate):
    """Template for Java code generation"""
    
    def get_prompt_template(self) -> str:
        return """You are an expert Java algorithm designer tasked with improving a heuristic method.

## PROBLEM CONTEXT
**Problem**: {problem_name}
**Description**: {problem_description}
**Algorithm Approach**: {algorithm_approach}
**Optimization Objective**: {optimization_objective}
**Key Challenges**: {key_challenges}
**Performance Considerations**: {performance_considerations}
**Domain Knowledge**: {domain_knowledge}

## CURRENT SITUATION  
- Iteration: {current_iteration} of {max_iterations}
- Current best ranking: {best_cost} (lower is better)
- Performance trend: {convergence_trend}
- Performance gap: {performance_gap:.2f} units from average
- Configurations tested: {num_configurations}

## CONTEXT: DATA STRUCTURES & ENVIRONMENT
{context_code}

{function_section}

## PERFORMANCE ANALYSIS & STRATEGY GUIDANCE
- Best ranking so far: {best_cost}
- Average ranking: {average_cost:.2f}
- Worst ranking: {worst_cost}
- Performance range: {performance_range:.2f}
- Ranking pressure: {ranking_pressure:.2f} (closer to 1.0 = more room for improvement)
- Strategy focus: {strategy_description}
- **Improvement intensity needed**: {improvement_intensity}

## REQUIREMENTS FOR NEW VARIANT #{variant_number}
1. Must maintain the same method signature
2. Must be syntactically valid Java 8+
3. Can use Collections Framework (ArrayList, HashMap, etc.)
4. Follow Java coding conventions
5. Must be DIFFERENT from these already generated variants:
{previous_variants_info}

## IMPROVEMENT STRATEGY: {strategy}
{strategy_description}

## TASK
Generate a NEW and DIFFERENT Java method implementation that:
1. Improves algorithmic performance
2. Is distinctly different from previous variants  
3. Uses the strategy: {strategy}
4. Follows Java best practices

Provide ONLY the Java method implementation, no explanations.

```java"""
    
    def extract_code(self, response: str) -> str:
        """Extract Java code from LLM response"""
        code_block_pattern = r'```java\s*(.*?)```'
        matches = re.findall(code_block_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if matches:
            return matches[0].strip()
        
        # Look for method pattern
        method_pattern = r'((?:public|private|protected)?\s*(?:static)?\s*\w+\s+\w+\s*\([^)]*\)\s*\{.*?\})'
        matches = re.findall(method_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        return response.strip()
    
    def validate_code(self, code: str, prompt_data: Dict[str, Any]) -> bool:
        """Basic validation for Java method code"""
        if not code or '{' not in code or '}' not in code:
            return False
        
        # Check for balanced braces
        brace_count = code.count('{') - code.count('}')
        if brace_count != 0:
            return False
        
        return True
    
    def get_forbidden_patterns(self) -> List[str]:
        return [
            'Runtime.', 'System.exit', 'Runtime.exec',
            'ProcessBuilder', 'Class.forName',
            'System.setProperty', 'native '
        ]


class LLMService:
    """Service for interacting with LLMs for multi-language code generation"""
    
    # Language template registry
    LANGUAGE_TEMPLATES = {
        'cpp': CppTemplate,
        'c++': CppTemplate,
        'python': PythonTemplate,
        'py': PythonTemplate,
        'java': JavaTemplate
    }
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_provider = config.get('api_provider', 'openai')
        self.model = config.get('model', 'gpt-4')
        self.max_retries = config.get('max_retries', 3)
        self.timeout = config.get('timeout', 60)
        # Temperature configuration - supports both fixed value and random range
        temperature_range = config.get('temperature_range', {})
        if temperature_range.get('enabled', False):
            min_temp = temperature_range.get('min', 0.1)
            max_temp = temperature_range.get('max', 0.8)
            self.temperature = random.uniform(min_temp, max_temp)
            logging.info(f"Using random temperature: {self.temperature:.3f} (range: {min_temp}-{max_temp})")
        else:
            self.temperature = config.get('temperature', 0.2)
        self.max_tokens = config.get('max_tokens', 1500)
        
        # Dynamic prompting configuration
        self.use_dynamic_prompting = config.get('use_dynamic_prompting', True)
        self.scenario_config = config.get('scenario_config', {})
        
        # Determine language
        self.language = config.get('language', 'cpp').lower()
        if self.language not in self.LANGUAGE_TEMPLATES:
            raise ValueError(f"Unsupported language: {self.language}")
        
        # Initialize language template
        self.language_template = self.LANGUAGE_TEMPLATES[self.language](config)
        
        # Load custom prompt template if provided
        self.prompt_template = self._load_custom_prompt_template() or self.language_template.get_prompt_template()
        
        # Initialize dynamic prompting if enabled
        if self.use_dynamic_prompting:
            self.dynamic_prompt_builder = DynamicPromptBuilder(config)
        else:
            self.dynamic_prompt_builder = None
        
        # Initialize API client
        self.client = self._initialize_client()
        
        # Metrics tracking
        self.metrics = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_retries': 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_cost_estimate': 0.0
        }
        
        # Detailed logging setup
        self.logger = logging.getLogger(__name__)
        self.log_interactions = config.get('log_interactions', True)
        self.log_file_path = config.get('llm_log_file', './logs/irace-evo-llm.log')
        
        # Create logs directory if it doesn't exist
        import os
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Setup detailed file logger
        if self.log_interactions:
            self._setup_detailed_logger()
    
    def _setup_detailed_logger(self):
        """Setup detailed file logger for LLM interactions"""
        self.detailed_logger = logging.getLogger(f"{__name__}.detailed")
        
        # Remove existing handlers to avoid duplicates
        for handler in self.detailed_logger.handlers[:]:
            self.detailed_logger.removeHandler(handler)
        
        # Create file handler
        file_handler = logging.FileHandler(self.log_file_path, mode='a')
        
        # Create detailed formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        self.detailed_logger.addHandler(file_handler)
        self.detailed_logger.setLevel(logging.INFO)
        self.detailed_logger.propagate = False
        
        # Log session start
        self.detailed_logger.info("="*80)
        self.detailed_logger.info("irace-evo LLM Session Started")
        self.detailed_logger.info(f"Provider: {self.api_provider}, Model: {self.model}")
        self.detailed_logger.info("="*80)
    
    def _load_custom_prompt_template(self) -> Optional[str]:
        """Load custom prompt template if provided"""
        template_path = self.config.get('prompt_template')
        
        if template_path and os.path.exists(template_path):
            with open(template_path, 'r') as f:
                return f.read()
        return None
    
    def _initialize_client(self):
        """Initialize the appropriate LLM client based on provider"""
        try:
            if self.api_provider.lower() == 'openai':
                import openai
                return openai.OpenAI(timeout=self.timeout)  # Uses OPENAI_API_KEY env var
            elif self.api_provider.lower() == 'anthropic':
                import anthropic
                return anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
            else:
                raise ValueError(f"Unsupported API provider: {self.api_provider}")
        except ImportError as e:
            raise ImportError(f"Required package not installed for {self.api_provider}: {e}")
    
    def generate_function_variant(self, prompt_data: Dict[str, Any]) -> str:
        """
        Generate a new function variant using LLM
        
        Args:
            prompt_data: Dictionary with all data needed for prompt
            
        Returns:
            Generated function code in the specified language
        """
        
        # Build prompt from template and data
        prompt = self._build_prompt(prompt_data)
        
        # Try generating with retries
        for attempt in range(self.max_retries):
            try:
                self.metrics['total_calls'] += 1
                if attempt > 0:
                    self.metrics['total_retries'] += 1
                
                # Log detailed input
                call_id = f"CALL_{self.metrics['total_calls']:03d}"
                if self.log_interactions and hasattr(self, 'detailed_logger'):
                    self._log_llm_input(call_id, prompt, attempt, prompt_data)
                
                response, tokens_used, cost_estimate = self._call_llm(prompt, attempt)
                
                # Log detailed output
                if self.log_interactions and hasattr(self, 'detailed_logger'):
                    self._log_llm_output(call_id, response, tokens_used, cost_estimate, attempt)
                
                # Update token metrics
                self.metrics['total_input_tokens'] += tokens_used.get('input', 0)
                self.metrics['total_output_tokens'] += tokens_used.get('output', 0)
                self.metrics['total_cost_estimate'] += cost_estimate
                
                # Extract code using language-specific extractor
                function_code = self.language_template.extract_code(response)
                
                # Language-specific validation
                if self._validate_function_code(function_code, prompt_data):
                    self.metrics['successful_calls'] += 1
                    
                    # Log successful extraction
                    if self.log_interactions and hasattr(self, 'detailed_logger'):
                        self._log_code_extraction(call_id, function_code, success=True)
                    
                    return function_code
                else:
                    self.logger.warning(f"Generated {self.language} code failed validation, attempt {attempt + 1}")
                    if self.log_interactions and hasattr(self, 'detailed_logger'):
                        self._log_code_extraction(call_id, function_code, success=False, reason="Validation failed")
                    
            except Exception as e:
                self.metrics['failed_calls'] += 1
                self.logger.error(f"LLM call failed on attempt {attempt + 1}: {e}")
                if self.log_interactions and hasattr(self, 'detailed_logger'):
                    self.detailed_logger.error(f"{call_id} - API call failed: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        raise RuntimeError(f"Failed to generate valid {self.language} function after {self.max_retries} attempts")
    
    def fix_compilation_error(self, faulty_code: str, compilation_error: str, 
                             original_context: Dict[str, Any]) -> str:
        """
        Generate a corrected version of code based on compilation errors
        
        Args:
            faulty_code: The code that failed to compile
            compilation_error: The compilation error message
            original_context: The original context used to generate the faulty code
            
        Returns:
            Corrected function code
        """
        
        # Build error correction prompt
        error_correction_prompt = self._build_error_correction_prompt(
            faulty_code, compilation_error, original_context
        )
        
        # Try fixing with retries
        for attempt in range(self.max_retries):
            try:
                self.metrics['total_calls'] += 1
                if attempt > 0:
                    self.metrics['total_retries'] += 1
                
                # Log detailed input for error correction
                call_id = f"ERROR_FIX_{self.metrics['total_calls']:03d}"
                if self.log_interactions and hasattr(self, 'detailed_logger'):
                    self.detailed_logger.info(f"{call_id} - COMPILATION ERROR CORRECTION")
                    self.detailed_logger.info(f"Attempt: {attempt + 1}/{self.max_retries}")
                    self.detailed_logger.info(f"Faulty code length: {len(faulty_code)} chars")
                    self.detailed_logger.info(f"Compilation error: {compilation_error}")
                    self.detailed_logger.info(f"Prompt: {error_correction_prompt}")
                
                response, tokens_used, cost_estimate = self._call_llm(error_correction_prompt, attempt)
                
                # Update metrics
                self.metrics['total_input_tokens'] += tokens_used.get('input', 0)
                self.metrics['total_output_tokens'] += tokens_used.get('output', 0)
                self.metrics['total_cost_estimate'] += cost_estimate
                
                # Extract and validate corrected function code
                function_code = self.language_template.extract_code(response)
                
                # Log detailed output
                if self.log_interactions and hasattr(self, 'detailed_logger'):
                    self.detailed_logger.info(f"{call_id} - Raw response: {response}")
                    self.detailed_logger.info(f"{call_id} - Extracted function: {function_code}")
                
                # Simple validation - check if it looks like a function
                if self._validate_function_code(function_code, original_context):
                    if self.log_interactions and hasattr(self, 'detailed_logger'):
                        self.detailed_logger.info(f"{call_id} - ERROR CORRECTION SUCCESS")
                        self._log_code_extraction(call_id, function_code, success=True, reason="Error correction successful")
                    return function_code
                else:
                    self.logger.warning(f"Error correction failed validation, attempt {attempt + 1}")
                    if self.log_interactions and hasattr(self, 'detailed_logger'):
                        self._log_code_extraction(call_id, function_code, success=False, reason="Corrected code validation failed")
                    
            except Exception as e:
                self.metrics['failed_calls'] += 1
                self.logger.error(f"Error correction call failed on attempt {attempt + 1}: {e}")
                if self.log_interactions and hasattr(self, 'detailed_logger'):
                    self.detailed_logger.error(f"{call_id} - Error correction API call failed: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        raise RuntimeError(f"Failed to fix compilation error after {self.max_retries} attempts")
    
    def _build_error_correction_prompt(self, faulty_code: str, compilation_error: str, 
                                      context: Dict[str, Any]) -> str:
        """Build prompt for error correction"""
        
        problem_context = context.get('problem_context', {})
        
        # Create error correction prompt template
        error_correction_template = """You are an expert {language} programmer. The following code has compilation errors that need to be fixed.

## PROBLEM CONTEXT
**Problem**: {problem_name}
**Algorithm Approach**: {algorithm_approach}
**Function Purpose**: {function_purpose}

## BACKGROUND
You previously generated this code using the strategy "{strategy}" to improve an optimization algorithm. However, the generated code has compilation errors that need to be fixed.

## COMPILATION ERROR
The following code failed to compile with this error:
```
{compilation_error}
```

## FAULTY CODE (that you generated earlier)
```{language}
{faulty_code}
```

## ANALYSIS
Looking at the error, it appears the issue is likely related to:
- Incorrect struct/class member access
- Missing includes or namespace issues  
- Type mismatches or incorrect syntax
- Variable scope or declaration problems

## TASK
Fix the compilation error while maintaining the same:
1. Function signature and return type
2. Core algorithmic logic and purpose that you originally intended
3. Performance characteristics and optimization approach
4. Code style and structure where possible

## REQUIREMENTS
- Must compile without errors
- Must maintain the original function's behavior and your intended improvements
- Use modern {language} best practices
- Keep the same optimization level and approach
- Only fix what's necessary to resolve the compilation error
- Preserve the algorithmic innovations you introduced

Return ONLY the corrected function code, nothing else:"""

        return error_correction_template.format(
            language=self.language.upper(),
            problem_name=problem_context.get('problem_name', 'Optimization Problem'),
            algorithm_approach=problem_context.get('algorithm_approach', 'Heuristic algorithm'),
            function_purpose=context.get('function_purpose', 'Optimization function'),
            strategy=context.get('variant_info', {}).get('original_strategy', 'unknown strategy'),
            compilation_error=compilation_error,
            faulty_code=faulty_code
        )
    
    def _build_prompt(self, data: Dict[str, Any]) -> str:
        """Build the complete prompt from template and data"""
        
        # Check if dynamic prompting is enabled and we have performance context
        if (self.use_dynamic_prompting and self.dynamic_prompt_builder and 
            'elite_configs' in data and 'iteration_history' in data):
            
            # Log dynamic prompting usage
            elite_configs = data.get('elite_configs', [])
            iteration_history = data.get('iteration_history', [])
            
            print(f"[irace-evo] 🚀 DYNAMIC PROMPTING: Adapting prompt based on {len(iteration_history)} iterations of performance data")
            
            # Use dynamic prompting based on performance analysis
            base_template = self.prompt_template
            
            # Build adaptive prompt
            adaptive_template = self.dynamic_prompt_builder.build_adaptive_prompt(
                base_template, data, elite_configs, iteration_history
            )
            
            # Use the adaptive template for this generation
            current_template = adaptive_template
            print(f"[irace-evo] ✅ ADAPTIVE PROMPT: Generated enhanced prompt ({len(adaptive_template)} chars)")
        else:
            # Log why dynamic prompting is not used
            if not self.use_dynamic_prompting:
                print(f"[irace-evo] ⚪ STATIC PROMPT: Dynamic prompting disabled in config")
            elif not self.dynamic_prompt_builder:
                print(f"[irace-evo] ⚪ STATIC PROMPT: Dynamic prompt builder not initialized")
            elif 'elite_configs' not in data or 'iteration_history' not in data:
                print(f"[irace-evo] ⚪ STATIC PROMPT: Insufficient performance context (need 2+ iterations)")
            
            # Use standard template
            current_template = self.prompt_template
        
        # Prepare previous variants info
        previous_variants = data.get('previous_variants', [])
        if previous_variants:
            variants_info = "\n".join([f"- Variant: {v}" for v in previous_variants])
        else:
            variants_info = "- (No previous variants in this session)"
        
        # Determine improvement intensity based on performance metrics
        needs_aggressive = data.get('improvement_guidance', {}).get('needs_aggressive_changes', False)
        ranking_pressure_raw = data.get('improvement_guidance', {}).get('ranking_pressure', 0.5)
        
        # Ensure ranking_pressure is numeric
        try:
            ranking_pressure = float(ranking_pressure_raw) if ranking_pressure_raw is not None else 0.5
        except (ValueError, TypeError):
            ranking_pressure = 0.5
        
        if needs_aggressive or ranking_pressure > 0.7:
            improvement_intensity = "HIGH - Consider major algorithmic changes"
        elif ranking_pressure > 0.4:
            improvement_intensity = "MEDIUM - Moderate improvements needed"
        else:
            improvement_intensity = "LOW - Fine-tuning and conservative changes"
        
        # Extract problem context information
        problem_context = data.get('problem_context', {})
        key_challenges_str = ", ".join(problem_context.get('key_challenges', ['No specific challenges defined']))
        
        # Prepare numeric values for formatting (avoid .2f format errors)
        def safe_float(value, default=0.0):
            try:
                return float(value) if value is not None else default
            except (ValueError, TypeError):
                return default
        
        performance_gap_val = safe_float(data['improvement_guidance'].get('performance_gap', 0))
        average_cost_val = safe_float(data['performance_stats'].get('average_cost'), 1500.0)
        performance_range_val = safe_float(data['performance_stats'].get('performance_range'), 100.0)
        ranking_pressure_val = safe_float(ranking_pressure)
        
        # Build function section based on context mode
        function_section = self._build_function_section(data)
        
        # Fill template with enhanced data including problem context
        prompt = current_template.format(
            # Problem context fields
            problem_name=problem_context.get('problem_name', 'Optimization Problem'),
            problem_description=problem_context.get('problem_description', 'General optimization problem'),
            algorithm_approach=problem_context.get('algorithm_approach', 'Heuristic algorithm'),
            optimization_objective=problem_context.get('optimization_objective', 'Optimize performance'),
            key_challenges=key_challenges_str,
            performance_considerations=problem_context.get('performance_considerations', 'Focus on algorithmic efficiency'),
            domain_knowledge=problem_context.get('domain_knowledge', 'Apply general optimization principles'),
            # Existing fields
            current_iteration=data['iteration_context']['current_iteration'],
            max_iterations=data['iteration_context'].get('max_iterations', 4),
            best_cost=data['performance_stats'].get('best_cost_so_far', 'Unknown'),
            convergence_trend=data['performance_stats'].get('convergence_trend', 'unknown'),
            performance_gap=performance_gap_val,
            num_configurations=data['performance_stats'].get('num_configurations_tested', 'Unknown'),
            context_code=data.get('context_code', '// No context available'),
            function_section=function_section,
            average_cost=average_cost_val,
            worst_cost=data['performance_stats'].get('worst_cost', 'Unknown'),
            performance_range=performance_range_val,
            ranking_pressure=ranking_pressure_val,
            improvement_intensity=improvement_intensity,
            variant_number=data['variant_number'],
            strategy=data['strategy'],
            strategy_description=data['strategy_context'].get('description', ''),
            previous_variants_info=variants_info
        )
        
        return prompt
    
    def _build_function_section(self, data: Dict[str, Any]) -> str:
        """Build the function section based on context mode"""
        full_context_mode = data.get('full_context_mode', False)
        original_function = data.get('original_function', '')
        function_name = data.get('function_name', 'target_function')
        previous_functions = data.get('previous_functions', [])
        
        # Build diversity section if we have previous functions
        diversity_section = ""
        if previous_functions:
            diversity_section = f"""
## DIVERSITY REQUIREMENT - AVOID REPETITION
The following function implementations have been generated recently. Your new implementation must be FUNDAMENTALLY DIFFERENT:

"""
            for i, prev_func in enumerate(previous_functions[-3:], 1):  # Show last 3 only
                diversity_section += f"""### Previous Variant {i}:
```{self.language}
{prev_func}
```

"""
            diversity_section += """**CRITICAL**: Generate a completely different algorithmic approach. Do not repeat similar logic, variable names, or mathematical operations. Think of an entirely different way to solve the same problem while maintaining computational efficiency."""
        
        if full_context_mode:
            # Complete source code mode
            section = f"""## COMPLETE SOURCE CODE FOR CONTEXT
```{self.language}
{original_function}
```

## TASK: IMPROVE THE FUNCTION '{function_name}'
Your task is to improve ONLY the `{function_name}` function within this complete source code.
- Analyze the complete code to understand the context, data structures, and how the function fits
- Keep all other code unchanged
- Return ONLY the improved `{function_name}` function, nothing else
- Maintain the same function signature and behavior contract{diversity_section}"""
        else:
            # Function-only mode  
            section = f"""## CURRENT FUNCTION TO IMPROVE
```{self.language}
{original_function}
```{diversity_section}"""
        
        return section
    
    def _call_llm(self, prompt: str, attempt: int) -> tuple:
        """Make the actual LLM API call"""
        
        if self.api_provider.lower() == 'openai':
            return self._call_openai(prompt, attempt)
        elif self.api_provider.lower() == 'anthropic':
            return self._call_anthropic(prompt, attempt)
        else:
            raise ValueError(f"Unsupported provider: {self.api_provider}")
    
    def _call_openai(self, prompt: str, attempt: int) -> tuple:
        """Call OpenAI API"""
        try:
            self.logger.debug(f"Making OpenAI API call (attempt {attempt + 1}) with model {self.model}")
            
            # Prepare API call parameters with global optimization system prompt
            api_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": OPTIMIZATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature + (attempt * 0.1),  # Increase temperature for retries
                "timeout": self.timeout
            }
            
            # Use the correct token parameter depending on model
            # Newer models (like gpt-4o, gpt-4-turbo, o1-mini) use max_completion_tokens
            # Older models still use max_tokens
            if "gpt-4" in self.model.lower() or "gpt-5" in self.model.lower() or "o1" in self.model.lower() or "o4" in self.model.lower():
                api_params["max_completion_tokens"] = self.max_tokens
            else:
                api_params["max_tokens"] = self.max_tokens
            
            # Add stop sequences if they help with code generation
            # Removing stop parameter to see if it's causing issues
            # api_params["stop"] = ["```"]
            
            response = self.client.chat.completions.create(**api_params)
            
            # Extract tokens and calculate cost
            usage = response.usage
            tokens_used = {
                'input': usage.prompt_tokens,
                'output': usage.completion_tokens
            }
            
            # Cost estimation (approximate rates)
            cost_per_1k_input = 0.03 if 'gpt-4' in self.model else 0.0015
            cost_per_1k_output = 0.06 if 'gpt-4' in self.model else 0.002
            
            cost_estimate = (
                (tokens_used['input'] / 1000) * cost_per_1k_input +
                (tokens_used['output'] / 1000) * cost_per_1k_output
            )
            
            return response.choices[0].message.content, tokens_used, cost_estimate
            
        except Exception as e:
            error_msg = f"OpenAI API call failed on attempt {attempt + 1}: {type(e).__name__}: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _call_anthropic(self, prompt: str, attempt: int) -> tuple:
        """Call Anthropic Claude API"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.7 + (attempt * 0.1),
                system=OPTIMIZATION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract tokens and calculate cost
            usage = response.usage
            tokens_used = {
                'input': usage.input_tokens,
                'output': usage.output_tokens
            }
            
            # Claude pricing (approximate)
            cost_per_1k_input = 0.008 if 'claude-3-opus' in self.model else 0.003
            cost_per_1k_output = 0.024 if 'claude-3-opus' in self.model else 0.015
            
            cost_estimate = (
                (tokens_used['input'] / 1000) * cost_per_1k_input +
                (tokens_used['output'] / 1000) * cost_per_1k_output
            )
            
            return response.content[0].text, tokens_used, cost_estimate
            
        except Exception as e:
            raise RuntimeError(f"Anthropic API call failed: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics for this LLM service instance"""
        metrics = self.metrics.copy()
        # Add configuration information
        metrics['api_provider'] = self.api_provider
        metrics['model'] = self.model
        metrics['temperature'] = self.temperature
        metrics['max_tokens'] = getattr(self, 'max_tokens', None)
        return metrics
    
    def reset_metrics(self):
        """Reset metrics counters"""
        for key in self.metrics:
            if isinstance(self.metrics[key], (int, float)):
                self.metrics[key] = 0
    
    def _log_llm_input(self, call_id: str, prompt: str, attempt: int, prompt_data: Dict[str, Any]):
        """Log detailed LLM input"""
        variant_info = f"Variant #{prompt_data.get('variant_number', 'Unknown')}"
        strategy = prompt_data.get('strategy', 'Unknown')
        iteration = prompt_data.get('iteration_context', {}).get('current_iteration', 'Unknown')
        
        self.detailed_logger.info(f"\n{'-'*60}")
        self.detailed_logger.info(f"{call_id} - LLM INPUT (Attempt {attempt + 1})")
        self.detailed_logger.info(f"Iteration: {iteration}, {variant_info}, Strategy: {strategy}")
        self.detailed_logger.info(f"Provider: {self.api_provider}, Model: {self.model}")
        self.detailed_logger.info(f"{'-'*60}")
        self.detailed_logger.info("PROMPT:")
        self.detailed_logger.info(prompt)
        self.detailed_logger.info(f"{'-'*60}")
    
    def _log_llm_output(self, call_id: str, response: str, tokens_used: dict, cost_estimate: float, attempt: int):
        """Log detailed LLM output"""
        self.detailed_logger.info(f"\n{call_id} - LLM OUTPUT (Attempt {attempt + 1})")
        self.detailed_logger.info(f"Tokens - Input: {tokens_used.get('input', 0)}, Output: {tokens_used.get('output', 0)}")
        self.detailed_logger.info(f"Estimated Cost: ${cost_estimate:.4f}")
        self.detailed_logger.info(f"{'-'*60}")
        self.detailed_logger.info("RESPONSE:")
        self.detailed_logger.info(response)
        self.detailed_logger.info(f"{'-'*60}")
    
    def _log_code_extraction(self, call_id: str, extracted_code: str, success: bool, reason: str = ""):
        """Log code extraction results"""
        status = "SUCCESS" if success else "FAILED"
        self.detailed_logger.info(f"\n{call_id} - CODE EXTRACTION: {status}")
        if not success and reason:
            self.detailed_logger.info(f"Failure Reason: {reason}")
        self.detailed_logger.info(f"{'-'*60}")
        self.detailed_logger.info("EXTRACTED CODE:")
        self.detailed_logger.info(extracted_code)
        self.detailed_logger.info(f"{'='*60}")
        if success:
            self.detailed_logger.info("✓ Code extraction and validation successful")
        else:
            self.detailed_logger.info("✗ Code extraction or validation failed")
        self.detailed_logger.info(f"{'='*60}\n")
    
    def _validate_function_code(self, code: str, prompt_data: Dict[str, Any]) -> bool:
        """Validate function code using language-specific validator"""
        
        if not code:
            return False
        
        # Use language-specific validation
        if not self.language_template.validate_code(code, prompt_data):
            return False
        
        # Check for forbidden patterns
        code_lower = code.lower()
        for pattern in self.language_template.get_forbidden_patterns():
            if pattern.lower() in code_lower:
                self.logger.warning(f"Generated code contains forbidden pattern: {pattern}")
                return False
        
        return True


def get_supported_languages() -> List[str]:
    """Get list of supported programming languages"""
    return list(LLMService.LANGUAGE_TEMPLATES.keys())


# Utility function for testing
def test_llm_generation(language: str = 'cpp'):
    """Test LLM generation for specific language"""
    config = {
        'api_provider': 'openai',
        'model': 'gpt-3.5-turbo',
        'max_retries': 2,
        'language': language
    }
    
    service = LLMService(config)
    
    # Language-specific test data
    test_functions = {
        'cpp': 'double simple_heuristic(int x) { return x * 2.0; }',
        'python': 'def simple_heuristic(x: int) -> float:\n    return x * 2.0',
        'java': 'public double simpleHeuristic(int x) { return x * 2.0; }'
    }
    
    test_data = {
        'original_function': test_functions.get(language, test_functions['cpp']),
        'strategy': 'improve_efficiency',
        'strategy_context': {'description': 'Make the function more computationally efficient'},
        'iteration_context': {'current_iteration': 1, 'total_budget_used': 10},
        'performance_stats': {'best_cost_so_far': 100, 'average_cost': 150, 'convergence_trend': 'improving'},
        'variant_number': 1,
        'previous_variants': []
    }
    
    try:
        result = service.generate_function_variant(test_data)
        print(f"Generated {language} function:")
        print(result)
        return True
    except Exception as e:
        print(f"Test failed for {language}: {e}")
        return False


if __name__ == "__main__":
    print("Supported languages:", get_supported_languages())
    for lang in ['cpp', 'python', 'java']:
        print(f"\nTesting {lang}:")
        test_llm_generation(lang)