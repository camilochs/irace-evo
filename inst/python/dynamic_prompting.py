"""
Dynamic Prompting Module for irace-evo

Adapts LLM prompts based on performance gaps and iteration history to focus
evolution attention on poorly performing areas.

Author: Camilo Chacón Sartori
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import numpy as np

class PerformanceAnalyzer:
    """Analyzes performance gaps and patterns from iteration history"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def analyze_performance_gaps(self, elite_configs: List[Dict], iteration_history: List[Dict]) -> Dict[str, Any]:
        """
        Analyze performance gaps and identify areas needing focused evolution
        
        Args:
            elite_configs: Current elite configurations from irace
            iteration_history: Previous iterations' performance data
            
        Returns:
            Dictionary with performance analysis and focus areas
        """
        analysis = {
            'performance_gaps': {},
            'stagnant_areas': [],
            'promising_directions': [],
            'focus_recommendations': []
        }
        
        if not iteration_history or len(iteration_history) < 2:
            # Not enough history for analysis
            analysis['focus_recommendations'].append('general_improvement')
            return analysis
        
        # Analyze performance trends
        performance_trends = self._analyze_trends(iteration_history)
        analysis['performance_gaps'] = performance_trends
        
        # Identify stagnant areas (no improvement for N iterations)
        stagnant_threshold = self.config.get('stagnation_threshold', 3)
        analysis['stagnant_areas'] = self._identify_stagnant_areas(
            iteration_history, stagnant_threshold
        )
        
        # Find promising directions from recent improvements
        analysis['promising_directions'] = self._identify_promising_directions(
            iteration_history
        )
        
        # Generate focus recommendations
        analysis['focus_recommendations'] = self._generate_focus_recommendations(
            performance_trends, analysis['stagnant_areas'], analysis['promising_directions']
        )
        
        return analysis
    
    def _analyze_trends(self, iteration_history: List[Dict]) -> Dict[str, float]:
        """Analyze performance trends across iterations"""
        trends = {}
        
        # Extract performance metrics from each iteration
        recent_iterations = iteration_history[-5:]  # Last 5 iterations
        
        if len(recent_iterations) < 2:
            return trends
        
        # Calculate improvement rates with robust error handling
        for i in range(1, len(recent_iterations)):
            try:
                prev_best = recent_iterations[i-1].get('best_performance', float('inf'))
                curr_best = recent_iterations[i].get('best_performance', float('inf'))
                
                # Ensure we have valid numeric values
                if (isinstance(prev_best, (int, float)) and isinstance(curr_best, (int, float)) and
                    prev_best != float('inf') and curr_best != float('inf') and 
                    prev_best != 0):  # Avoid division by zero
                    improvement_rate = (prev_best - curr_best) / prev_best
                    trends[f'iteration_{i}'] = improvement_rate
            except (TypeError, ValueError, ZeroDivisionError) as e:
                # Skip invalid data points
                self.logger.warning(f"Skipping invalid performance data at iteration {i}: {e}")
                continue
        
        # Calculate average improvement trend
        if trends:
            trends['avg_improvement_rate'] = np.mean(list(trends.values()))
            trends['improvement_volatility'] = np.std(list(trends.values()))
        
        return trends
    
    def _identify_stagnant_areas(self, iteration_history: List[Dict], threshold: int) -> List[str]:
        """Identify areas with no significant improvement"""
        stagnant_areas = []
        
        if len(iteration_history) < threshold:
            return stagnant_areas
        
        # Extract and filter valid performance values
        recent_best = []
        for it in iteration_history[-threshold:]:
            perf = it.get('best_performance', float('inf'))
            # Only include valid numeric values
            if isinstance(perf, (int, float)) and perf != float('inf'):
                recent_best.append(perf)
        
        # Check if performance has plateaued
        improvement_threshold = 0.01  # 1% improvement threshold
        if len(recent_best) < 2:
            return stagnant_areas  # Not enough valid data
            
        max_performance = min(recent_best) if recent_best else float('inf')
        min_recent = min(recent_best[-threshold//2:]) if len(recent_best) >= threshold//2 else float('inf')
        
        if max_performance != float('inf') and min_recent != float('inf'):
            recent_improvement = (max_performance - min_recent) / max_performance
            if abs(recent_improvement) < improvement_threshold:
                stagnant_areas.append('overall_performance')
        
        return stagnant_areas
    
    def _identify_promising_directions(self, iteration_history: List[Dict]) -> List[str]:
        """Identify promising directions from recent successes"""
        promising = []
        
        if len(iteration_history) < 2:
            return promising
        
        # Look at successful strategies from recent iterations
        recent_iterations = iteration_history[-3:]
        
        for iteration in recent_iterations:
            successful_strategies = iteration.get('successful_strategies', [])
            for strategy in successful_strategies:
                if strategy not in promising:
                    promising.append(strategy)
        
        return promising
    
    def _generate_focus_recommendations(self, trends: Dict, stagnant_areas: List, 
                                      promising_directions: List) -> List[str]:
        """Generate specific focus recommendations for prompt adaptation"""
        recommendations = []
        
        # Check improvement rate
        avg_improvement = trends.get('avg_improvement_rate', 0)
        
        if avg_improvement < 0.01:  # Less than 1% improvement
            recommendations.append('aggressive_exploration')
            
        if 'overall_performance' in stagnant_areas:
            recommendations.append('paradigm_shift')
            recommendations.append('hybrid_approaches')
            
        if promising_directions:
            recommendations.append('exploit_promising_directions')
            
        # Default recommendation if nothing specific identified
        if not recommendations:
            recommendations.append('balanced_exploration')
            
        return recommendations


class DynamicPromptBuilder:
    """Builds adaptive prompts based on performance analysis"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.analyzer = PerformanceAnalyzer(config)
        
        # Load focus-specific prompt templates
        self.focus_templates = self._load_focus_templates()
        
    def _load_focus_templates(self) -> Dict[str, str]:
        """Load different prompt templates for different focus areas"""
        templates = {
            'general_improvement': """
    ## EVOLUTION FOCUS: General Algorithm Improvement (HIGH EFFICIENCY)
    Your goal is to create **lightweight, high-throughput heuristics** to enhance the algorithm's core logic.
    Focus on **minimizing computational overhead** and maximizing operations per second.
    The primary metric is **speed per iteration**.
    """,
            
            'aggressive_exploration': """
    ## EVOLUTION FOCUS: Aggressive Exploration (MINIMALIST HEURISTICS)
    The algorithm has stagnated. Explore radically different but **computationally cheap** approaches.
    CRITICAL: Avoid any complex logic. Focus on **simple, atomic operations** that enable a higher number of iterations.
    Consider novel heuristics or entirely different strategies, but they must be **faster to compute** than current ones.
    """,
            
            'paradigm_shift': """
    ## EVOLUTION FOCUS: Paradigm Shift (EXTREME EFFICIENCY)
    Current approaches are not yielding improvements. Propose fundamentally different but **ultra-efficient** paradigms:
    - Use data structures with **O(1) access time** only.
    - Implement **single-pass algorithms** that avoid state changes or recursive calls.
    - Decompose the problem into **independent, non-recursive sub-problems**.
    - Use simple arithmetic or bitwise operations for weighting.
    CRITICAL: Every new approach must have a lower Big O complexity than existing ones.
    """,
            
            'exploit_promising_directions': """
    ## EVOLUTION FOCUS: Exploit Promising Directions (SIMPLIFY FOR SPEED)
    Recent iterations show promising patterns. Build on these successes by **aggressively reducing computational cost**:
    - Refactor successful heuristics to remove **non-essential logic**.
    - Combine approaches using basic arithmetic or **precomputed look-up tables**.
    - Optimize components by replacing complex calculations with **simple approximations**.
    CONSTRAINT: Make successful approaches even faster and simpler by **removing computational bloat**.
    """,
            
            'hybrid_approaches': """
    ## EVOLUTION FOCUS: Hybrid Algorithm Development (HIGH-THROUGHPUT COMBINATIONS)
    Combine multiple simple algorithmic approaches for better throughput:
    - Integrate different optimization strategies with **low-cost weighting mechanisms**.
    - AVOID complex ensemble methods or multi-stage pipelines (high overhead).
    - Combine techniques in a **single-pass, stateless manner**.
    """,
            
            'balanced_exploration': """
    ## EVOLUTION FOCUS: Balanced Exploration and Exploitation (SPEED FIRST)
    Maintain a balance between improving current approaches and exploring **computationally cheap** new directions.
    Make meaningful but **fast-to-compute** improvements that increase algorithm throughput.
    CONSTRAINT: All changes must **reduce the time per iteration** and enable more total iterations within a given time budget.
    """
        }
        return templates
        
    def build_adaptive_prompt(self, base_template: str, prompt_data: Dict[str, Any], 
                            elite_configs: List[Dict], iteration_history: List[Dict]) -> str:
        """
        Build an adaptive prompt based on performance analysis
        
        Args:
            base_template: Original prompt template
            prompt_data: Standard prompt data
            elite_configs: Current elite configurations
            iteration_history: Performance history from previous iterations
            
        Returns:
            Adapted prompt with performance-based focus
        """
        
        # Analyze performance to determine focus areas
        performance_analysis = self.analyzer.analyze_performance_gaps(
            elite_configs, iteration_history
        )
        
        # Select primary focus based on recommendations
        focus_recommendations = performance_analysis['focus_recommendations']
        primary_focus = focus_recommendations[0] if focus_recommendations else 'general_improvement'
        
        # Log dynamic prompting activation
        self.logger.info(f"🎯 DYNAMIC PROMPTING ACTIVATED - Focus: '{primary_focus}'")
        if len(iteration_history) > 0:
            latest_iteration = max(it.get('iteration', 0) for it in iteration_history)
            self.logger.info(f"📊 Performance Analysis: {len(iteration_history)} iterations analyzed (latest: {latest_iteration})")
        
        # Get focus-specific template addition
        focus_template = self.focus_templates.get(primary_focus, self.focus_templates['general_improvement'])
        
        # Build performance context section
        performance_context = self._build_performance_context(performance_analysis, iteration_history)
        
        # Create enhanced prompt data with performance insights
        enhanced_prompt_data = prompt_data.copy()
        enhanced_prompt_data.update({
            'performance_focus': focus_template,
            'performance_context': performance_context,
            'focus_area': primary_focus,
            'iteration_insights': self._build_iteration_insights(iteration_history)
        })
        
        # Build the complete adaptive prompt with error handling
        try:
            adaptive_prompt = f"""{focus_template}

{performance_context}

{base_template}

## PERFORMANCE-DRIVEN GUIDANCE
Based on recent performance analysis, pay special attention to:
{self._build_specific_guidance(performance_analysis, primary_focus)}
"""
        except KeyError as e:
            # Fallback if template variables are missing
            self.logger.warning(f"Template variable missing: {e}. Using base template.")
            adaptive_prompt = base_template
        
        # Log the adaptation decision
        self.logger.info(f"Dynamic prompting: Applied focus '{primary_focus}' based on performance analysis")
        
        return adaptive_prompt
        
    def _build_performance_context(self, analysis: Dict[str, Any], history: List[Dict]) -> str:
        """Build performance context section for the prompt"""
        context_parts = []
        
        # Add trend information
        trends = analysis.get('performance_gaps', {})
        if trends:
            avg_improvement = trends.get('avg_improvement_rate', 0)
            context_parts.append(f"Recent performance trend: {avg_improvement:.3f} average improvement rate")
        
        # Add stagnation information
        stagnant_areas = analysis.get('stagnant_areas', [])
        if stagnant_areas:
            context_parts.append(f"Stagnant areas identified: {', '.join(stagnant_areas)}")
        
        # Add promising directions
        promising = analysis.get('promising_directions', [])
        if promising:
            context_parts.append(f"Promising directions: {', '.join(promising)}")
            
        if not context_parts:
            context_parts.append("Limited performance history available - focus on general improvements")
        
        return "## PERFORMANCE CONTEXT\n" + "\n".join(f"- {part}" for part in context_parts)
    
    def _build_iteration_insights(self, history: List[Dict]) -> str:
        """Build insights from iteration history"""
        if not history:
            return "No previous iteration data available"
            
        insights = []
        
        # Recent performance
        if len(history) >= 1:
            latest = history[-1]
            best_perf = latest.get('best_performance')
            if best_perf is not None:
                insights.append(f"Latest best performance: {best_perf}")
        
        # Performance progression
        if len(history) >= 3:
            recent_perfs = [it.get('best_performance') for it in history[-3:] if it.get('best_performance') is not None]
            if len(recent_perfs) >= 2:
                trend = "improving" if recent_perfs[-1] < recent_perfs[0] else "declining"
                insights.append(f"Recent trend: {trend}")
        
        return "Recent insights: " + " | ".join(insights) if insights else "No specific insights available"
    
    def _build_specific_guidance(self, analysis: Dict[str, Any], focus_area: str) -> str:
        """Build specific guidance based on performance analysis"""
        guidance_parts = []
        
        if focus_area == 'aggressive_exploration':
            guidance_parts.extend([
                "- Consider simpler data structures with faster access patterns", 
                "- Experiment with novel but LIGHTWEIGHT heuristics (avoid nested loops)"
            ])
        elif focus_area == 'exploit_promising_directions':
            promising = analysis.get('promising_directions', [])
            if promising:
                guidance_parts.append(f"- Build upon these successful strategies: {', '.join(promising)}")
            guidance_parts.extend([
                "- Refine and SIMPLIFY the most effective components (remove overhead)",
            ])
        elif focus_area == 'paradigm_shift':
            guidance_parts.extend([
                "- Consider completely different BUT SIMPLE problem-solving paradigms", 
                "- Try hybrid approaches combining different techniques"
            ])
        else:
            guidance_parts.extend([
                "- Find a new heuristic for this problem"
            ])
            
        return "\n".join(guidance_parts)


def get_iteration_history(scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Load iteration history from previous irace-evo runs
    
    Args:
        scenario: irace scenario configuration
        
    Returns:
        List of previous iteration performance data
    """
    try:
        exec_dir = scenario.get('execDir', '.')
        history_file = os.path.join(exec_dir, '.irace_evo_history.json')
        
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                return json.load(f)
        else:
            return []
            
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to load iteration history: {e}")
        return []


def save_iteration_performance(scenario: Dict[str, Any], iteration_data: Dict[str, Any]):
    """
    Save current iteration performance to history
    
    Args:
        scenario: irace scenario configuration
        iteration_data: Current iteration performance data
    """
    try:
        exec_dir = scenario.get('execDir', '.')
        history_file = os.path.join(exec_dir, '.irace_evo_history.json')
        
        # Load existing history
        history = get_iteration_history(scenario)
        
        # Add current iteration
        history.append(iteration_data)
        
        # Keep only last N iterations to prevent file from growing too large
        max_history = 20
        if len(history) > max_history:
            history = history[-max_history:]
        
        # Save updated history
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
            
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to save iteration history: {e}")