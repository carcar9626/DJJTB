#!/usr/bin/env python3
"""
Universal README Generator
Auto-generate README files from any Python/Shell project
Part of DJJTB Quick Tools
"""

import os
import sys
import re
import ast
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))
import djjtb.utils as djj

# Optional imports for AI models
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


@dataclass
class ScriptInfo:
    """Container for script analysis results."""
    filepath: str
    script_type: str
    description: str
    functions: List[str]
    dependencies: List[str]
    usage_examples: List[str]
    arguments: List[str]
    docstring: Optional[str] = None


class ScriptAnalyzer:
    """Analyzes Python and shell scripts to extract information."""
    
    def __init__(self):
        self.python_patterns = {
            'imports': r'^(?:from\s+\S+\s+)?import\s+(.+)',
            'functions': r'^def\s+(\w+)\s*\(',
            'classes': r'^class\s+(\w+)\s*[:\(]',
            'main_guard': r'if\s+__name__\s*==\s*["\']__main__["\']',
            'argparse': r'argparse\.ArgumentParser|add_argument',
            'cli_args': r'add_argument\(["\']([^"\']+)',
        }
        
        self.shell_patterns = {
            'shebang': r'^#!/.+',
            'functions': r'^(?:function\s+)?(\w+)\s*\(\s*\)',
            'variables': r'^([A-Z_][A-Z0-9_]*)\s*=',
            'commands': r'^\s*([a-zA-Z][\w-]*)\s+',
            'arguments': r'\$\{?(\d+|\w+)\}?',
        }
    
    def analyze_python_file(self, filepath: str) -> ScriptInfo:
        """Analyze a Python file and extract information."""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        info = ScriptInfo(
            filepath=filepath,
            script_type='python',
            description='',
            functions=[],
            dependencies=[],
            usage_examples=[],
            arguments=[]
        )
        
        # Try to parse as AST for better analysis
        try:
            tree = ast.parse(content)
            info.docstring = ast.get_docstring(tree)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    info.functions.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        info.dependencies.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        info.dependencies.append(node.module)
        except SyntaxError:
            pass
        
        # Fallback to regex patterns
        lines = content.split('\n')
        for line in lines:
            # Extract imports
            import_match = re.match(self.python_patterns['imports'], line.strip())
            if import_match:
                imports = [imp.strip() for imp in import_match.group(1).split(',')]
                info.dependencies.extend(imports)
            
            # Extract CLI arguments
            arg_match = re.search(self.python_patterns['cli_args'], line)
            if arg_match:
                info.arguments.append(arg_match.group(1))
        
        # Clean and deduplicate
        info.dependencies = list(set([dep.split('.')[0] for dep in info.dependencies]))
        info.functions = list(set(info.functions))
        info.arguments = list(set(info.arguments))
        
        # Generate description from docstring or filename
        if info.docstring:
            info.description = info.docstring.split('\n')[0].strip()
        else:
            # Try to infer purpose from filename/content
            filename = Path(filepath).stem
            if any(term in filename.lower() for term in ['test', 'spec']):
                info.description = f"Test module: {filename}"
            elif any(term in filename.lower() for term in ['util', 'helper', 'tool']):
                info.description = f"Utility module: {filename}"
            elif any(term in filename.lower() for term in ['main', 'app', 'run']):
                info.description = f"Main application: {filename}"
            elif any(term in filename.lower() for term in ['config', 'setting']):
                info.description = f"Configuration module: {filename}"
            else:
                info.description = f"Python module: {filename}"
        
        return info
    
    def analyze_shell_file(self, filepath: str) -> ScriptInfo:
        """Analyze a shell script and extract information."""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        info = ScriptInfo(
            filepath=filepath,
            script_type='shell',
            description='',
            functions=[],
            dependencies=[],
            usage_examples=[],
            arguments=[]
        )
        
        lines = content.split('\n')
        description_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Extract description from initial comments
            if i < 20 and (stripped.startswith('#') or not stripped):
                if stripped.startswith('#'):
                    desc_line = stripped[1:].strip()
                    if desc_line and not desc_line.startswith('!'):
                        description_lines.append(desc_line)
            
            # Extract functions
            func_match = re.match(self.shell_patterns['functions'], stripped)
            if func_match:
                info.functions.append(func_match.group(1))
            
            # Extract command usage
            if stripped and not stripped.startswith('#'):
                cmd_match = re.match(self.shell_patterns['commands'], stripped)
                if cmd_match:
                    cmd = cmd_match.group(1)
                    if cmd not in ['if', 'then', 'else', 'fi', 'for', 'while', 'do', 'done']:
                        info.dependencies.append(cmd)
            
            # Extract arguments
            args = re.findall(self.shell_patterns['arguments'], line)
            for arg in args:
                if arg.isdigit() or arg in ['@', '*']:
                    info.arguments.append(f'${arg}')
                elif arg.isupper():
                    info.arguments.append(f'${arg}')
        
        # Set description
        if description_lines:
            info.description = ' '.join(description_lines[:3])
        else:
            filename = Path(filepath).stem
            if any(term in filename.lower() for term in ['install', 'setup']):
                info.description = f"Installation script: {filename}"
            elif any(term in filename.lower() for term in ['build', 'deploy']):
                info.description = f"Build/deploy script: {filename}"
            elif any(term in filename.lower() for term in ['backup', 'sync']):
                info.description = f"Backup/sync script: {filename}"
            else:
                info.description = f"Shell script: {filename}"
        
        # Clean and deduplicate
        info.dependencies = list(set(info.dependencies))
        info.functions = list(set(info.functions))
        info.arguments = list(set(info.arguments))
        
        return info


class LocalAIEnhancer:
    """Enhances README generation using local AI models."""
    
    def __init__(self, model_type: str = "ollama"):
        self.model_type = model_type
        self.model = None
        self.tokenizer = None
        
    def setup_ollama(self, model_name: str = "llama2"):
        """Setup Ollama for local AI enhancement."""
        if not REQUESTS_AVAILABLE:
            print("\033[93m⚠️  Warning: requests library not available for Ollama integration\033[0m")
            return False
        
        try:
            # Test Ollama connection
            response = requests.get("http://localhost:11434/api/version", timeout=5)
            if response.status_code == 200:
                self.model = model_name
                print(f"\033[92m✓ Connected to Ollama with {model_name}\033[0m")
                return True
        except:
            pass
        print("\033[93m⚠️  Ollama not available - using basic analysis\033[0m")
        return False
    
    def enhance_description(self, script_info: ScriptInfo) -> str:
        """Use AI to enhance script description."""
        if self.model_type == "ollama" and self.model:
            return self._enhance_with_ollama(script_info)
        return script_info.description
    
    def _enhance_with_ollama(self, script_info: ScriptInfo) -> str:
        """Enhance description using Ollama."""
        prompt = f"""
        Analyze this {script_info.script_type} script and provide a clear, concise description:
        
        Functions: {', '.join(script_info.functions[:5])}
        Dependencies: {', '.join(script_info.dependencies[:5])}
        Current description: {script_info.description}
        
        Provide a brief, professional description (1-2 sentences):
        """
        
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                enhanced = result.get("response", script_info.description).strip()
                if enhanced and len(enhanced) > 10:  # Basic validation
                    return enhanced
        except:
            pass
        
        return script_info.description


class READMEGenerator:
    """Generates README files from script analysis."""
    
    def __init__(self, use_ai: bool = False, ai_model: str = "ollama"):
        self.analyzer = ScriptAnalyzer()
        self.ai_enhancer = None
        
        if use_ai:
            self.ai_enhancer = LocalAIEnhancer(ai_model)
            if ai_model == "ollama":
                self.ai_enhancer.setup_ollama()
    
    def scan_directory(self, directory: str) -> List[ScriptInfo]:
        """Scan directory for Python and shell scripts."""
        scripts = []
        path = Path(directory)
        
        # Directories to exclude from scanning
        exclude_dirs = {
            'venv', 'env', '.venv', '.env',           # Virtual environments
            'node_modules', '__pycache__',             # Package/cache dirs
            '.git', '.svn', '.hg',                     # Version control
            'build', 'dist', '.tox',                   # Build directories
            '.pytest_cache', '.coverage',              # Test/coverage
            'site-packages', 'lib', 'include',        # Library directories
            '.idea', '.vscode', '.vs',                 # IDE directories
            'temp', 'tmp', '.tmp',                     # Temporary directories
            'logs', 'log'                              # Log directories
        }
        
        for file_path in path.rglob("*"):
            # Skip if any parent directory is in exclude list
            if any(part.lower() in exclude_dirs for part in file_path.parts):
                continue
                
            if file_path.is_file():
                if file_path.suffix == ".py":
                    scripts.append(self.analyzer.analyze_python_file(str(file_path)))
                elif file_path.suffix in [".sh", ".bash"] or self._is_shell_script(file_path):
                    scripts.append(self.analyzer.analyze_shell_file(str(file_path)))
        
        return scripts
    
    def _is_shell_script(self, file_path: Path) -> bool:
        """Check if file is a shell script by examining shebang."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline().strip()
                return first_line.startswith('#!/') and ('sh' in first_line or 'bash' in first_line)
        except:
            return False
    
    def generate_readme(self, scripts: List[ScriptInfo], project_name: str, project_path: str) -> str:
        """Generate README content from script analysis."""
        readme_content = [
            f"# {project_name}\n\n",
            "## Overview\n\n",
            f"This project contains {len(scripts)} scripts for various automation and utility tasks.\n\n"
        ]
        
        # Group scripts by type and category
        python_scripts = [s for s in scripts if s.script_type == 'python']
        shell_scripts = [s for s in scripts if s.script_type == 'shell']
        
        # Categorize Python scripts
        main_scripts = [s for s in python_scripts if any(term in Path(s.filepath).stem.lower() for term in ['main', 'app', 'run'])]
        utils = [s for s in python_scripts if any(term in Path(s.filepath).stem.lower() for term in ['util', 'helper', 'tool'])]
        tests = [s for s in python_scripts if any(term in Path(s.filepath).stem.lower() for term in ['test', 'spec'])]
        other_python = [s for s in python_scripts if s not in main_scripts + utils + tests]
        
        # Main Scripts Section
        if main_scripts:
            readme_content.extend([
                "## 🚀 Main Scripts\n\n",
                "| Script | Description | Dependencies |\n",
                "|--------|-------------|-------------|\n"
            ])
            
            for script in main_scripts:
                description = script.description
                if self.ai_enhancer:
                    description = self.ai_enhancer.enhance_description(script)
                
                deps = ", ".join(script.dependencies[:3])
                if len(script.dependencies) > 3:
                    deps += "..."
                
                filename = Path(script.filepath).name
                readme_content.append(f"| `{filename}` | {description} | {deps} |\n")
        
        # Python Scripts Section
        if other_python:
            readme_content.extend([
                "\n## 🐍 Python Scripts\n\n",
                "| Script | Description | Dependencies |\n",
                "|--------|-------------|-------------|\n"
            ])
            
            for script in other_python:
                description = script.description
                if self.ai_enhancer:
                    description = self.ai_enhancer.enhance_description(script)
                
                deps = ", ".join(script.dependencies[:3])
                if len(script.dependencies) > 3:
                    deps += "..."
                
                filename = Path(script.filepath).name
                readme_content.append(f"| `{filename}` | {description} | {deps} |\n")
        
        # Utilities Section
        if utils:
            readme_content.extend([
                "\n## 🛠️ Utilities\n\n",
                "| Utility | Description | Key Functions |\n",
                "|---------|-------------|---------------|\n"
            ])
            
            for script in utils:
                description = script.description
                if self.ai_enhancer:
                    description = self.ai_enhancer.enhance_description(script)
                
                functions = ", ".join(script.functions[:3])
                if len(script.functions) > 3:
                    functions += "..."
                
                filename = Path(script.filepath).name
                readme_content.append(f"| `{filename}` | {description} | {functions} |\n")
        
        # Shell Scripts Section
        if shell_scripts:
            readme_content.extend([
                "\n## 📜 Shell Scripts\n\n",
                "| Script | Description | Commands Used |\n",
                "|--------|-------------|---------------|\n"
            ])
            
            for script in shell_scripts:
                description = script.description
                if self.ai_enhancer:
                    description = self.ai_enhancer.enhance_description(script)
                
                deps = ", ".join(script.dependencies[:3])
                if len(script.dependencies) > 3:
                    deps += "..."
                
                filename = Path(script.filepath).name
                readme_content.append(f"| `{filename}` | {description} | {deps} |\n")
        
        # Installation section
        all_deps = set()
        for script in scripts:
            all_deps.update(script.dependencies)
        
        # Filter out standard library and common system commands
        external_deps = [dep for dep in all_deps if dep not in [
            'os', 'sys', 'subprocess', 'pathlib', 'logging', 'json', 'time', 'tempfile',
            'select', 'ast', 're', 'argparse', 'shutil', 'glob', 'collections',
            'ls', 'cd', 'echo', 'grep', 'awk', 'sed', 'find', 'sort', 'cat'
        ]]
        
        if external_deps:
            readme_content.extend([
                "\n## 📦 Installation & Dependencies\n\n",
                "### Python Dependencies\n",
                "```bash\n",
                f"pip install {' '.join(sorted(external_deps))}\n",
                "```\n\n"
            ])
        
        # Usage section
        readme_content.extend([
            "## 🎯 Usage\n\n",
            "### Python Scripts\n",
            "```bash\n",
            "python script_name.py [arguments]\n",
            "```\n\n",
            "### Shell Scripts\n",
            "```bash\n",
            "chmod +x script_name.sh\n",
            "./script_name.sh [arguments]\n",
            "```\n\n"
        ])
        
        # Tests section
        if tests:
            readme_content.extend([
                "## 🧪 Tests\n\n",
                "| Test | Description |\n",
                "|------|-------------|\n"
            ])
            
            for script in tests:
                filename = Path(script.filepath).name
                description = script.description
                readme_content.append(f"| `{filename}` | {description} |\n")
            
            readme_content.append("\n")
        
        # Project structure if there are subdirectories
        subdirs = set()
        for script in scripts:
            script_path = Path(script.filepath)
            relative_path = script_path.relative_to(project_path)
            if len(relative_path.parts) > 1:
                subdirs.add(relative_path.parts[0])
        
        if subdirs:
            readme_content.extend([
                "## 📁 Project Structure\n\n",
                "```\n",
                f"{Path(project_path).name}/\n"
            ])
            
            for subdir in sorted(subdirs):
                subdir_scripts = [s for s in scripts if subdir in s.filepath]
                readme_content.append(f"├── {subdir}/     # {len(subdir_scripts)} scripts\n")
            
            readme_content.append("```\n\n")
        
        readme_content.extend([
            "---\n",
            "*Generated with DJJTB README Generator*\n"
        ])
        
        return "".join(readme_content)
    
    def save_readme(self, content: str, output_path: str):
        """Save README content to file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\033[92m✓ README generated: {output_path}\033[0m")


def main():
    """Main function with DJJTB-style interface."""
    while True:
        os.system('clear')
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33m📄 README GENERATOR 📝\033[0m")
        print("Auto-generate documentation for any project")
        print("\033[92m==================================================\033[0m")
        print()
        
        # Get project path
        project_path = djj.get_path_input("📁 Enter project path to analyze")
        
        if not os.path.isdir(project_path):
            print("\033[93m❌ Invalid directory path\033[0m")
            djj.wait_with_skip(3, "Try again")
            continue
        
        print()
        print(f"\033[92m✓ Project path: {project_path}\033[0m")
        
        # Get project name
        default_name = Path(project_path).name
        project_name = djj.get_string_input(
            f"\033[93m📝 Project name (default: {default_name})\033[0m",
            default=default_name
        )
        
        print()
        
        # Ask about AI enhancement
        use_ai = djj.prompt_choice(
            "\033[93m🤖 Use AI enhancement for descriptions?\033[0m\n1. Yes (requires Ollama)\n2. No (basic analysis)\n",
            ['1', '2'],
            default='2'
        ) == '1'
        
        print()
        
        # Initialize generator
        print("\033[93m🔍 Initializing README generator...\033[0m")
        generator = READMEGenerator(use_ai=use_ai, ai_model="ollama")
        
        # Scan directory
        print(f"\033[93m📁 Scanning directory: {project_path}\033[0m")
        scripts = generator.scan_directory(project_path)
        
        if not scripts:
            print("\033[93m❌ No Python or shell scripts found!\033[0m")
            djj.wait_with_skip(3, "Try again")
            continue
        
        print(f"\033[92m✓ Found {len(scripts)} script(s)\033[0m")
        
        # Show preview of found scripts
        print("\033[93m📜 Scripts found:\033[0m")
        for i, script in enumerate(scripts[:5]):
            filename = Path(script.filepath).name
            print(f"  {i+1}. {filename} ({script.script_type})")
        if len(scripts) > 5:
            print(f"  ... and {len(scripts) - 5} more")
        
        print()
        
        # Get output location
        output_mode = djj.prompt_choice(
            "\033[93m📁 Where should the README be saved?\033[0m\n1. In the project folder\n2. Desktop\n3. Custom location\n",
            ['1', '2', '3'],
            default='1'
        )
        
        if output_mode == '1':
            output_path = os.path.join(project_path, "README.md")
        elif output_mode == '2':
            output_path = os.path.expanduser("~/Desktop/README.md")
        else:
            output_dir = djj.get_path_input("📁 Enter output folder")
            output_path = os.path.join(output_dir, "README.md")
        
        print()
        print(f"\033[93m⚙️  Generating README...\033[0m")
        
        # Generate README
        readme_content = generator.generate_readme(scripts, project_name, project_path)
        
        # Save README
        generator.save_readme(readme_content, output_path)
        
        print()
        print(f"\033[92m🎉 README generated successfully!\033[0m")
        print(f"\033[93m📄 Location: {output_path}\033[0m")
        print(f"\033[93m📊 Analyzed: {len(scripts)} scripts\033[0m")
        
        # Offer to open the file
        if djj.prompt_choice(
            "\033[93m📖 Open README file?\033[0m\n1. Yes\n2. No\n",
            ['1', '2'],
            default='1'
        ) == '1':
            print("\n" * 2)
        djj.prompt_open_folder(output_path)
        
        print()
        
        # What next?
        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()