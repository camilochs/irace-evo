"""
Compilation Manager for irace-evo

Handles compilation and build processes for different programming languages.
This is a legacy module - functionality has been moved to language_handlers.py
but kept for backwards compatibility.

Author: Camilo Chacón Sartori
"""

import os
import subprocess
import tempfile
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from language_handlers import LanguageHandlerFactory


class CompilationManager:
    """
    Legacy compilation manager - delegates to language handlers
    
    This class is maintained for backwards compatibility.
    New code should use LanguageHandler classes directly.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Determine language
        language_config = config.get('language_config', {})
        self.language = language_config.get('language', 'cpp')
        
        # Create appropriate language handler
        full_config = {
            'language_config': language_config,
            'build_config': config
        }
        self.handler = LanguageHandlerFactory.create_handler(self.language, full_config)
    
    def compile_source(self, source_code: str, output_name: str = "program") -> str:
        """
        Compile source code using appropriate language handler
        
        Args:
            source_code: Source code to compile
            output_name: Name for output executable
            
        Returns:
            Path to compiled executable
            
        Raises:
            RuntimeError: If compilation fails
        """
        try:
            return self.handler.compile_and_test(source_code, output_name)
        except Exception as e:
            self.logger.error(f"Compilation failed: {e}")
            raise RuntimeError(f"Compilation failed: {e}")
    
    def validate_source(self, source_code: str) -> bool:
        """
        Validate source code syntax
        
        Args:
            source_code: Source code to validate
            
        Returns:
            True if syntax is valid
        """
        return self.handler.validate_syntax(source_code)


# Utility functions for build system integration
class BuildSystemIntegrator:
    """Integrates with existing build systems (Makefile, CMake, etc.)"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def use_makefile(self, source_code: str, makefile_path: str, target: str = "all") -> str:
        """
        Use existing Makefile to build code
        
        Args:
            source_code: Source code (written to temp file)
            makefile_path: Path to Makefile
            target: Make target to build
            
        Returns:
            Path to built executable
        """
        if not os.path.exists(makefile_path):
            raise FileNotFoundError(f"Makefile not found: {makefile_path}")
        
        makefile_dir = os.path.dirname(makefile_path)
        
        # Write source code to temporary file in Makefile directory
        source_file = os.path.join(makefile_dir, "algorithm_variant.cpp")
        with open(source_file, 'w') as f:
            f.write(source_code)
        
        try:
            # Run make
            result = subprocess.run(
                ["make", "-f", makefile_path, target],
                cwd=makefile_dir,
                capture_output=True,
                text=True,
                timeout=self.config.get('compile_timeout', 60)
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Make failed: {result.stderr}")
            
            # Look for executable in common locations
            potential_paths = [
                os.path.join(makefile_dir, target),
                os.path.join(makefile_dir, "bin", target),
                os.path.join(makefile_dir, "build", target),
                os.path.join(makefile_dir, "algorithm_variant")
            ]
            
            for path in potential_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    return path
            
            raise RuntimeError("No executable found after make")
            
        finally:
            # Clean up temporary source file
            if os.path.exists(source_file):
                os.unlink(source_file)
    
    def use_cmake(self, source_code: str, cmake_dir: str) -> str:
        """
        Use CMake build system
        
        Args:
            source_code: Source code
            cmake_dir: Directory containing CMakeLists.txt
            
        Returns:
            Path to built executable
        """
        cmake_file = os.path.join(cmake_dir, "CMakeLists.txt")
        if not os.path.exists(cmake_file):
            raise FileNotFoundError(f"CMakeLists.txt not found: {cmake_file}")
        
        # Create build directory
        build_dir = os.path.join(cmake_dir, "build")
        os.makedirs(build_dir, exist_ok=True)
        
        # Write source code
        source_file = os.path.join(cmake_dir, "algorithm_variant.cpp")
        with open(source_file, 'w') as f:
            f.write(source_code)
        
        try:
            # Configure with CMake
            configure_result = subprocess.run(
                ["cmake", ".."],
                cwd=build_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if configure_result.returncode != 0:
                raise RuntimeError(f"CMake configure failed: {configure_result.stderr}")
            
            # Build
            build_result = subprocess.run(
                ["cmake", "--build", "."],
                cwd=build_dir,
                capture_output=True,  
                text=True,
                timeout=self.config.get('compile_timeout', 120)
            )
            
            if build_result.returncode != 0:
                raise RuntimeError(f"CMake build failed: {build_result.stderr}")
            
            # Look for executable
            potential_paths = [
                os.path.join(build_dir, "algorithm_variant"),
                os.path.join(build_dir, "bin", "algorithm_variant"),
                os.path.join(build_dir, "Release", "algorithm_variant"),
                os.path.join(build_dir, "Debug", "algorithm_variant")
            ]
            
            for path in potential_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    return path
            
            raise RuntimeError("No executable found after CMake build")
            
        finally:
            if os.path.exists(source_file):
                os.unlink(source_file)


class TestRunner:
    """Runs basic functionality tests on compiled programs"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.test_config = config.get('validation_config', {})
        self.logger = logging.getLogger(__name__)
    
    def run_basic_test(self, executable_path: str) -> bool:
        """
        Run basic functionality test on executable
        
        Args:
            executable_path: Path to executable
            
        Returns:
            True if test passes
        """
        if not os.path.exists(executable_path):
            return False
        
        if not os.access(executable_path, os.X_OK):
            return False
        
        # Run with test arguments if specified
        test_args = self.test_config.get('test_arguments', [])
        timeout = self.test_config.get('test_timeout', 10)
        
        try:
            result = subprocess.run(
                [executable_path] + test_args,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Check exit code
            if result.returncode != 0:
                self.logger.warning(f"Test failed with exit code {result.returncode}")
                return False
            
            # Check output format if specified
            expected_pattern = self.test_config.get('expected_output_pattern')
            if expected_pattern:
                import re
                if not re.search(expected_pattern, result.stdout):
                    self.logger.warning("Test output doesn't match expected pattern")
                    return False
            
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.warning("Test timed out")
            return False
        except Exception as e:
            self.logger.error(f"Test execution failed: {e}")
            return False
    
    def run_unit_tests(self, executable_path: str) -> bool:
        """
        Run unit tests if configured
        
        Args:
            executable_path: Path to main executable
            
        Returns:
            True if all unit tests pass
        """
        unit_tests = self.test_config.get('unit_tests', [])
        
        if not unit_tests:
            return True  # No unit tests configured
        
        for test_file in unit_tests:
            if not os.path.exists(test_file):
                self.logger.warning(f"Unit test file not found: {test_file}")
                continue
            
            try:
                result = subprocess.run(
                    [test_file],
                    capture_output=True,
                    text=True,
                    timeout=self.test_config.get('test_timeout', 30)
                )
                
                if result.returncode != 0:
                    self.logger.error(f"Unit test failed: {test_file}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Unit test execution failed: {e}")
                return False
        
        return True


# Utility functions
def detect_build_system(directory: str) -> Optional[str]:
    """
    Detect build system in directory
    
    Args:
        directory: Directory to check
        
    Returns:
        Build system type or None
    """
    if os.path.exists(os.path.join(directory, "Makefile")):
        return "makefile"
    elif os.path.exists(os.path.join(directory, "CMakeLists.txt")):
        return "cmake"
    elif os.path.exists(os.path.join(directory, "build.gradle")):
        return "gradle"
    elif os.path.exists(os.path.join(directory, "pom.xml")):
        return "maven"
    elif os.path.exists(os.path.join(directory, "setup.py")):
        return "python_setuptools"
    else:
        return None


def create_minimal_makefile(language: str, source_file: str, output_name: str) -> str:
    """
    Create a minimal Makefile for compilation
    
    Args:
        language: Programming language
        source_file: Source file name
        output_name: Output executable name
        
    Returns:
        Makefile content
    """
    if language.lower() in ['cpp', 'c++']:
        return f"""# Generated Makefile for irace-evo
CXX = g++
CXXFLAGS = -O3 -std=c++17 -Wall
TARGET = {output_name}
SOURCE = {source_file}

$(TARGET): $(SOURCE)
\t$(CXX) $(CXXFLAGS) $(SOURCE) -o $(TARGET)

clean:
\trm -f $(TARGET)

.PHONY: clean
"""
    elif language.lower() == 'java':
        class_name = os.path.splitext(source_file)[0]
        return f"""# Generated Makefile for Java
JAVAC = javac
JAVA = java
TARGET = {output_name}
SOURCE = {source_file}
CLASS = {class_name}.class

$(TARGET): $(SOURCE)
\t$(JAVAC) $(SOURCE)
\techo '#!/bin/bash' > $(TARGET)
\techo 'java {class_name} "$$@"' >> $(TARGET)
\tchmod +x $(TARGET)

clean:
\trm -f $(TARGET) *.class

.PHONY: clean
"""
    else:
        raise ValueError(f"Unsupported language for Makefile generation: {language}")


# Testing
if __name__ == "__main__":
    # Test compilation manager
    config = {
        'language_config': {'language': 'cpp'},
        'compiler': 'g++',
        'flags': ['-O3', '-std=c++17'],
        'output_dir': './test_output'
    }
    
    manager = CompilationManager(config)
    
    # Test C++ code
    test_code = """
#include <iostream>
double simple_heuristic(int x) {
    return x * 2.0;
}
int main() {
    std::cout << simple_heuristic(5) << std::endl;
    return 0;
}
"""
    
    try:
        executable = manager.compile_source(test_code, "test_program")
        print(f"Compilation successful: {executable}")
        
        # Test the executable
        tester = TestRunner(config)
        if tester.run_basic_test(executable):
            print("Basic test passed")
        else:
            print("Basic test failed")
            
    except Exception as e:
        print(f"Compilation failed: {e}")