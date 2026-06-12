"""
Language Handlers for irace-evo

Language-specific handlers for parsing, compilation, and testing
of different programming languages.

Author: Camilo Chacón Sartori
"""

import os
import re
import subprocess
import tempfile
import ast
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path


class LanguageHandler(ABC):
    """Abstract base class for language-specific handlers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.language_config = config.get('language_config', {})
        self.build_config = config.get('build_config', {})
    
    @abstractmethod
    def extract_function(self, source_code: str, function_name: str) -> str:
        """Extract a specific function from source code"""
        pass
    
    @abstractmethod
    def replace_function(self, source_code: str, function_name: str, new_function: str) -> str:
        """Replace a function in source code with new implementation"""
        pass
    
    @abstractmethod
    def compile_and_test(self, source_code: str, output_name: str = "program") -> str:
        """Compile source code and return path to executable"""
        pass
    
    @abstractmethod
    def validate_syntax(self, code: str) -> bool:
        """Validate syntax of source code"""
        pass


class CppLanguageHandler(LanguageHandler):
    """Handler for C++ language"""
    
    def extract_function(self, source_code: str, function_name: str) -> str:
        """Extract C++ function from source code"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Extracting C++ function '{function_name}' from source code")
        
        # Simplified approach: use brace counting instead of complex regex
        # First find the function signature - handle complex return types like "set<int>"
        # Look for the actual line with function declaration
        lines = source_code.split('\n')
        function_line_idx = -1
        for i, line in enumerate(lines):
            if re.search(rf'\b{re.escape(function_name)}\s*\([^)]*\)\s*\{{', line):
                function_line_idx = i
                break
        
        if function_line_idx == -1:
            logger.error(f"Function '{function_name}' not found in source code")
            raise ValueError(f"Function {function_name} not found in C++ source code")
        
        # Find where the function starts in the original source
        function_line = lines[function_line_idx]
        function_start = source_code.find(function_line)
        logger.info(f"Found function at line {function_line_idx}: {function_line.strip()}")
        # Find the opening brace position in the function line
        brace_pos = source_code.find('{', function_start)
        if brace_pos == -1:
            logger.error(f"Opening brace not found for function '{function_name}'")
            raise ValueError(f"Opening brace not found for function {function_name}")
        
        logger.info(f"Found opening brace at position {brace_pos}")
        
        # Start counting from after the opening brace
        brace_count = 1
        current_pos = brace_pos + 1
        start_pos = function_start
        
        logger.info("Starting brace counting to find function end...")
        while current_pos < len(source_code) and brace_count > 0:
            char = source_code[current_pos]
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            current_pos += 1
        
        if brace_count == 0:
            function_code = source_code[start_pos:current_pos]
            logger.info(f"Successfully extracted function. Length: {len(function_code)} chars")
            
            # Show the complete extracted function for debugging
            lines = function_code.split('\n')
            logger.info("Extracted function preview:")
            for i, line in enumerate(lines):
                logger.info(f"  {i+1}: {line}")
                
            return function_code
        else:
            logger.error("Unmatched braces in function extraction")
            raise ValueError(f"Unmatched braces while extracting function {function_name}")
            
        raise ValueError(f"Function {function_name} not found in C++ source code")
    
    def replace_function(self, source_code: str, function_name: str, new_function: str) -> str:
        """Replace C++ function with new implementation"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Replacing C++ function '{function_name}' with new implementation")
        
        # Use the same approach as extract_function
        # Look for the actual line with function declaration
        lines = source_code.split('\n')
        function_line_idx = -1
        for i, line in enumerate(lines):
            if re.search(rf'\b{re.escape(function_name)}\s*\([^)]*\)\s*\{{', line):
                function_line_idx = i
                break
        
        if function_line_idx == -1:
            logger.error(f"Function '{function_name}' not found for replacement")
            raise ValueError(f"Function {function_name} not found for replacement in C++ code")
        
        # Find where the function starts in the original source
        function_line = lines[function_line_idx]
        function_start = source_code.find(function_line)
        logger.info(f"Found function to replace at line {function_line_idx}: {function_line.strip()}")
        
        # Find the opening brace position
        brace_pos = source_code.find('{', function_start)
        if brace_pos == -1:
            logger.error(f"Opening brace not found for function '{function_name}'")
            raise ValueError(f"Opening brace not found for function {function_name}")
        
        logger.info(f"Found opening brace at position {brace_pos}")
        
        # Start counting from after the opening brace
        brace_count = 1
        current_pos = brace_pos + 1
        start_pos = function_start
        
        logger.info("Counting braces to find function end for replacement...")
        while current_pos < len(source_code) and brace_count > 0:
            char = source_code[current_pos]
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            current_pos += 1
        
        if brace_count == 0:
            # Replace the old function with the new one
            before_function = source_code[:start_pos]
            after_function = source_code[current_pos:]
            new_source_code = before_function + new_function + after_function
            
            logger.info(f"Function replacement completed. Old length: {len(source_code)}, New length: {len(new_source_code)}")
            return new_source_code
        else:
            logger.error("Unmatched braces in function replacement")
            raise ValueError(f"Unmatched braces while replacing function {function_name}")
        
        raise ValueError(f"Function {function_name} not found for replacement in C++ code")
    
    def compile_and_test(self, source_code: str, output_name: str = "program") -> str:
        """Compile C++ source code"""
        # Get compilation settings
        compiler = self.build_config.get('compiler', 'g++')
        flags = self.build_config.get('flags', ['-O3', '-std=c++17', '-Wall'])
        timeout = self.build_config.get('compile_timeout', 30)
        
        # Create temporary source file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as temp_source:
            temp_source.write(source_code)
            temp_source_path = temp_source.name
        
        try:
            # Create output executable path
            output_dir = self.build_config.get('output_dir', './bin')
            os.makedirs(output_dir, exist_ok=True)
            executable_path = os.path.join(output_dir, output_name)
            
            # Build compilation command
            cmd = [compiler] + flags + [temp_source_path, '-o', executable_path]
            
            # Compile
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"C++ compilation failed: {result.stderr}")
            
            # Check if executable was created
            if not os.path.exists(executable_path):
                raise RuntimeError("Executable was not created")
            
            # Make executable
            os.chmod(executable_path, 0o755)
            
            return executable_path
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_source_path):
                os.unlink(temp_source_path)
    
    def validate_syntax(self, code: str) -> bool:
        """Basic C++ syntax validation"""
        if not code:
            return False
        
        # Check balanced braces
        brace_count = code.count('{') - code.count('}')
        if brace_count != 0:
            return False
        
        # Check balanced parentheses
        paren_count = code.count('(') - code.count(')')
        if paren_count != 0:
            return False
        
        # Check for basic function structure
        if not re.search(r'\w+\s+\w+\s*\([^)]*\)\s*\{', code):
            return False
        
        return True


class PythonLanguageHandler(LanguageHandler):
    """Handler for Python language"""
    
    def extract_function(self, source_code: str, function_name: str) -> str:
        """Extract Python function from source code"""
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    # Get the source segment for this function
                    lines = source_code.splitlines()
                    start_line = node.lineno - 1
                    
                    # Find end line (next function or end of file)
                    end_line = len(lines)
                    for other_node in ast.walk(tree):
                        if (isinstance(other_node, (ast.FunctionDef, ast.ClassDef)) and 
                            other_node.lineno > node.lineno):
                            end_line = min(end_line, other_node.lineno - 1)
                    
                    return '\n'.join(lines[start_line:end_line])
            
            raise ValueError(f"Function {function_name} not found in Python source")
            
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")
    
    def replace_function(self, source_code: str, function_name: str, new_function: str) -> str:
        """Replace Python function with new implementation"""
        try:
            tree = ast.parse(source_code)
            lines = source_code.splitlines()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    start_line = node.lineno - 1
                    
                    # Find end line
                    end_line = len(lines)
                    for other_node in ast.walk(tree):
                        if (isinstance(other_node, (ast.FunctionDef, ast.ClassDef)) and 
                            other_node.lineno > node.lineno):
                            end_line = min(end_line, other_node.lineno - 1)
                    
                    # Replace the function
                    new_lines = lines[:start_line] + [new_function] + lines[end_line:]
                    return '\n'.join(new_lines)
            
            raise ValueError(f"Function {function_name} not found for replacement")
            
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")
    
    def compile_and_test(self, source_code: str, output_name: str = "program") -> str:
        """Prepare Python source code for execution"""
        # Python doesn't compile to executable, but we validate and prepare
        if not self.validate_syntax(source_code):
            raise RuntimeError("Python syntax validation failed")
        
        # Create output directory
        output_dir = self.build_config.get('output_dir', './bin')
        os.makedirs(output_dir, exist_ok=True)
        
        # Save as Python file
        python_file = os.path.join(output_dir, f"{output_name}.py")
        with open(python_file, 'w') as f:
            f.write(source_code)
        
        # Create wrapper script if needed
        interpreter = self.build_config.get('interpreter', 'python3')
        wrapper_script = os.path.join(output_dir, output_name)
        
        with open(wrapper_script, 'w') as f:
            f.write(f"""#!/bin/bash
{interpreter} "{python_file}" "$@"
""")
        
        # Make wrapper executable
        os.chmod(wrapper_script, 0o755)
        
        return wrapper_script
    
    def validate_syntax(self, code: str) -> bool:
        """Validate Python syntax"""
        if not code:
            return False
        
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False


class JavaLanguageHandler(LanguageHandler):
    """Handler for Java language"""
    
    def extract_function(self, source_code: str, function_name: str) -> str:
        """Extract Java method from source code"""
        # Pattern for Java method
        pattern = rf'((?:public|private|protected)?\s*(?:static)?\s*\w+\s+{re.escape(function_name)}\s*\([^)]*\)\s*\{{[^}}]*\}})'
        match = re.search(pattern, source_code, re.MULTILINE | re.DOTALL)
        
        if match:
            return match.group(1)
        
        raise ValueError(f"Method {function_name} not found in Java source code")
    
    def replace_function(self, source_code: str, function_name: str, new_function: str) -> str:
        """Replace Java method with new implementation"""
        pattern = rf'((?:public|private|protected)?\s*(?:static)?\s*\w+\s+{re.escape(function_name)}\s*\([^)]*\)\s*\{{[^}}]*\}})'
        
        if re.search(pattern, source_code, re.MULTILINE | re.DOTALL):
            return re.sub(pattern, new_function, source_code, count=1, flags=re.MULTILINE | re.DOTALL)
        
        raise ValueError(f"Method {function_name} not found for replacement in Java code")
    
    def compile_and_test(self, source_code: str, output_name: str = "Program") -> str:
        """Compile Java source code"""
        # Get compilation settings
        javac = self.build_config.get('compiler', 'javac')
        java_flags = self.build_config.get('flags', ['-cp', '.'])
        timeout = self.build_config.get('compile_timeout', 30)
        
        # Create temporary source file
        java_filename = f"{output_name}.java"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as temp_source:
            temp_source.write(source_code)
            temp_source_path = temp_source.name
        
        try:
            # Compile Java source
            cmd = [javac] + java_flags + [temp_source_path]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Java compilation failed: {result.stderr}")
            
            # Create output directory and move compiled class
            output_dir = self.build_config.get('output_dir', './bin')
            os.makedirs(output_dir, exist_ok=True)
            
            # Create wrapper script to run Java program
            wrapper_script = os.path.join(output_dir, output_name)
            class_file = temp_source_path.replace('.java', '.class')
            
            with open(wrapper_script, 'w') as f:
                f.write(f"""#!/bin/bash
java -cp "{os.path.dirname(class_file)}" "{output_name}" "$@"
""")
            
            # Make wrapper executable
            os.chmod(wrapper_script, 0o755)
            
            return wrapper_script
            
        finally:
            # Clean up temporary files
            if os.path.exists(temp_source_path):
                os.unlink(temp_source_path)
    
    def validate_syntax(self, code: str) -> bool:
        """Basic Java syntax validation"""
        if not code:
            return False
        
        # Check balanced braces
        brace_count = code.count('{') - code.count('}')
        if brace_count != 0:
            return False
        
        # Check for basic method structure
        if not re.search(r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+\w+\s*\([^)]*\)\s*\{', code):
            return False
        
        return True


class LanguageHandlerFactory:
    """Factory for creating language-specific handlers"""
    
    _handlers = {
        'cpp': CppLanguageHandler,
        'c++': CppLanguageHandler,
        'python': PythonLanguageHandler,
        'py': PythonLanguageHandler,
        'java': JavaLanguageHandler
    }
    
    @classmethod
    def create_handler(cls, language: str, config: Dict[str, Any]) -> LanguageHandler:
        """Create appropriate language handler"""
        language = language.lower()
        
        if language not in cls._handlers:
            raise ValueError(f"Unsupported language: {language}. Supported: {list(cls._handlers.keys())}")
        
        return cls._handlers[language](config)
    
    @classmethod
    def get_supported_languages(cls) -> list:
        """Get list of supported languages"""
        return list(cls._handlers.keys())