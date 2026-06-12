"""
Code Evolution Manager for irace-evo

Handles code generation, compilation, and management of algorithm variants
using Large Language Models (LLMs) integrated with irace.

Author: Camilo Chacón Sartori
"""

import json
import os
import subprocess
import tempfile
import hashlib
import logging
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

from logging_config import get_logger
from llm_service import LLMService
from compilation import CompilationManager
from strategies import BUILTIN_STRATEGIES
from language_handlers import LanguageHandlerFactory
from dynamic_prompting import get_iteration_history, save_iteration_performance


class CodeVariant:
    """Represents a single code variant with metadata"""
    
    def __init__(self, code: str, variant_id: str, parent_id: Optional[str] = None, 
                 strategy: str = "unknown"):
        self.code = code
        self.variant_id = variant_id
        self.parent_id = parent_id
        self.strategy = strategy
        self.executable_path: Optional[str] = None
        self.compilation_success = False
        self.compilation_errors: List[str] = []
        self.fingerprint = self._calculate_fingerprint()
    
    def _calculate_fingerprint(self) -> str:
        """Calculate unique fingerprint for this code variant"""
        return hashlib.md5(self.code.encode()).hexdigest()[:8]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'code': self.code,
            'variant_id': self.variant_id,
            'parent_id': self.parent_id,
            'strategy': self.strategy,
            'executable': self.executable_path,
            'compilation_success': self.compilation_success,
            'compilation_errors': self.compilation_errors,
            'fingerprint': self.fingerprint
        }


class CodeEvolutionManager:
    """Main manager for code evolution process"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize logger using centralized configuration
        self.logger = get_logger(__name__)
        
        # Get language configuration  
        self.language = config.get('language_config', {}).get('language', 'cpp')
        
        # Initialize language-specific components
        self.language_handler = LanguageHandlerFactory.create_handler(self.language, config)
        
        # Initialize LLM service with language config
        llm_config = config.get('llm_config', {})
        llm_config['language'] = self.language
        self.llm_service = LLMService(llm_config)
        
        self.compiler = CompilationManager(config.get('build_config', {}))
        
        # Evolution settings
        self.evolution_config = config.get('evolution_config', {})
        self.max_retries = self.evolution_config.get('max_compilation_failures', 3)
        self.strategies = self._load_strategies()
        
        # State tracking
        self.generated_variants: List[CodeVariant] = []
        self.failed_variants: List[CodeVariant] = []
    
    def _load_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Load available strategies from config and built-ins"""
        # Start with all builtin strategies
        all_strategies = BUILTIN_STRATEGIES.copy()
        
        # Debug logging
        self.logger.info(f"Loaded {len(all_strategies)} builtin strategies: {list(all_strategies.keys())}")
        
        # Add user-defined custom strategies  
        user_strategies = self.evolution_config.get('custom_strategies', [])
        for strategy in user_strategies:
            if isinstance(strategy, dict) and 'name' in strategy:
                all_strategies[strategy['name']] = strategy
        
        # Filter by available_strategies list if specified
        available_list = self.evolution_config.get('available_strategies', [])
        self.logger.info(f"Available strategies from config: {available_list}")
        
        if available_list:
            filtered_strategies = {}
            for strategy_name in available_list:
                if strategy_name in all_strategies:
                    filtered_strategies[strategy_name] = all_strategies[strategy_name]
                    self.logger.info(f"Added strategy: {strategy_name}")
                else:
                    self.logger.warning(f"Strategy '{strategy_name}' not found in builtin or custom strategies")
            
            self.logger.info(f"Final filtered strategies: {list(filtered_strategies.keys())}")
            return filtered_strategies
        
        return all_strategies
    
    def generate_and_compile_variants(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Main entry point: generate and compile code variants
        
        Args:
            context: Context from irace with iteration stats, elite configs, etc.
            
        Returns:
            List of successfully compiled variant dictionaries
        """
        target_variants = context.get('target_variants', 5)
        successful_variants = []
        total_attempts = 0
        max_total_attempts = target_variants * 3  # Allow some failures
        
        self.logger.info(f"Generating {target_variants} code variants")
        
        # Load iteration history for dynamic prompting
        iteration_history = get_iteration_history(context.get('scenario_config', {}))
        
        if len(iteration_history) == 0:
            print(f"[irace-evo] 📋 PERFORMANCE HISTORY: No previous iterations found (first run)")
        elif len(iteration_history) < 2:
            print(f"[irace-evo] 📋 PERFORMANCE HISTORY: {len(iteration_history)} iteration found (insufficient for analysis)")
        else:
            latest_perf = iteration_history[-1].get('best_performance', 'unknown')
            print(f"[irace-evo] 📋 PERFORMANCE HISTORY: {len(iteration_history)} iterations loaded (latest best: {latest_perf})")
        
        self.logger.info(f"Loaded {len(iteration_history)} iterations from history")
        
        # Add performance context to generation context
        enhanced_context = context.copy()
        enhanced_context['iteration_history'] = iteration_history
        enhanced_context['elite_configs'] = context.get('elite_configurations', [])
        
        # Get elite code variants (if any from previous iterations)
        self.logger.info("Getting elite variants from previous iterations...")
        elite_variants = self._get_elite_variants(enhanced_context)
        self.logger.info(f"Found {len(elite_variants)} elite variants")
        
        self.logger.info(f"Starting generation loop. Target: {target_variants}, Max attempts: {max_total_attempts}")
        
        # Elite preservation: check if enabled in config and preserve best variant
        current_iteration = enhanced_context.get('iteration_context', {}).get('current_iteration', 1)
        elite_preservation_enabled = self.config.get('llm_config', {}).get('elite_preservation', False)
        
        self.logger.info(f"Elite preservation enabled: {elite_preservation_enabled}")
        
        if current_iteration > 1 and elite_variants and elite_preservation_enabled:
            # Sort elite variants by performance (best first)
            elite_variants_sorted = sorted(elite_variants, key=lambda v: getattr(v, 'performance_rank', float('inf')))
            best_variant = elite_variants_sorted[0]
            
            self.logger.info(f"ELITE PRESERVATION: Preserving best variant {best_variant.variant_id}")
            
            # Add the elite variant directly to successful variants (no regeneration)
            elite_dict = {
                'code': best_variant.code,
                'variant_id': best_variant.variant_id,  # Keep original ID for tracking
                'parent': best_variant.parent_id,
                'strategy': 'elite_preserved',
                'fingerprint': best_variant.fingerprint,
                'executable': None,  # Will be set during processing in R
                'compilation_success': True,  # Assume preserved variants were successfully compiled
                'generation_strategy': 'elite_preserved'
            }
            successful_variants.append(elite_dict)
            self.logger.info(f"Elite variant preserved: {elite_dict['variant_id']}")
            
            # Remove the preserved variant from the evolution pool
            elite_variants = [v for v in elite_variants if v.variant_id != best_variant.variant_id]
            self.logger.info(f"Remaining variants for evolution: {len(elite_variants)}")
        
        while len(successful_variants) < target_variants and total_attempts < max_total_attempts:
            self.logger.info(f"=== Attempt {total_attempts + 1}/{max_total_attempts} ===")
            self.logger.info(f"Current successful variants: {len(successful_variants)}/{target_variants}")
            
            try:
                # Select strategy for this variant
                self.logger.info("Selecting strategy...")
                strategy = self._select_strategy(len(successful_variants), context)
                self.logger.info(f"Selected strategy: {strategy}")
                
                # Generate code variant
                self.logger.info("Generating single variant...")
                variant = self._generate_single_variant(
                    elite_variants, enhanced_context, strategy, total_attempts
                )
                self.logger.info(f"Generated variant: {variant.variant_id}")
                
                # Attempt to compile with intelligent error correction
                self.logger.info(f"Compiling variant {variant.variant_id}...")
                compilation_success = self._compile_variant_with_error_correction(
                    variant, elite_variants, context, strategy, total_attempts
                )
                
                if compilation_success:
                    successful_variants.append(variant.to_dict())
                    self.generated_variants.append(variant)
                    self.logger.info(f"Variant {variant.variant_id} compiled successfully")
                else:
                    self.failed_variants.append(variant)
                    self.logger.warning(f"Variant {variant.variant_id} compilation failed after error correction attempts")
                
            except Exception as e:
                self.logger.error(f"Error generating variant on attempt {total_attempts + 1}: {type(e).__name__}: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            total_attempts += 1
            self.logger.info(f"Completed attempt {total_attempts}. Moving to next...")
            self.logger.info("=" * 50)
        
        # Fallback: if too few successful variants, use conservative variants
        if len(successful_variants) < max(1, target_variants // 2):
            fallback_variants = self._generate_fallback_variants(
                elite_variants, target_variants - len(successful_variants)
            )
            successful_variants.extend(fallback_variants)
        
        # Get LLM metrics
        llm_metrics = self.llm_service.get_metrics()
        
        self.logger.info(f"Generated {len(successful_variants)} successful variants out of {total_attempts} attempts")
        self.logger.info(f"LLM Metrics - Calls: {llm_metrics['total_calls']}, "
                        f"Retries: {llm_metrics['total_retries']}, "
                        f"Tokens: {llm_metrics['total_input_tokens']}+{llm_metrics['total_output_tokens']}, "
                        f"Cost: ${llm_metrics['total_cost_estimate']:.3f}")
        
        # Save performance metrics for next iteration's dynamic prompting
        current_iteration = enhanced_context['iteration_context']['current_iteration']
        current_performance_data = {
            'iteration': current_iteration,
            'total_variants_generated': len(successful_variants),
            'llm_calls': llm_metrics['total_calls'],
            'successful_strategies': [v['strategy'] for v in successful_variants],
            'generation_timestamp': time.time()
            # Note: best_performance will be added later by irace based on racing results
        }
        
        try:
            save_iteration_performance(enhanced_context.get('scenario_config', {}), current_performance_data)
            self.logger.info(f"Saved performance data for iteration {current_iteration}")
        except Exception as e:
            self.logger.warning(f"Failed to save performance data: {e}")
        
        return successful_variants, llm_metrics
    
    def _get_elite_variants(self, context: Dict[str, Any]) -> List[CodeVariant]:
        """Extract elite variants from context with elite preservation"""
        current_iteration = context['iteration_context']['current_iteration']
        self.logger.info(f"Getting elite variants for iteration {current_iteration} with elite preservation")
        
        # For first iteration, use original source
        if current_iteration <= 1:
            self.logger.info("First iteration detected, loading original source...")
            return [self._load_original_source()]
        
        # Load variants from previous iterations with performance ranking
        all_variants = []
        elite_variants = []
        
        # Get performance rankings from context
        elite_configs = context.get('elite_configurations', [])
        performance_stats = context.get('performance_stats', {})
        elite_rankings = performance_stats.get('elite_rankings', [])
        
        self.logger.info(f"Elite configurations count: {len(elite_configs)}")
        self.logger.info(f"Elite rankings: {elite_rankings}")
        
        # Try to load source files from previous iterations
        source_dir = "./irace-evo-sources"
        if os.path.exists(source_dir):
            self.logger.info(f"Looking for source files from previous iterations in {source_dir}")
            
            # Load variants from the most recent iteration first (better performance data)
            prev_iter = current_iteration - 1
            pattern = f"variant_*_iter{prev_iter}.cpp"
            import glob
            iter_files = glob.glob(os.path.join(source_dir, pattern))
            
            # Create a mapping of variant performance
            variant_performance = {}
            if elite_configs:
                self.logger.info(f"Elite configs type: {type(elite_configs)}")
                self.logger.info(f"Elite configs content: {elite_configs}")
                
                # Handle different data structures from R
                try:
                    if isinstance(elite_configs, list):
                        for config in elite_configs:
                            if isinstance(config, dict):
                                variant_name = config.get('.VARIANT.', config.get('VARIANT', 'original'))
                                rank = config.get('.RANK.', config.get('RANK', float('inf')))
                            else:
                                # Handle R data frame row-like structure
                                continue
                            
                            if variant_name != 'original' and variant_name:
                                if variant_name not in variant_performance or rank < variant_performance[variant_name]:
                                    variant_performance[variant_name] = rank
                    elif isinstance(elite_configs, dict):
                        # Handle case where elite_configs is a dictionary with column names as keys
                        variants = elite_configs.get('.VARIANT.', elite_configs.get('VARIANT', []))
                        ranks = elite_configs.get('.RANK.', elite_configs.get('RANK', []))
                        
                        if isinstance(variants, list) and isinstance(ranks, list):
                            for variant_name, rank in zip(variants, ranks):
                                if variant_name != 'original' and variant_name:
                                    if variant_name not in variant_performance or rank < variant_performance[variant_name]:
                                        variant_performance[variant_name] = rank
                except Exception as e:
                    self.logger.warning(f"Error processing elite configs: {e}")
                    variant_performance = {}  # Fallback to empty mapping
            
            self.logger.info(f"Variant performance mapping: {variant_performance}")
            
            # Load variants with their performance info
            for file_path in iter_files:
                try:
                    with open(file_path, 'r') as f:
                        source_code = f.read()
                    
                    # Extract variant ID from filename
                    filename = os.path.basename(file_path)
                    variant_id = filename.replace('.cpp', '')
                    
                    # Get performance ranking for this variant (lower is better)
                    performance_rank = variant_performance.get(variant_id, float('inf'))
                    
                    variant = CodeVariant(
                        code=source_code,
                        variant_id=variant_id,
                        parent_id=f"iter{prev_iter}",
                        strategy="previous_elite" if performance_rank <= 3 else "previous_variant"
                    )
                    # Store performance info for sorting
                    variant.performance_rank = performance_rank
                    all_variants.append(variant)
                    self.logger.info(f"Loaded variant: {variant_id} with rank {performance_rank}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load variant from {file_path}: {e}")
            
            # Sort variants by performance (best first)
            all_variants.sort(key=lambda v: getattr(v, 'performance_rank', float('inf')))
            
            # Implement elite preservation strategy
            if all_variants:
                # Always preserve the best variant (elite preservation)
                best_variant = all_variants[0]
                elite_variants.append(best_variant)
                self.logger.info(f"ELITE PRESERVED: {best_variant.variant_id} (rank: {getattr(best_variant, 'performance_rank', 'unknown')})")
                
                # Add other variants for evolution (can be replaced)
                for variant in all_variants[1:]:
                    elite_variants.append(variant)
                    self.logger.info(f"Available for evolution: {variant.variant_id} (rank: {getattr(variant, 'performance_rank', 'unknown')})")
        
        # If we found elite variants, return them; otherwise fallback to original
        if elite_variants:
            self.logger.info(f"Found {len(elite_variants)} variants with elite preservation")
            return elite_variants
        else:
            self.logger.info("No elite variants found, using original source as fallback...")
            return [self._load_original_source()]
    
    def _load_original_source(self) -> CodeVariant:
        """Load the original source code as base variant"""
        self.logger.info("Loading original source code...")
        
        source_config = self.config.get('source_config', {})
        source_file = source_config.get('source_file')
        self.logger.info(f"Source file configured as: {source_file}")
        
        if not source_file:
            raise ValueError("No source file specified in configuration")
            
        if not os.path.exists(source_file):
            self.logger.error(f"Source file does not exist: {source_file}")
            # Try to check current working directory
            cwd = os.getcwd()
            self.logger.info(f"Current working directory: {cwd}")
            abs_path = os.path.abspath(source_file)
            self.logger.info(f"Absolute path would be: {abs_path}")
            raise FileNotFoundError(f"Source file not found: {source_file}")
        
        self.logger.info(f"Reading source file: {source_file}")
        with open(source_file, 'r') as f:
            source_code = f.read()
        
        self.logger.info(f"Source code loaded successfully. Length: {len(source_code)} chars")
        
        return CodeVariant(
            code=source_code,
            variant_id="original", 
            parent_id=None,
            strategy="original"
        )
    
    def _select_strategy(self, variant_index: int, context: Dict[str, Any]) -> str:
        """Select strategy for generating this variant"""
        available_strategies = list(self.strategies.keys())
        
        # Safety check for empty strategies list
        if not available_strategies:
            self.logger.error("No strategies available! Using fallback strategy.")
            # Fallback to all builtin strategies if filtered list is empty
            from strategies import BUILTIN_STRATEGIES
            available_strategies = list(BUILTIN_STRATEGIES.keys())
            if not available_strategies:
                raise RuntimeError("No builtin strategies found!")
            self.strategies = BUILTIN_STRATEGIES.copy()
        
        self.logger.info(f"Available strategies for selection: {available_strategies}")
        # Simple round-robin for now
        # TODO: Implement adaptive strategy selection
        selected = available_strategies[variant_index % len(available_strategies)]
        self.logger.info(f"Selected strategy: {selected}")
        return selected
    
    def _generate_single_variant(self, elite_variants: List[CodeVariant], 
                                context: Dict[str, Any], strategy: str, 
                                attempt: int) -> CodeVariant:
        """Generate a single code variant using LLM"""
        self.logger.info(f"Starting _generate_single_variant for attempt {attempt}")
        
        # Select base variant (parent)
        self.logger.info(f"Selecting base variant from {len(elite_variants)} elite variants...")
        base_variant = elite_variants[attempt % len(elite_variants)]
        self.logger.info(f"Selected base variant: {base_variant.variant_id}")
        
        # Get function name (always needed)
        function_name = self.config['source_config']['function_name']
        
        # Determine if this is the first variant generation or a retry
        is_first_variant = (attempt == 0)
        
        if is_first_variant:
            # First variant: Give LLM the complete source code for full context
            self.logger.info("First variant: Using complete source code for maximum context")
            original_function = base_variant.code  # Full code
            context_code = "// Complete source code provided above"
            full_context_mode = True
        else:
            # Subsequent variants: Extract only the specific function  
            self.logger.info("Subsequent variant: Using function-only approach for efficiency")
            self.logger.info(f"Extracting function '{function_name}' from source code...")
            original_function = self._extract_function(base_variant.code, function_name)
            self.logger.info(f"Extracted function. Length: {len(original_function)} chars")
            
            # Extract context information (data structures, global variables, etc.)
            context_code = self._extract_context_information(base_variant.code)
            self.logger.info(f"Extracted context information. Length: {len(context_code)} chars")
            full_context_mode = False
        
        
        # Prepare prompt
        self.logger.info("Preparing prompt data for LLM...")
        prompt_data = {
            'original_function': original_function,
            'context_code': context_code,
            'full_context_mode': full_context_mode,
            'function_name': function_name,
            'strategy': strategy,
            'strategy_context': self.strategies[strategy],
            'iteration_context': context['iteration_context'],
            'performance_stats': context['performance_stats'],
            'improvement_guidance': context.get('improvement_guidance', {}),
            'problem_context': self.config.get('problem_context', {}),
            'variant_number': attempt + 1,
            'previous_variants': [v.strategy for v in self.generated_variants[-3:]],  # Last 3 for diversity
            'previous_functions': [self._extract_function(v.code, self.config['source_config']['function_name']) 
                                 for v in self.generated_variants[-3:] if v.code],  # Actual function code for diversity
            # Add performance context for dynamic prompting
            'elite_configs': context.get('elite_configs', []),
            'iteration_history': context.get('iteration_history', [])
        }
        self.logger.info("Prompt data prepared successfully")
        
        # Generate new function
        self.logger.info("Calling LLM service to generate function variant...")
        new_function = self.llm_service.generate_function_variant(prompt_data)
        self.logger.info(f"LLM returned new function. Length: {len(new_function)} chars")
        
        # Replace function in source code
        self.logger.info("Replacing function in source code...")
        new_source = self._replace_function(base_variant.code, function_name, new_function)
        self.logger.info(f"Function replaced. New source length: {len(new_source)} chars")
        
        variant_id = f"var_{attempt:03d}_{strategy[:4]}"
        self.logger.info(f"Created variant with ID: {variant_id}")
        
        return CodeVariant(
            code=new_source,
            variant_id=variant_id,
            parent_id=base_variant.variant_id,
            strategy=strategy
        )
    
    def _extract_function(self, source_code: str, function_name: str) -> str:
        """Extract specific function using language-specific handler"""
        self.logger.info(f"Starting function extraction for '{function_name}'")
        self.logger.info(f"Source code length: {len(source_code)} characters")
        
        try:
            result = self.language_handler.extract_function(source_code, function_name)
            self.logger.info(f"Function extraction completed. Extracted function length: {len(result)} characters")
            return result
        except Exception as e:
            self.logger.error(f"Function extraction failed: {type(e).__name__}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _extract_context_information(self, source_code: str) -> str:
        """Extract relevant context information from source code"""
        context_parts = []
        
        # Extract struct definitions
        struct_matches = []
        lines = source_code.split('\n')
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Look for struct definitions
            if line_stripped.startswith('struct ') or line_stripped.startswith('class '):
                struct_name = line_stripped.split()[1].split('{')[0].split(':')[0]
                
                # Extract the full struct definition
                brace_count = line.count('{') - line.count('}')
                struct_lines = [line]
                
                j = i + 1
                while j < len(lines) and brace_count > 0:
                    struct_lines.append(lines[j])
                    brace_count += lines[j].count('{') - lines[j].count('}')
                    j += 1
                
                struct_definition = '\n'.join(struct_lines)
                struct_matches.append(struct_definition)
        
        if struct_matches:
            context_parts.append("// Data structures used in the algorithm:")
            context_parts.extend(struct_matches)
        
        # Extract global variables and constants
        global_vars = []
        for line in lines:
            line_stripped = line.strip()
            # Look for global variables (simple heuristic)
            if (line_stripped.startswith('vector<') or 
                line_stripped.startswith('int ') or 
                line_stripped.startswith('double ') or
                line_stripped.startswith('const ')) and ';' in line and '(' not in line:
                global_vars.append(line)
        
        if global_vars:
            context_parts.append("\n// Global variables and constants:")
            context_parts.extend(global_vars)
        
        # Extract relevant includes
        includes = []
        for line in lines[:20]:  # Check first 20 lines for includes
            if line.strip().startswith('#include'):
                includes.append(line.strip())
        
        if includes:
            context_parts.append("\n// Required includes:")
            context_parts.extend(includes)
        
        return '\n'.join(context_parts) if context_parts else "// No additional context found"
    
    def _replace_function(self, source_code: str, function_name: str, new_function: str) -> str:
        """Replace function in source code using language-specific handler"""
        return self.language_handler.replace_function(source_code, function_name, new_function)
    
    def _compile_variant(self, variant: CodeVariant) -> bool:
        """Attempt to compile a code variant using language-specific handler"""
        try:
            # Use language handler for compilation
            executable_path = self.language_handler.compile_and_test(
                variant.code,
                output_name=f"algorithm_{variant.variant_id}"
            )
            
            variant.executable_path = executable_path
            variant.compilation_success = True
            return True
            
        except Exception as e:
            variant.compilation_errors.append(str(e))
            variant.compilation_success = False
            self.logger.error(f"Compilation failed for {variant.variant_id}: {e}")
            return False
    
    def _compile_variant_with_error_correction(self, variant: CodeVariant, 
                                             elite_variants: List[CodeVariant],
                                             context: Dict[str, Any], strategy: str, 
                                             attempt: int) -> bool:
        """
        Attempt to compile a variant with intelligent error correction
        
        Args:
            variant: The variant to compile
            elite_variants: Elite variants for context
            context: Generation context
            strategy: Strategy used to generate the variant
            attempt: Current attempt number
            
        Returns:
            True if compilation successful (possibly after correction), False otherwise
        """
        # Get error correction settings from configuration
        intelligent_correction = self.evolution_config.get('intelligent_error_correction', True)
        max_correction_attempts = self.evolution_config.get('max_error_correction_attempts', 2)
        
        # If intelligent correction is disabled, use simple compilation
        if not intelligent_correction:
            return self._compile_variant(variant)
        
        for correction_attempt in range(max_correction_attempts + 1):
            if correction_attempt == 0:
                self.logger.info(f"Attempting initial compilation of {variant.variant_id}")
            else:
                self.logger.info(f"Attempting error correction #{correction_attempt} for {variant.variant_id}")
            
            # Try to compile current code
            compilation_success = self._compile_variant(variant)
            
            if compilation_success:
                if correction_attempt > 0:
                    self.logger.info(f"Error correction successful for {variant.variant_id} after {correction_attempt} attempts")
                return True
            
            # If compilation failed and we still have correction attempts left
            if correction_attempt < max_correction_attempts and variant.compilation_errors:
                self.logger.info(f"Compilation failed, attempting LLM error correction...")
                
                try:
                    # Get the latest compilation error
                    compilation_error = variant.compilation_errors[-1]
                    
                    # Prepare context for error correction
                    correction_context = self._prepare_error_correction_context(
                        context, variant, strategy, elite_variants
                    )
                    
                    # Get corrected code from LLM
                    self.logger.info("Calling LLM for error correction...")
                    corrected_function = self.llm_service.fix_compilation_error(
                        faulty_code=self._extract_function(variant.code, 
                                                          self.config['source_config']['function_name']),
                        compilation_error=compilation_error,
                        original_context=correction_context
                    )
                    
                    # Replace function in the variant's source code
                    function_name = self.config['source_config']['function_name']
                    base_variant = elite_variants[0] if elite_variants else variant
                    corrected_source = self._replace_function(
                        base_variant.code, function_name, corrected_function
                    )
                    
                    # Update variant with corrected code
                    variant.code = corrected_source
                    variant.compilation_errors = []  # Reset errors for new attempt
                    variant.strategy = f"{strategy}_corrected_{correction_attempt}"
                    
                    self.logger.info(f"Generated corrected code for {variant.variant_id}")
                    
                except Exception as e:
                    self.logger.error(f"Error correction failed for {variant.variant_id}: {e}")
                    # Continue to next correction attempt or exit loop
                    continue
            else:
                # No more correction attempts or no errors to work with
                break
        
        # All attempts exhausted
        self.logger.error(f"Failed to compile {variant.variant_id} after {max_correction_attempts} error correction attempts")
        return False
    
    def _prepare_error_correction_context(self, original_context: Dict[str, Any],
                                        variant: CodeVariant, strategy: str,
                                        elite_variants: List[CodeVariant]) -> Dict[str, Any]:
        """Prepare context specifically for error correction"""
        
        correction_context = original_context.copy()
        
        # Add error correction specific information
        correction_context.update({
            'function_purpose': f"Optimization function using {strategy} strategy",
            'variant_info': {
                'variant_id': variant.variant_id,
                'original_strategy': strategy,
                'compilation_errors': variant.compilation_errors
            },
            'error_correction_attempt': True
        })
        
        return correction_context
    
    def _generate_fallback_variants(self, elite_variants: List[CodeVariant], 
                                   needed: int) -> List[Dict[str, Any]]:
        """Generate conservative fallback variants when main generation fails"""
        fallback_variants = []
        
        # Use original source with minimal modifications
        if elite_variants:
            base = elite_variants[0]  # Use original source
            
            for i in range(needed):
                # Create minimal variation (e.g., different variable names)
                variant = CodeVariant(
                    code=base.code,  # For now, just use original
                    variant_id=f"fallback_{i:02d}",
                    parent_id=base.variant_id,
                    strategy="fallback"
                )
                
                if self._compile_variant(variant):
                    fallback_variants.append(variant.to_dict())
                
                if len(fallback_variants) >= needed:
                    break
        
        return fallback_variants