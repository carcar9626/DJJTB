#!/usr/bin/env python3
"""
Workflow Hub - Centralized Workflow Management for DJJTB

This module allows users to chain multiple tools together in a workflow,
with centralized input/output management and session state tracking.
"""

import os
import sys
import pathlib
from typing import List, Dict, Any, Optional

# Add the project root to Python path
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import djjtb.utils as djj


class WorkflowHub:
    """Centralized workflow management for DJJTB tools"""
    
    def __init__(self):
        self.steps = []
        self.current_step = 0
        self.session_data = {}
        
    def add_step(self, tool_name: str, tool_module: str, input_paths: List[str] = None, 
                output_path: str = None, parameters: Dict[str, Any] = None):
        """Add a new step to the workflow"""
        step = {
            'tool_name': tool_name,
            'tool_module': tool_module,
            'input_paths': input_paths or [],
            'output_path': output_path,
            'parameters': parameters or {},
            'finished': False
        }
        self.steps.append(step)
        
    def setup_workflow(self):
        """Set up the workflow by getting initial inputs"""
        print("\033[92m=== WORKFLOW HUB SETUP ===\033[0m")
        
        try:
            # Get initial input files/folders using existing patterns
            print("Choose input method:")
            print("1. Single folder (all media files)")
            print("2. Multiple files/folders (space-separated)")
            print("3. Single file")
            
            input_mode = djj.prompt_choice(
                "\033[93mInput mode:\033[0m",
                ['1', '2', '3'],
                default='2'
            )
            
            initial_input_files = []
            
            if input_mode == '1':  # Single folder
                print("\033[93mEnter folder path:\033[0m")
                folder_path = djj.get_path_input("Enter folder path")
                
                print("Include subfolders?")
                include_subfolders = djj.prompt_choice(
                    "\033[93mInclude subfolders?\033[0m",
                    ['1', '2'], 
                    default='1'
                ) == '1'
                
                # Collect media files from folder
                extensions = ('.mp4', '.mkv', '.webm', '.mov', '.jpg', '.jpeg', '.png', '.gif')
                path_obj = pathlib.Path(folder_path).expanduser().resolve()
                
                if path_obj.is_dir():
                    print(f"Scanning {folder_path}...")
                    if include_subfolders:
                        # Walk through all subdirectories
                        for root, _, files in os.walk(path_obj):
                            for file in sorted(files):
                                if file.lower().endswith(extensions):
                                    initial_input_files.append(os.path.join(root, file))
                    else:
                        # Only files in the top level
                        for file in sorted(path_obj.iterdir()):
                            if file.is_file() and file.suffix.lower() in extensions:
                                initial_input_files.append(str(file))
                else:
                    print(f"\033[93mError: '{folder_path}' is not a valid directory.\033[0m")
                    return False
                    
            elif input_mode == '2':  # Multiple files/folders
                print("\033[93mEnter file paths or folder paths (space-separated):\033[0m")
                paths_input = input(" > ").strip()
                
                if not paths_input:
                    print("\033[93mNo input provided.\033[0m")
                    return False
                    
                # Parse input paths
                for path_str in paths_input.split():
                    path_str = path_str.strip('\'"')
                    try:
                        path_obj = pathlib.Path(path_str).expanduser().resolve()
                        if path_obj.exists():
                            if path_obj.is_file() and path_obj.suffix.lower() in ('.mp4', '.mkv', '.webm', '.mov', '.jpg', '.jpeg', '.png', '.gif'):
                                initial_input_files.append(str(path_obj))
                            elif path_obj.is_dir():
                                # Collect media files from directory
                                extensions = ('.mp4', '.mkv', '.webm', '.mov', '.jpg', '.jpeg', '.png', '.gif')
                                for file_path in path_obj.rglob('*'):
                                    if (file_path.is_file() and 
                                        file_path.suffix.lower() in extensions):
                                        initial_input_files.append(str(file_path))
                        else:
                            print(f"\033[93mWarning: Path '{path_str}' does not exist.\033[0m")
                    except Exception as e:
                        print(f"\033[93mError processing path '{path_str}': {e}\033[0m")
                        
            elif input_mode == '3':  # Single file
                print("\033[93mEnter file path:\033[0m")
                file_path = djj.get_path_input("Enter file path")
                path_obj = pathlib.Path(file_path)
                if path_obj.suffix.lower() in ('.mp4', '.mkv', '.webm', '.mov', '.jpg', '.jpeg', '.png', '.gif'):
                    initial_input_files = [str(path_obj)]
                else:
                    print(f"\033[93mWarning: File doesn't have a supported extension.\033[0m")
                    initial_input_files = [str(path_obj)]  # Include anyway, let the script decide
            
            if not initial_input_files:
                print("\033[93mNo valid media files found!\033[0m")
                return False
                
            # Save initial inputs to session
            self.session_data['initial_input_paths'] = initial_input_files
            self.session_data['workflow_started'] = True
            
            print(f"\033[92m✓ Found {len(initial_input_files)} media file(s)\033[0m")
            
            # Show sample files found
            for i, file_path in enumerate(initial_input_files[:5]):
                print(f"  {i+1}. {os.path.basename(file_path)}")
            if len(initial_input_files) > 5:
                print(f"  ... and {len(initial_input_files) - 5} more")
            
            return True
            
        except (EOFError, KeyboardInterrupt):
            print("\n\033[93mInput cancelled.\033[0m")
            return False
        except Exception as e:
            print(f"\033[93mError setting up workflow: {e}\033[0m")
            # Ask if user wants to retry or quit
            try:
                choice = djj.prompt_choice(
                    "\033[93mRetry setup? Or quit?\033[0m",
                    ['1', '2'], 
                    default='1'
                )
                if choice == '1':
                    return self.setup_workflow()  # Retry
                else:
                    return False  # Quit
            except:
                return False  # If we can't ask, just exit gracefully
    
    def select_workflow_tools(self):
        """Allow user to select tools for the workflow"""
        print("\033[92m=== SELECT WORKFLOW TOOLS ===\033[0m")
        
        # Available tools - both video and image tools plus AI
        available_tools = [
            # Video tools
            {'name': 'Video Re-encoder', 'module': 'djjtb.media_tools.video_tools.video_re-encoder'},
            {'name': 'Reverse Merge', 'module': 'djjtb.media_tools.video_tools.video_reverse_merge'},
            {'name': 'Slideshow Watermark', 'module': 'djjtb.media_tools.video_tools.video_slideshow_watermark'},
            {'name': 'Video Cropper', 'module': 'djjtb.media_tools.video_tools.video_cropper'},
            {'name': 'Group Merger', 'module': 'djjtb.media_tools.video_tools.video_group_merger'},
            {'name': 'Video Splitter', 'module': 'djjtb.media_tools.video_tools.video_splitter'},
            {'name': 'Speed Changer', 'module': 'djjtb.media_tools.video_tools.video_speed_changer'},
            {'name': 'Frame Extractor', 'module': 'djjtb.media_tools.video_tools.video_frame_extractor'},
            {'name': 'GIFs Converter', 'module': 'djjtb.media_tools.video_tools.video_gif_converter'},
            {'name': 'Audio Extractor', 'module': 'djjtb.media_tools.video_tools.video_audio_extractor'},
            
            # Image tools
            {'name': 'Image Resizer', 'module': 'djjtb.media_tools.image_tools.image_resizer'},
            {'name': 'Image Converter', 'module': 'djjtb.media_tools.image_tools.image_converter'},
            {'name': 'Image Processor', 'module': 'djjtb.media_tools.image_tools.image_processor'},
            {'name': 'Collage Creator', 'module': 'djjtb.media_tools.image_tools.image_collage_creator'},
            {'name': 'Strip Padding', 'module': 'djjtb.media_tools.image_tools.image_strip_padding'},
            {'name': 'Slideshow Maker', 'module': 'djjtb.media_tools.image_tools.image_slideshow_maker'},
            {'name': 'Image Stack', 'module': 'djjtb.media_tools.image_tools.image_stack'},
            {'name': 'WebP to MP4 Converter', 'module': 'djjtb.media_tools.image_tools.image_webp_to_mp4'},
            
            # AI tools
            {'name': 'Codeformer Runner', 'module': 'djjtb.ai_tools.codeformer_runner'},
            {'name': 'FaceFusion Runner', 'module': 'djjtb.ai_tools.facefusion_runner'},
            {'name': 'Image Tagger', 'module': 'djjtb.ai_tools.image_tagger'},
            {'name': 'JoyTag Tagger', 'module': 'djjtb.ai_tools.joytag_tagger'},
            {'name': 'Image Finder', 'module': 'djjtb.ai_tools.image_finder'}
        ]
        
        # Display available tools
        print("\033[92mAvailable Tools:\033[0m")
        for i, tool in enumerate(available_tools, 1):
            print(f" {i}. {tool['name']}")
        
        print("\nSelect steps to include in workflow (comma-separated numbers, or 'all' for all):")
        selection = input(" > ").strip()
        
        if not selection:
            return False
            
        # Parse selection
        tool_indices = []
        if selection.lower() == 'all':
            tool_indices = list(range(1, len(available_tools) + 1))
        else:
            try:
                for idx in selection.split(','):
                    idx = int(idx.strip())
                    if 1 <= idx <= len(available_tools):
                        tool_indices.append(idx)
                    else:
                        print(f"\033[93mWarning: Index {idx} out of range.\033[0m")
            except ValueError:
                print("\033[93mInvalid input. Please enter comma-separated numbers or 'all'.\033[0m")
                return False
        
        # Add selected tools to workflow
        for idx in tool_indices:
            tool = available_tools[idx - 1]
            self.add_step(
                tool_name=tool['name'],
                tool_module=tool['module']
            )
            
        print(f"\033[92m✓ Added {len(tool_indices)} tool(s) to workflow\033[0m")
        return True
    
    def run_workflow(self):
        """Execute the workflow steps"""
        if not self.steps:
            print("\033[93mNo workflow steps defined.\033[0m")
            return
            
        print("\033[92m=== EXECUTING WORKFLOW ===\033[0m")
        
        # Get initial inputs
        if 'initial_input_paths' not in self.session_data:
            print("First run setup...")
            self.setup_workflow()
            
        current_inputs = self.session_data['initial_input_paths']
        
        for i, step in enumerate(self.steps):
            print(f"\n\033[92mStep {i+1}: {step['tool_name']}\033[0m")
            
            # Save inputs for this step
            step['input_paths'] = current_inputs
            
            # Get output path for this step
            if i == len(self.steps) - 1:  # Last step
                output_path = djj.get_centralized_output_path(
                    f"workflow_step_{i+1}", 
                    default_name=f"{step['tool_name'].replace(' ', '_')}"
                )
            else:
                # For intermediate steps, we'll create temporary folder or use a naming scheme
                output_path = self.generate_temp_output_path(f"workflow_step_{i+1}")
            
            step['output_path'] = output_path
            
            print(f"  Input: {len(current_inputs)} files")
            print(f"  Output: {output_path}")
            
            # Show what's going to be run
            tool_module = step['tool_module']
            print(f"  Running tool: {tool_module}")
            
            # Actually run the tool (this will use actual Python execution for now)
            print("\033[92mRunning tool using subprocess...\033[0m")
            # In a real implementation, this would launch the appropriate script:
            # djj.run_script_in_tab('{tool_module}', venv_path, project_path)
            
            # For demonstration, we'll show a more realistic simulation
            print(f"Simulating execution of: python3 -m {tool_module}")
            print("This would create a new Terminal tab and run the tool with:")
            print(f"  source ~/Documents/Scripts/DJJTB/venv/bin/activate")
            print(f"  cd /Users/home/Documents/Scripts/DJJTB")
            print(f"  python3 -m {tool_module}")
            
            # In a real implementation, we'd use:
            # djj.run_script_in_tab(tool_module, "~/Documents/Scripts/DJJTB/venv/bin/activate", "/Users/home/Documents/Scripts/DJJTB")
            
        print("\n\033[92m=== WORKFLOW COMPLETED ===\033[0m")
    
    def generate_temp_output_path(self, script_name):
        """Generate a temporary output path for intermediate steps"""
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        return os.path.join(
            os.path.expanduser("~"), 
            "Desktop", 
            f"{script_name}_{timestamp}"
        )
        
    def show_workflow_status(self):
        """Display current workflow status"""
        print("\033[92m=== WORKFLOW STATUS ===\033[0m")
        print(f"Total steps: {len(self.steps)}")
        
        for i, step in enumerate(self.steps):
            status = "✓ Complete" if step.get('finished', False) else "○ Pending"
            print(f"  Step {i+1}: [{status}] {step['tool_name']}")
            
    def loop_back_to_step(self, step_index: int):
        """Loop back to a previous step or continue from current"""
        try:
            if 0 <= step_index < len(self.steps):
                self.current_step = step_index
                print(f"\033[92m✓ Looping back to step {step_index + 1}\033[0m")
            else:
                print(f"\033[93mInvalid step index. Must be between 0 and {len(self.steps) - 1}\033[0m")
        except Exception as e:
            print(f"\033[93mError looping back: {e}\033[0m")

    def run_interactive_workflow(self):
        """Run a workflow with interactive step selection"""
        print("\033[92m=== INTERACTIVE WORKFLOW HUB ===\033[0m")
        
        # Setup initial inputs 
        while True:
            try:
                if not self.setup_workflow():
                    print("Workflow setup failed.")
                    return
                break
            except Exception as e:
                print(f"\033[93mSetup error: {e}\033[0m")
                choice = djj.prompt_choice(
                    "\033[93mContinue or quit?\033[0m",
                    ['1', '2'], 
                    default='1'
                )
                if choice == '2':
                    return
        
        # Select tools
        while True:
            try:
                if not self.select_workflow_tools():
                    print("Tool selection failed.")
                    return
                break
            except Exception as e:
                print(f"\033[93mTool selection error: {e}\033[0m")
                choice = djj.prompt_choice(
                    "\033[93mContinue or quit?\033[0m",
                    ['1', '2'], 
                    default='1'
                )
                if choice == '2':
                    return
        
        # Show workflow status before running
        self.show_workflow_status()
        
        while True:
            try:
                choice = djj.prompt_choice(
                    "\033[93mWorkflow Options\033[0m\n1. Run Workflow\n2. Add Step\n3. Remove Step\n4. Loop Back\n5. Show Status\n6. Exit",
                    ['1', '2', '3', '4', '5', '6']
                )
                
                if choice == '1':
                    self.run_workflow()
                    break
                elif choice == '2':
                    print("Adding step functionality...")
                    # Implementation would go here
                    pass
                elif choice == '3':
                    print("Removing step functionality...")
                    # Implementation would go here
                    pass
                elif choice == '4':
                    try:
                        step_num = int(input("\033[93mEnter step number to loop back to (1-based): \033[0m")) - 1
                        self.loop_back_to_step(step_num)
                    except ValueError:
                        print("\033[93mInvalid step number.\033[0m")
                    except Exception as e:
                        print(f"\033[93mError looping back: {e}\033[0m")
                elif choice == '5':
                    self.show_workflow_status()
                elif choice == '6':
                    break
            except (EOFError, KeyboardInterrupt):
                print("\n\033[93mExiting workflow.\033[0m")
                break
            except Exception as e:
                print(f"\033[93mError in workflow: {e}\033[0m")
                choice = djj.prompt_choice(
                    "\033[93mContinue or quit?\033[0m",
                    ['1', '2'], 
                    default='1'
                )
                if choice == '2':
                    break
                 
        print("Workflow session ended.")


# Main execution when run directly
def main():
    workflow = WorkflowHub()
    workflow.run_interactive_workflow()


if __name__ == "__main__":
    main()