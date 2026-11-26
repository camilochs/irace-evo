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


def find_braced_definition(source: str, name: str):
    """Start and end offsets of the definition of `name` in C-like source
    (C++, Java): the first `name(` whose matching `)` is followed by `{`
    before any `;`, so calls and declarations are skipped. The signature may
    span lines, with the return type on a line of its own; the definition
    ends at the brace that closes the body. Comment lines just above it are
    not part of it."""
    for m in re.finditer(rf"\b{re.escape(name)}\s*\(", source):
        depth, j = 0, m.end() - 1
        while j < len(source):
            depth += {"(": 1, ")": -1}.get(source[j], 0)
            if depth == 0:
                break
            j += 1
        brace = source.find("{", j)
        if brace < 0 or any(c in source[j + 1:brace] for c in ";}="):
            continue
        depth, k = 0, brace
        while k < len(source):
            depth += {"{": 1, "}": -1}.get(source[k], 0)
            k += 1
            if depth == 0:
                break
        if depth:
            raise ValueError(f"Unmatched braces in the definition of {name}")
        start = source.rfind("\n", 0, m.start()) + 1
        while start > 0:
            prev_start = source.rfind("\n", 0, start - 1) + 1
            prev = source[prev_start:start - 1].strip()
            if (not prev or prev.endswith((";", "}", "{", "*/")) or prev.startswith(("//", "/*", "*", "#", "@"))):
                break
            start = prev_start
        return start, k
    raise ValueError(f"No definition of {name} found")



class LanguageHandler(ABC):
    """Abstract base class for language-specific handlers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.language_config = config.get('language_config', {})
        build_config = config.get('build_config', {})
        # The template keeps one section per language (build_config.cpp,
        # build_config.python, ...) and says only the chosen one is used;
        # a flat build_config is accepted as well.
        language = self.language_config.get('language', 'cpp')
        aliases = {'cpp': ('cpp', 'c++'), 'python': ('python', 'py'), 'py': ('python', 'py'), 'java': ('java',)}
        for key in aliases.get(language, (language,)):
            if isinstance(build_config.get(key), dict):
                build_config = build_config[key]
                break
        self.build_config = build_config
    
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
        """The definition of a C++ function, found by matching braces"""
        start, end = find_braced_definition(source_code, function_name)
        return source_code[start:end]
    
    def replace_function(self, source_code: str, function_name: str, new_function: str) -> str:
        """Put new_function in place of the definition of function_name"""
        start, end = find_braced_definition(source_code, function_name)
        return source_code[:start] + new_function.strip() + source_code[end:]
    
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
            
            # Build compilation command. The variant is written to a temporary
            # file, so the original file's directory goes on the include path
            # for its local #include "..." lines, followed by the configured
            # include paths, library paths and libraries.
            source_file = self.config.get('source_config', {}).get('source_file')
            include_dirs = ([os.path.dirname(os.path.abspath(source_file))] if source_file else [])
            include_dirs += self.build_config.get('include_paths', [])
            cmd = ([compiler] + flags + [f"-I{d}" for d in include_dirs]
                   + [temp_source_path, '-o', executable_path]
                   + [f"-L{d}" for d in self.build_config.get('library_paths', [])]
                   + [f"-l{l}" for l in self.build_config.get('libraries', [])])
            
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
        python_file = os.path.abspath(os.path.join(output_dir, f"{output_name}.py"))
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
    """Handler for Java: the method is found by matching braces, and each
    variant is compiled into a directory of its own (Java needs the file to
    be named after its public class, which is the source file's name)."""
    
    def extract_function(self, source_code: str, function_name: str) -> str:
        start, end = find_braced_definition(source_code, function_name)
        return source_code[start:end]
    
    def replace_function(self, source_code: str, function_name: str, new_function: str) -> str:
        start, end = find_braced_definition(source_code, function_name)
        return source_code[:start] + new_function.strip() + source_code[end:]
    
    def compile_and_test(self, source_code: str, output_name: str = "Program") -> str:
        """Compile into <output_dir>/<output_name>/ and return a script that runs it"""
        javac = self.build_config.get('compiler', 'javac')
        flags = self.build_config.get('flags', [])
        timeout = self.build_config.get('compile_timeout', 45)
        source_file = self.config.get('source_config', {}).get('source_file', 'Program.java')
        class_name = os.path.splitext(os.path.basename(source_file))[0]
        output_dir = os.path.abspath(self.build_config.get('output_dir', './bin'))
        class_dir = os.path.join(output_dir, output_name + ".classes")
        os.makedirs(class_dir, exist_ok=True)
        java_file = os.path.join(class_dir, class_name + ".java")
        with open(java_file, 'w') as f:
            f.write(source_code)
        result = subprocess.run([javac] + flags + ['-d', class_dir, java_file],
                                capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"Java compilation failed: {result.stderr}")
        wrapper_script = os.path.join(output_dir, output_name)
        with open(wrapper_script, 'w') as f:
            f.write(f'#!/bin/bash\nexec java -cp "{class_dir}" {class_name} "$@"\n')
        os.chmod(wrapper_script, 0o755)
        return wrapper_script
    
    def validate_syntax(self, code: str) -> bool:
        """Balanced braces and something that looks like a method"""
        if not code or code.count('{') != code.count('}'):
            return False
        return bool(re.search(r'\w+\s*\([^;{]*\)[^;{]*\{', code))


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