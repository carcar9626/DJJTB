
    
    # Filter for DJJTB-relevant scripts if in#!/usr/bin/env python3
"""
Auto README Generator
Analyzes Python and shell scripts to generate comprehensive README files.
Supports both rule-based analysis and local AI models.
"""

import os
import re
import ast
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

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
            'djj_utils': r'import\s+djjtb\.utils\s+as\s+djj',
            'menu_functions': r'def\s+(show_\w*menu|handle_\w+)',
            'ffmpeg_usage': r'ffmpeg|subprocess\.run.*ffmpeg',
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
        
        # Special handling for DJJTB project structure
        is_djjtb_script = 'djjtb.utils' in content or 'import djjtb.utils as djj' in content
        is_launcher_script = 'DJJTBLauncher' in content or 'show_main_menu' in content
        is_media_tool = any(tool in filepath.lower() for tool in ['video', 'image', 'media', 'audio'])
        
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
        menu_functions = []
        media_operations = []
        
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
            
            # DJJTB-specific: Extract menu functions
            menu_match = re.search(self.python_patterns['menu_functions'], line)
            if menu_match:
                menu_functions.append(menu_match.group(1))
            
            # DJJTB-specific: Detect FFmpeg usage
            if re.search(self.python_patterns['ffmpeg_usage'], line, re.IGNORECASE):
                media_operations.append('FFmpeg processing')
        
        # Clean and deduplicate
        info.dependencies = list(set([dep.split('.')[0] for dep in info.dependencies]))
        info.functions = list(set(info.functions))
        info.arguments = list(set(info.arguments))
        
        # Generate DJJTB-specific description
        if is_launcher_script:
            info.description = "Main DJJTB launcher with interactive menu system for media and AI tools"
        elif 'utils' in filepath and 'djjtb' in filepath:
            info.description = "DJJTB utility functions for UI, file handling, terminal management, and common operations"
        elif is_media_tool:
            # Extract tool type from filepath
            tool_type = self._extract_tool_type(filepath)
            if 'merger' in filepath.lower():
                info.description = f"{tool_type} merging tool with group processing capabilities"
            elif 'converter' in filepath.lower():
                info.description = f"{tool_type} format conversion tool with batch processing"
            elif 'cropper' in filepath.lower():
                info.description = f"{tool_type} cropping tool with custom dimensions"
            elif 'resizer' in filepath.lower():
                info.description = f"{tool_type} resizing tool with aspect ratio preservation"
            else:
                info.description = f"{tool_type} processing tool with FFmpeg integration"
        elif info.docstring:
            info.description = info.docstring.split('\n')[0].strip()
        else:
            info.description = f"Python script: {Path(filepath).stem}"
        
        # Add DJJTB-specific usage examples
        if is_djjtb_script:
            if is_launcher_script:
                info.usage_examples = ["python3 djjtb.py", "Run from DJJTB main menu"]
            else:
                module_path = self._get_module_path(filepath)
                info.usage_examples = [f"python3 -m {module_path}", "Run from DJJTB launcher menu"]
        
        return info
    
    def _extract_tool_type(self, filepath: str) -> str:
        """Extract tool type from filepath for DJJTB scripts."""
        if 'video' in filepath.lower():
            return 'Video'
        elif 'image' in filepath.lower():
            return 'Image'
        elif 'audio' in filepath.lower():
            return 'Audio'
        elif 'media' in filepath.lower():
            return 'Media'
        elif 'ai' in filepath.lower():
            return 'AI'
        else:
            return 'Media'
    
    def _get_module_path(self, filepath: str) -> str:
        """Convert filepath to Python module path for DJJTB project."""
        # Convert /path/to/djjtb/media_tools/video_tools/script.py -> djjtb.media_tools.video_tools.script
        path_obj = Path(filepath)
        parts = path_obj.parts
        
        # Find djjtb in the path
        try:
            djjtb_index = parts.index('djjtb')
            module_parts = parts[djjtb_index:]
            # Remove .py extension from last part
            if module_parts[-1].endswith('.py'):
                module_parts = module_parts[:-1] + (module_parts[-1][:-3],)
            return '.'.join(module_parts)
        except ValueError:
            # Fallback if djjtb not found in path
            return path_obj.stem
    
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
        in_comment_block = False
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
            info.description = f"Shell script: {Path(filepath).stem}"
        
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
            print("Warning: requests library not available for Ollama integration")
            return False
        
        try:
            # Test Ollama connection
            response = requests.get("http://localhost:11434/api/version", timeout=5)
            if response.status_code == 200:
                self.model = model_name
                return True
        except:
            pass
        return False
    
    def setup_transformers(self, model_name: str = "microsoft/DialoGPT-medium"):
        """Setup Transformers for local AI enhancement."""
        if not TRANSFORMERS_AVAILABLE:
            print("Warning: transformers library not available")
            return False
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name)
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def enhance_description(self, script_info: ScriptInfo) -> str:
        """Use AI to enhance script description."""
        if self.model_type == "ollama" and self.model:
            return self._enhance_with_ollama(script_info)
        elif self.model_type == "transformers" and self.model:
            return self._enhance_with_transformers(script_info)
        return script_info.description
    
    def _enhance_with_ollama(self, script_info: ScriptInfo) -> str:
        """Enhance description using Ollama."""
        prompt = f"""
        Analyze this {script_info.script_type} script and provide a clear, concise description:
        
        Functions: {', '.join(script_info.functions)}
        Dependencies: {', '.join(script_info.dependencies)}
        Arguments: {', '.join(script_info.arguments)}
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
                return result.get("response", script_info.description).strip()
        except:
            pass
        
        return script_info.description
    
    def _enhance_with_transformers(self, script_info: ScriptInfo) -> str:
        """Enhance description using Transformers."""
        # This is a simplified example - you'd want a more sophisticated approach
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
            elif ai_model == "transformers":
                self.ai_enhancer.setup_transformers()
    
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
    
    def generate_readme(self, scripts: List[ScriptInfo], project_name: str = None) -> str:
        """Generate README content from script analysis."""
        if not project_name:
            project_name = "DJJTB - DJ's Toolbox"
        
        readme_content = [
            f"# {project_name}\n\n",
            "## Overview\n\n",
            "DJJTB (DJ's Toolbox) is a comprehensive Python-based media processing suite with an interactive terminal interface. ",
            f"This repository contains {len(scripts)} scripts for video processing, image manipulation, AI tools, and automation utilities.\n\n",
            
            "## 🚀 Quick Start\n\n",
            "```bash\n",
            "# Clone and setup\n",
            "cd /Users/home/Documents/Scripts/DJJTB\n",
            "python3 -m venv venv\n",
            "source venv/bin/activate\n",
            "pip install -r requirements.txt\n\n",
            "# Launch main interface\n",
            "python3 djjtb.py\n",
            "```\n\n",
            
            "## 📁 Project Structure\n\n",
            "```\n",
            "DJJTB/\n",
            "├── djjtb.py              # Main launcher script\n",
            "├── djjtb/\n",
            "│   ├── utils.py          # Core utility functions\n",
            "│   ├── media_tools/      # Video & image processing\n",
            "│   ├── ai_tools/         # AI-powered utilities\n",
            "│   └── quick_tools/      # Standalone tools\n",
            "└── venv/                 # Python virtual environment\n",
            "```\n\n"
        ]
        
        # Group scripts by category
        launchers = [s for s in scripts if 'djjtb.py' in s.filepath or 'launcher' in s.filepath.lower()]
        utils = [s for s in scripts if 'utils.py' in s.filepath]
        video_tools = [s for s in scripts if 'video' in s.filepath.lower() and 'media_tools' in s.filepath]
        image_tools = [s for s in scripts if 'image' in s.filepath.lower() and 'media_tools' in s.filepath]
        ai_tools = [s for s in scripts if 'ai_tools' in s.filepath]
        quick_tools = [s for s in scripts if 'quick_tools' in s.filepath]
        other_scripts = [s for s in scripts if s not in launchers + utils + video_tools + image_tools + ai_tools + quick_tools]
        
        # Main Components
        if launchers or utils:
            readme_content.append("## 🎛️ Main Components\n\n")
            
            if launchers:
                for script in launchers:
                    filename = Path(script.filepath).name
                    readme_content.extend([
                        f"### {filename}\n",
                        f"{script.description}\n\n",
                        "**Features:**\n",
                        "- Interactive menu system with color-coded interface\n",
                        "- Terminal tab management for parallel processing\n",
                        "- Integrated app launcher for media applications\n",
                        "- Centralized path and session management\n\n"
                    ])
            
            if utils:
                for script in utils:
                    filename = Path(script.filepath).name
                    readme_content.extend([
                        f"### {filename}\n",
                        f"{script.description}\n\n",
                        "**Key Functions:**\n"
                    ])
                    
                    # Group functions by category
                    ui_functions = [f for f in script.functions if any(term in f for term in ['prompt', 'menu', 'choice', 'input'])]
                    file_functions = [f for f in script.functions if any(term in f for term in ['path', 'media', 'collect'])]
                    terminal_functions = [f for f in script.functions if any(term in f for term in ['terminal', 'tab', 'script'])]
                    
                    if ui_functions:
                        readme_content.append("- **UI/Input:** " + ", ".join(ui_functions[:5]) + "\n")
                    if file_functions:
                        readme_content.append("- **File Handling:** " + ", ".join(file_functions[:5]) + "\n")
                    if terminal_functions:
                        readme_content.append("- **Terminal Management:** " + ", ".join(terminal_functions[:5]) + "\n")
                    
                    readme_content.append("\n")
        
        # Video Tools Section
        if video_tools:
            readme_content.extend([
                "## 🎬 Video Tools\n\n",
                "| Tool | Description | Key Features |\n",
                "|------|-------------|-------------|\n"
            ])
            
            for script in video_tools:
                filename = Path(script.filepath).stem.replace('video_', '').replace('_', ' ').title()
                description = script.description
                
                # Extract key features based on common patterns
                features = []
                if 'ffmpeg' in ' '.join(script.dependencies).lower():
                    features.append("FFmpeg")
                if 'group' in script.filepath.lower():
                    features.append("Batch processing")
                if 'merge' in script.filepath.lower():
                    features.append("Video merging")
                if any(f in script.functions for f in ['get_user_input', 'prompt_choice']):
                    features.append("Interactive UI")
                
                features_str = ", ".join(features) if features else "Media processing"
                readme_content.append(f"| **{filename}** | {description} | {features_str} |\n")
        
        # Image Tools Section
        if image_tools:
            readme_content.extend([
                "\n## 🖼️ Image Tools\n\n",
                "| Tool | Description | Key Features |\n",
                "|------|-------------|-------------|\n"
            ])
            
            for script in image_tools:
                filename = Path(script.filepath).stem.replace('image_', '').replace('_', ' ').title()
                description = script.description
                
                features = []
                if 'PIL' in script.dependencies or 'Pillow' in script.dependencies:
                    features.append("PIL/Pillow")
                if 'opencv' in ' '.join(script.dependencies).lower():
                    features.append("OpenCV")
                if 'batch' in script.filepath.lower():
                    features.append("Batch processing")
                
                features_str = ", ".join(features) if features else "Image processing"
                readme_content.append(f"| **{filename}** | {description} | {features_str} |\n")
        
        # AI Tools Section
        if ai_tools:
            readme_content.extend([
                "\n## 🤖 AI Tools\n\n",
                "| Tool | Description | Technology |\n",
                "|------|-------------|------------|\n"
            ])
            
            for script in ai_tools:
                filename = Path(script.filepath).stem.replace('_', ' ').title()
                description = script.description
                
                tech = []
                if 'torch' in script.dependencies or 'pytorch' in script.dependencies:
                    tech.append("PyTorch")
                if 'tensorflow' in script.dependencies:
                    tech.append("TensorFlow")
                if 'comfy' in script.filepath.lower():
                    tech.append("ComfyUI")
                if 'lora' in script.filepath.lower():
                    tech.append("LoRA")
                
                tech_str = ", ".join(tech) if tech else "AI/ML"
                readme_content.append(f"| **{filename}** | {description} | {tech_str} |\n")
        
        # Quick Tools Section
        if quick_tools:
            readme_content.extend([
                "\n## ⚡ Quick Tools\n\n",
                "| Tool | Description | Usage |\n",
                "|------|-------------|-------|\n"
            ])
            
            for script in quick_tools:
                filename = Path(script.filepath).stem.replace('_', ' ').title()
                description = script.description
                module_path = self.analyzer._get_module_path(script.filepath) if hasattr(self, 'analyzer') else filename.lower().replace(' ', '_')
                
                readme_content.append(f"| **{filename}** | {description} | `python3 -m {module_path}` |\n")
        
        # Installation section with DJJTB-specific requirements
        all_deps = set()
        for script in scripts:
            all_deps.update(script.dependencies)
        
        # Filter out standard library and DJJTB-specific imports
        external_deps = [dep for dep in all_deps if dep not in [
            'os', 'sys', 'subprocess', 'pathlib', 'logging', 'json', 'time', 'tempfile',
            'djjtb', 'djjtb.utils', 'select', 'ast', 're'
        ]]
        
        if external_deps:
            readme_content.extend([
                "\n## 📦 Installation & Dependencies\n\n",
                "### System Requirements\n",
                "- macOS (optimized for Terminal.app integration)\n",
                "- Python 3.8+\n",
                "- FFmpeg (for video processing tools)\n\n",
                "### Python Dependencies\n",
                "```bash\n",
                f"pip install {' '.join(sorted(external_deps))}\n",
                "```\n\n",
                "### FFmpeg Installation\n",
                "```bash\n",
                "# Using Homebrew\n",
                "brew install ffmpeg\n",
                "```\n\n"
            ])
        
        # Usage section
        readme_content.extend([
            "## 🎯 Usage\n\n",
            "### Main Interface\n",
            "```bash\n",
            "# Launch the main DJJTB interface\n",
            "cd /Users/home/Documents/Scripts/DJJTB\n",
            "source venv/bin/activate\n",
            "python3 djjtb.py\n",
            "```\n\n",
            "### Direct Tool Access\n",
            "```bash\n",
            "# Run individual tools directly\n",
            "python3 -m djjtb.media_tools.video_tools.video_group_merger\n",
            "python3 -m djjtb.quick_tools.reverse_image_search\n",
            "```\n\n",
            "### Integration with Utils\n",
            "All DJJTB scripts use the centralized utils module:\n",
            "```python\n",
            "import djjtb.utils as djj\n\n",
            "# Common patterns\n",
            "choice = djj.prompt_choice(\"Select option\", ['1', '2', '3'])\n",
            "media_files = djj.get_centralized_media_input(\"script_name\")\n",
            "output_path = djj.get_centralized_output_path(\"script_name\")\n",
            "```\n\n"
        ])
        
        # Features section
        readme_content.extend([
            "## ✨ Key Features\n\n",
            "- **🖥️ Terminal Integration**: Optimized for macOS Terminal.app with tab management\n",
            "- **🎨 Color-coded Interface**: Enhanced UX with consistent color schemes\n",
            "- **📁 Smart Path Management**: Centralized input/output handling with session persistence\n",
            "- **⚡ Parallel Processing**: Multi-tab execution for batch operations\n",
            "- **🔄 Session Management**: Automatic cleanup and tab organization\n",
            "- **🎛️ Interactive Menus**: Intuitive navigation with skip options\n",
            "- **📱 App Integration**: Launch external media apps from within DJJTB\n\n"
        ])
        
        # Other scripts section
        if other_scripts:
            readme_content.extend([
                "## 📜 Additional Scripts\n\n",
                "| Script | Type | Description |\n",
                "|--------|------|-------------|\n"
            ])
            
            for script in other_scripts:
                filename = Path(script.filepath).name
                script_type = script.script_type.title()
                description = script.description
                
                readme_content.append(f"| `{filename}` | {script_type} | {description} |\n")
        
        readme_content.extend([
            "\n## 🛠️ Development\n\n",
            "### Project Structure Guidelines\n",
            "- All media tools import `djjtb.utils as djj`\n",
            "- Use centralized input/output functions from utils\n",
            "- Follow consistent UI patterns with color coding\n",
            "- Implement proper error handling and logging\n",
            "- Support both single and batch processing modes\n\n",
            "### Adding New Tools\n",
            "1. Create script in appropriate category folder\n",
            "2. Import and use `djjtb.utils` for UI consistency\n",
            "3. Add menu entry in main launcher\n",
            "4. Follow naming convention: `category_toolname.py`\n\n",
            "---\n",
            "*Generated with DJJTB README Generator*\n"
        ])
        
        return "".join(readme_content)
    
    def save_readme(self, content: str, output_path: str = "README.md"):
        """Save README content to file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"README generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Auto-generate README files from scripts")
    parser.add_argument("directory", help="Directory to scan for scripts")
    parser.add_argument("-o", "--output", default="README.md", help="Output README file")
    parser.add_argument("-n", "--name", help="Project name for README")
    parser.add_argument("--ai", action="store_true", help="Use AI enhancement")
    parser.add_argument("--ai-model", choices=["ollama", "transformers"], default="ollama",
                       help="AI model type to use")
    parser.add_argument("--export-json", help="Export script analysis as JSON")
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = READMEGenerator(use_ai=args.ai, ai_model=args.ai_model)
    
    # Scan directory
    print(f"Scanning directory: {args.directory}")
    scripts = generator.scan_directory(args.directory)
    print(f"Found {len(scripts)} scripts")
    
    # Export JSON if requested
    if args.export_json:
        with open(args.export_json, 'w') as f:
            json.dump([asdict(script) for script in scripts], f, indent=2)
        print(f"Script analysis exported to: {args.export_json}")
    
    # Generate README
    project_name = args.name or Path(args.directory).name
    readme_content = generator.generate_readme(scripts, project_name)
    
    # Save README
    generator.save_readme(readme_content, args.output)


if __name__ == "__main__":
    main()