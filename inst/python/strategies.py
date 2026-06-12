"""
Built-in Strategies for irace-evo Code Evolution

Defines predefined strategies for LLM-based code generation and evolution.
Each strategy provides specific guidance for how to modify and improve algorithms.

Author: Camilo Chacón Sartori
"""

# Built-in strategies available across all languages
BUILTIN_STRATEGIES = {
  "improve_efficiency": {
    "name": "improve_efficiency",
    "description": "Refactor the code to enhance raw performance and reduce its fundamental algorithmic complexity.",
    "prompt_context": "Analyze and minimize time and space complexity. Introduce performance-enhancing patterns like memoization, efficient data structures, and smarter control flow to reduce computational waste.",
    "examples": [
      "Use memoization or caching for expensive function calls",
      "Replace list/array lookups with hash set/map lookups",
      "Flatten or optimize nested loops to reduce complexity",
      "Implement more aggressive early termination criteria",
      "Switch to more efficient data structures (e.g., priority queue, hash map)"
    ],
    "focus_areas": [
      "algorithmic_complexity",
      "memoization",
      "data_structures",
      "computational_overhead"
    ]
  },
  "add_randomization": {
    "name": "add_randomization",
    "description": "Inject stochastic elements to navigate the search space more effectively, enhancing exploration and preventing premature convergence on local optima.",
    "prompt_context": "Integrate randomness in a controlled manner. Consider techniques like random sampling, probabilistic decision-making (e.g., Simulated Annealing), random restarts, or noise injection to diversify the search process.",
    "examples": [
      "Implement a random restart mechanism after stagnation",
      "Use a probabilistic acceptance criterion (like in Simulated Annealing)",
      "Randomly select from a set of neighborhood operators",
      "Apply random perturbations to elite solutions",
      "Shuffle data processing order to avoid bias"
    ],
    "focus_areas": [
      "exploration_vs_exploitation",
      "diversification_mechanisms",
      "local_optima_escape",
      "stochastic_search"
    ]
  },
  "modify_logic": {
    "name": "modify_logic",
    "description": "Fundamentally alter the core logic or pivot to a new algorithmic paradigm to change how the solution space is explored.",
    "prompt_context": "Rethink the main algorithm. This could involve changing the search strategy (e.g., from greedy to local search), redesigning core operators, introducing new heuristics, or changing the problem's solution representation.",
    "examples": [
      "Switch from a constructive heuristic to an improvement heuristic",
      "Implement a completely different neighborhood structure",
      "Change the solution encoding (e.g., binary to permutation)",
      "Adopt a different metaheuristic framework (e.g., Tabu Search)",
      "Redesign the fitness evaluation function"
    ],
    "focus_areas": [
      "algorithmic_paradigm",
      "heuristic_design",
      "solution_representation",
      "search_operators"
    ]
  },
  
  "innovate_heuristic_design": {
    "name": "innovate_heuristic_design",
    "description": "Conceptualize, formulate, and develop a novel heuristic by deeply analyzing the problem's underlying structure, constraints, and objectives. The goal is to create a new, intelligent rule or guiding principle that enables more effective and efficient exploration of the solution space.",
    "prompt_context": "Act as an algorithmic research partner. Deconstruct the given optimization problem to identify its core decision points and bottlenecks. Analyze existing heuristics to understand their strengths and weaknesses. Synthesize insights from the problem's mathematical structure, domain-specific knowledge, or even analogies from other scientific fields (like physics or biology) to propose a brand-new heuristic. Invent a novel heuristic that preserves logical consistency, avoids syntactic errors, and differs meaningfully from known methods. Clearly define its logic, the data it requires, and the rationale for why it is expected to outperform existing methods.",
    "examples": [
      "Develop a 'regret-based' heuristic that prioritizes actions with the highest opportunity cost if not chosen immediately.",
      "Formulate a scoring function based on a novel composite metric, such as 'structural stability' or 'resource tension'.",
      "Design a look-ahead heuristic that simulates the short-term consequences of a decision across multiple conflicting objectives.",
      "Create a new heuristic inspired by a natural process, like crystal formation or flocking behavior, to guide the construction of a solution.",
      "Propose a dynamic heuristic that adapts its decision-making criteria based on the current state of the solution."
    ],
    "focus_areas": [
      "problem_decomposition_and_analysis",
      "feature_engineering_for_decision_making",
      "cross-domain_inspiration_and_analogy",
      "heuristic_logic_and_formulation",
      "performance_justification_and_rationale"
    ]
  },
  "conservative_improvement": {
    "name": "conservative_improvement",
    "description": "Apply low-risk, incremental changes to refine the algorithm's behavior without altering its core structure.",
    "prompt_context": "Focus on small, safe modifications that improve robustness, clarity, or produce marginal performance gains. This includes fine-tuning parameters, reordering safe operations, and adding defensive checks.",
    "examples": [
      "Fine-tune a learning rate or cooling schedule",
      "Adjust a probability threshold for an operator",
      "Add assertion checks for critical invariants",
      "Replace magic numbers with named constants",
      "Slightly reorder non-dependent operations for better cache locality"
    ],
    "focus_areas": [
      "incremental_refinement",
      "robustness",
      "parameter_tuning",
      "code_health"
    ]
  },
  "hybrid_approach": {
    "name": "hybrid_approach",
    "description": "Synergistically combine distinct algorithmic strategies to leverage their complementary strengths.",
    "prompt_context": "Design a multi-stage or integrated algorithm. Combine a global search method (like a Genetic Algorithm) with a powerful local search optimizer, or use a constructive heuristic to generate an initial solution before applying an improvement heuristic.",
    "examples": [
      "Use a greedy heuristic for an initial solution, then refine with local search",
      "Create a Memetic Algorithm (GA for global search + local search for intensification)",
      "Alternate between different neighborhood structures in a VNS framework",
      "Integrate a deterministic procedure within a stochastic metaheuristic",
      "Use an ensemble of different algorithms"
    ],
    "focus_areas": [
      "metaheuristic_integration",
      "exploration_intensification",
      "memetic_algorithms",
      "multi_stage_search"
    ]
  },
  "problem_specific": {
    "name": "problem_specific",
    "description": "Exploit the intrinsic structure and unique constraints of the specific problem to create a highly specialized and effective heuristic.",
    "prompt_context": "Go beyond generic algorithms. Deeply analyze the problem's mathematical properties, known constraints, and any available domain knowledge to design custom-tailored operators, bounds, or search procedures.",
    "examples": [
      "Design a custom crossover operator for a permutation problem",
      "Use problem-specific knowledge to prune the search space",
      "Leverage problem symmetries to reduce redundant exploration",
      "Use dynamic programming for optimal subproblems",
      "Create a specialized heuristic based on known properties of optimal solutions"
    ],
    "focus_areas": [
      "domain_expertise",
      "constraint_handling",
      "custom_heuristics",
      "structural_properties"
    ]
  }
}

# Language-specific strategy extensions
LANGUAGE_SPECIFIC_STRATEGIES = {
    "cpp": {
        "memory_optimization": {
            "name": "memory_optimization",
            "description": "Optimize memory usage and access patterns for C++",
            "prompt_context": "Focus on memory efficiency, cache-friendly access patterns, RAII principles, and smart pointer usage",
            "examples": [
                "use smart pointers instead of raw pointers",
                "optimize memory layout and access patterns", 
                "implement move semantics",
                "use stack allocation when possible",
                "minimize dynamic allocations"
            ],
            "focus_areas": [
                "memory_management",
                "cache_efficiency",
                "raii",
                "smart_pointers"
            ]
        },
        
        "stl_optimization": {
            "name": "stl_optimization", 
            "description": "Leverage STL containers and algorithms optimally",
            "prompt_context": "Use appropriate STL containers, algorithms, and modern C++ features for better performance",
            "examples": [
                "choose optimal STL containers",
                "use STL algorithms instead of manual loops",
                "leverage C++17/20 features",
                "use unordered containers when appropriate",
                "implement custom comparators"
            ],
            "focus_areas": [
                "stl_usage",
                "modern_cpp",
                "containers",
                "algorithms"
            ]
        }
    },
    
    "python": {
        "pythonic_optimization": {
            "name": "pythonic_optimization",
            "description": "Use Python-specific optimizations and idioms",
            "prompt_context": "Leverage Python's strengths: list comprehensions, generators, built-in functions, and libraries",
            "examples": [
                "use list/dict comprehensions",
                "implement generators for memory efficiency",
                "leverage built-in functions like map, filter",
                "use collections module effectively",
                "exploit NumPy for numerical operations"
            ],
            "focus_areas": [
                "pythonic_style",
                "comprehensions", 
                "generators",
                "built_ins"
            ]
        },
        
        "library_integration": {
            "name": "library_integration",
            "description": "Integrate powerful Python libraries for optimization",
            "prompt_context": "Use NumPy, SciPy, or other libraries to improve performance and functionality",
            "examples": [
                "use NumPy arrays for numerical computation",
                "leverage SciPy optimization functions",
                "use heapq for priority queues",
                "integrate multiprocessing for parallelism",
                "use itertools for efficient iterations"
            ],
            "focus_areas": [
                "numpy",
                "scipy",
                "standard_library",
                "performance_libraries"
            ]
        }
    },
    
    "java": {
        "object_oriented": {
            "name": "object_oriented",
            "description": "Leverage Java's OOP features and design patterns",
            "prompt_context": "Use inheritance, polymorphism, design patterns, and Java-specific optimizations",
            "examples": [
                "implement strategy pattern",
                "use inheritance for code reuse", 
                "leverage interfaces and polymorphism",
                "apply factory patterns",
                "use builder pattern for complex objects"
            ],
            "focus_areas": [
                "oop_design",
                "design_patterns",
                "inheritance",
                "interfaces"
            ]
        },
        
        "collections_optimization": {
            "name": "collections_optimization",
            "description": "Optimize using Java Collections Framework",
            "prompt_context": "Choose appropriate collections, use streams, and leverage Java 8+ features",
            "examples": [
                "use appropriate List/Set/Map implementations",
                "leverage Java 8 streams",
                "use parallel streams for parallelism", 
                "choose HashMap vs TreeMap appropriately",
                "implement custom Comparators"
            ],
            "focus_areas": [
                "collections_framework",
                "streams",
                "java8_features",
                "performance_tuning"
            ]
        }
    }
}


def get_available_strategies(language: str = None) -> dict:
    """
    Get available strategies for a specific language or all strategies
    
    Args:
        language: Programming language (optional)
        
    Returns:
        Dictionary of available strategies
    """
    strategies = BUILTIN_STRATEGIES.copy()
    
    if language and language.lower() in LANGUAGE_SPECIFIC_STRATEGIES:
        strategies.update(LANGUAGE_SPECIFIC_STRATEGIES[language.lower()])
    
    return strategies


def get_strategy_by_name(strategy_name: str, language: str = None) -> dict:
    """
    Get a specific strategy by name
    
    Args:
        strategy_name: Name of the strategy
        language: Programming language (optional)
        
    Returns:
        Strategy dictionary
        
    Raises:
        KeyError: If strategy not found
    """
    strategies = get_available_strategies(language)
    
    if strategy_name not in strategies:
        available = list(strategies.keys())
        raise KeyError(f"Strategy '{strategy_name}' not found. Available: {available}")
    
    return strategies[strategy_name]


def create_custom_strategy(name: str, description: str, prompt_context: str, 
                          examples: list = None, focus_areas: list = None) -> dict:
    """
    Create a custom strategy
    
    Args:
        name: Strategy name
        description: Strategy description
        prompt_context: Context for LLM prompts
        examples: List of example techniques
        focus_areas: List of focus areas
        
    Returns:
        Custom strategy dictionary
    """
    return {
        "name": name,
        "description": description,
        "prompt_context": prompt_context,
        "examples": examples or [],
        "focus_areas": focus_areas or [],
        "custom": True
    }


def validate_strategy(strategy: dict) -> bool:
    """
    Validate that a strategy has required fields
    
    Args:
        strategy: Strategy dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["name", "description", "prompt_context"]
    
    return all(field in strategy for field in required_fields)


# Strategy selection utilities
class StrategySelector:
    """Utility class for intelligent strategy selection"""
    
    def __init__(self, language: str = "cpp"):
        self.language = language
        self.strategies = get_available_strategies(language)
        
    def select_by_performance_trend(self, trend: str) -> str:
        """Select strategy based on performance trend"""
        strategy_map = {
            "improving": "conservative_improvement",
            "stagnating": "add_randomization", 
            "degrading": "modify_logic",
            "unknown": "improve_efficiency"
        }
        
        return strategy_map.get(trend, "improve_efficiency")
    
    def select_by_iteration(self, iteration: int, max_iterations: int = 10) -> str:
        """Select strategy based on iteration number"""
        progress = iteration / max_iterations
        
        if progress < 0.3:
            # Early iterations: explore different approaches
            return "modify_logic"
        elif progress < 0.7:
            # Middle iterations: optimize and add randomness
            return "improve_efficiency" if iteration % 2 == 0 else "add_randomization"
        else:
            # Late iterations: conservative improvements
            return "conservative_improvement"
    
    def select_adaptive(self, context: dict) -> str:
        """Adaptive strategy selection based on context"""
        # Extract context information
        iteration = context.get('iteration_context', {}).get('current_iteration', 1)
        max_iter = context.get('iteration_context', {}).get('max_iterations', 10)
        trend = context.get('performance_stats', {}).get('convergence_trend', 'unknown')
        
        # Combine different selection criteria
        trend_strategy = self.select_by_performance_trend(trend)
        iter_strategy = self.select_by_iteration(iteration, max_iter)
        
        # Weighted selection (favor trend-based selection)
        if trend != "unknown":
            return trend_strategy
        else:
            return iter_strategy


# Testing and utility functions
if __name__ == "__main__":
    print("Available built-in strategies:")
    for name, strategy in BUILTIN_STRATEGIES.items():
        print(f"- {name}: {strategy['description']}")
    
    print(f"\nC++ specific strategies:")
    cpp_strategies = get_available_strategies("cpp")
    for name in cpp_strategies:
        if name not in BUILTIN_STRATEGIES:
            print(f"- {name}: {cpp_strategies[name]['description']}")
    
    # Test strategy selector
    selector = StrategySelector("cpp")
    test_context = {
        'iteration_context': {'current_iteration': 3, 'max_iterations': 10},
        'performance_stats': {'convergence_trend': 'stagnating'}
    }
    
    selected = selector.select_adaptive(test_context)
    print(f"\nSelected strategy for test context: {selected}")