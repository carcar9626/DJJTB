#!/usr/bin/env python3
"""
ComfyUI Batch Processor - DJJTB Edition
Processes images through ComfyUI workflows using symlinks
"""

import os
import json
import requests
import time
import sys
from pathlib import Path
from datetime import datetime
import djjtb.utils as djj

# ComfyUI server address (default)
COMFYUI_URL = "http://127.0.0.1:8188"

# ComfyUI input folder (where ComfyUI processes files from)
COMFYUI_INPUT_FOLDER = "/Users/home/Documents/ai_models/ComfyUI_App/ComfyUI/input"

# Default workflow folder
DEFAULT_WORKFLOW_FOLDER = "/Volumes/Movies_2SSD/ComfyUI.bak/user/default/workflows/API"

# Log file location
LOG_FOLDER = Path("/Users/home/Documents/Scripts/DJJTB_output/comfyui_batch_logs")

# Job tracking file
JOB_COUNTER_FILE = LOG_FOLDER / "job_counter.txt"

# Supported image formats
IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.bmp']

# Wait time between submissions (seconds)
QUEUE_DELAY = 1


def get_next_job_id():
    """Get the next job ID, incrementing from the counter file"""
    LOG_FOLDER.mkdir(parents=True, exist_ok=True)
    
    if JOB_COUNTER_FILE.exists():
        try:
            with open(JOB_COUNTER_FILE, 'r') as f:
                current_id = int(f.read().strip())
        except:
            current_id = 0
    else:
        current_id = 0
    
    # Increment for next job
    next_id = current_id + 1
    
    # Save the new counter
    with open(JOB_COUNTER_FILE, 'w') as f:
        f.write(str(next_id))
    
    return f"{next_id:05d}"  # Format as 00001, 00002, etc.


def get_todays_log_file():
    """Get today's log file path (creates if doesn't exist)"""
    LOG_FOLDER.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_FOLDER / f"{today}.log"
    return log_file


def log_job(job_id, source_folder, workflow_path, num_files, file_list):
    """Log job information to today's log file"""
    log_file = get_todays_log_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = f"""
{'=' * 70}
JOB ID: {job_id}
TIME: {timestamp}
SOURCE FOLDER: {source_folder}
WORKFLOW: {Path(workflow_path).name}
WORKFLOW PATH: {workflow_path}
NUMBER OF FILES: {num_files}
FILES:
"""
    
    for i, file_path in enumerate(file_list, 1):
        log_entry += f"  {i:3}. {Path(file_path).name}\n"
    
    log_entry += f"{'=' * 70}\n"
    
    # Append to log file
    with open(log_file, 'a') as f:
        f.write(log_entry)
    
    return log_file


def get_workflow_files(folder_path):
    """Get all JSON workflow files from a folder"""
    workflows = []
    folder = Path(folder_path)
    
    if not folder.exists():
        return workflows
    
    for file in sorted(folder.glob('*.json')):
        if file.is_file():
            workflows.append(file)
    
    return workflows


def select_workflow_from_folder(folder_path):
    """Interactive workflow selector from a folder"""
    workflows = get_workflow_files(folder_path)
    
    if not workflows:
        print(f"❌ \033[93mNo workflow files found in:\033[0m {folder_path}")
        return None
    
    print()
    print(f"\033[93m📂 Workflows in:\033[0m {Path(folder_path).name}")
    print("\033[93m" + "-" * 50 + "\033[0m")
    
    for i, workflow_path in enumerate(workflows, 1):
        print(f"{i:2}. {workflow_path.name}")
    
    print("\033[93m" + "-" * 50 + "\033[0m")
    print()
    
    # Get valid choice numbers
    valid_choices = [str(i) for i in range(1, len(workflows) + 1)]
    
    choice = djj.prompt_choice(
        "\033[93mSelect workflow number\033[0m",
        valid_choices,
        default='1'
    )
    
    selected_workflow = workflows[int(choice) - 1]
    print(f"✅ \033[92mSelected:\033[0m {selected_workflow.name}")
    print()
    
    return str(selected_workflow)


class ComfyUIBatchProcessor:
    def __init__(self, workflow_path, source_folder, comfyui_input_folder, load_image_node_id, job_id=None):
        self.workflow_path = workflow_path
        self.source_folder = Path(source_folder)
        self.comfyui_input_folder = Path(comfyui_input_folder)
        self.load_image_node_id = str(load_image_node_id)
        self.server_url = COMFYUI_URL
        self.client_id = "djjtb_batch_processor"
        self.created_symlinks = []
        self.job_id = job_id
        
    def load_workflow(self):
        """Load the workflow JSON file"""
        try:
            with open(self.workflow_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ \033[93mError: Workflow file not found at:\033[0m {self.workflow_path}")
            return None
        except json.JSONDecodeError:
            print(f"❌ \033[93mError: Invalid JSON in workflow file\033[0m")
            return None
    
    def get_images(self, include_subfolders=False):
        """Get list of all images in source folder"""
        images = []
        
        if not self.source_folder.exists():
            print(f"❌ \033[93mError: Source folder not found:\033[0m {self.source_folder}")
            return images
        
        if include_subfolders:
            # Recursively find images
            for root, _, files in os.walk(self.source_folder):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                        rel_path = Path(root) / file
                        images.append(rel_path)
        else:
            # Only top-level folder
            for file in self.source_folder.iterdir():
                if file.is_file() and any(file.name.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                    images.append(file)
        
        return sorted(images)
    
    def create_symlink(self, image_path):
        """Create symlink from ComfyUI input folder to source image
        Always creates symlink at root of comfyui_input_folder regardless of source subfolder
        """
        source_path = image_path
        # Use just the filename at root of ComfyUI input folder
        dest_path = self.comfyui_input_folder / image_path.name
        
        try:
            # Create ComfyUI input folder if it doesn't exist
            self.comfyui_input_folder.mkdir(parents=True, exist_ok=True)
            
            # Check if source exists
            if not source_path.exists():
                return False, f"Source file not found: {source_path}"
            
            # If symlink/file already exists, remove it first
            if dest_path.exists() or dest_path.is_symlink():
                dest_path.unlink()
            
            # Create symlink
            dest_path.symlink_to(source_path)
            
            # Track this symlink for potential cleanup
            self.created_symlinks.append(dest_path)
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def cleanup_symlinks(self):
        """Remove symlinks created by this script"""
        if not self.created_symlinks:
            return
        
        print()
        print("🧹 \033[93mCleaning up symlinks...\033[0m")
        
        cleaned = 0
        for symlink_path in self.created_symlinks:
            try:
                if symlink_path.is_symlink():
                    symlink_path.unlink()
                    cleaned += 1
            except Exception as e:
                print(f"   ⚠️  \033[93mCould not remove\033[0m {symlink_path.name}: {e}")
        
        if cleaned > 0:
            print(f"✅ \033[92mRemoved {cleaned} symlinks\033[0m")
    
    def update_workflow_image(self, workflow, image_filename):
        """Update the workflow to use a specific image"""
        if isinstance(workflow, dict):
            # API format
            if self.load_image_node_id in workflow:
                node = workflow[self.load_image_node_id]
                if 'inputs' in node:
                    node['inputs']['image'] = image_filename
                elif 'widgets_values' in node:
                    node['widgets_values'][0] = image_filename
        
        return workflow
    
    def submit_workflow(self, workflow):
        """Submit workflow to ComfyUI queue"""
        try:
            prompt_data = {
                "prompt": workflow,
                "client_id": self.client_id
            }
            
            response = requests.post(
                f"{self.server_url}/prompt",
                json=prompt_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get('prompt_id')
                return True, prompt_id
            else:
                return False, f"HTTP {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to ComfyUI"
        except Exception as e:
            return False, str(e)
    
    def check_comfyui_running(self):
        """Check if ComfyUI server is accessible"""
        try:
            response = requests.get(f"{self.server_url}/system_stats", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_queue_status(self):
        """Get current queue status"""
        try:
            response = requests.get(f"{self.server_url}/queue", timeout=5)
            if response.status_code == 200:
                data = response.json()
                queue_running = len(data.get('queue_running', []))
                queue_pending = len(data.get('queue_pending', []))
                return queue_running, queue_pending
            return 0, 0
        except:
            return 0, 0
    
    def process_all_images(self, include_subfolders=False, cleanup_after=False):
        """Main processing function"""
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mComfyUI Batch Processor\033[0m")
        if self.job_id:
            print(f"\033[93mJob ID:\033[0m {self.job_id}")
        print("\033[92m==================================================\033[0m")
        print()
        
        # Check ComfyUI connection
        print("🔍 \033[93mChecking ComfyUI connection...\033[0m")
        if not self.check_comfyui_running():
            print(f"❌ \033[93mCannot connect to ComfyUI at\033[0m {self.server_url}")
            print(f"   \033[93mMake sure ComfyUI is running!\033[0m")
            return False
        print(f"✅ \033[92mConnected to ComfyUI\033[0m")
        print()
        
        # Load workflow
        print("📂 \033[93mLoading workflow...\033[0m")
        base_workflow = self.load_workflow()
        if not base_workflow:
            return False
        print(f"✅ \033[92mLoaded workflow\033[0m")
        print()
        
        # Get images
        print("🖼️  \033[93mScanning for images...\033[0m")
        images = self.get_images(include_subfolders)
        if not images:
            print(f"❌ \033[93mNo images found in:\033[0m {self.source_folder}")
            print(f"   \033[93mSupported formats:\033[0m {', '.join(IMAGE_EXTENSIONS)}")
            return False
        
        print(f"✅ \033[92mFound {len(images)} images to process\033[0m")
        
        # Show sample of images
        print()
        print("\033[93mSample of images:\033[0m")
        for i, img in enumerate(images[:5], 1):
            print(f"  {i}. {img.name}")
        if len(images) > 5:
            print(f"  ... and {len(images) - 5} more")
        print()
        
        # Process each image
        successful = 0
        failed = 0
        symlinked = 0
        
        print("\033[93m" + "=" * 50 + "\033[0m")
        print("\033[1;33mProcessing Images\033[0m")
        print("\033[93m" + "=" * 50 + "\033[0m")
        
        for idx, image_path in enumerate(images, 1):
            print(f"\n\033[93m[{idx}/{len(images)}]\033[0m {image_path.name}")
            
            # Create symlink in ComfyUI input folder (always at root)
            print(f"    🔗 \033[93mCreating symlink...\033[0m")
            link_success, link_error = self.create_symlink(image_path)
            
            if not link_success:
                print(f"    ❌ \033[93mSymlink failed:\033[0m {link_error}")
                failed += 1
                continue
            
            symlinked += 1
            print(f"    ✅ \033[92mSymlinked\033[0m")
            
            # Update workflow with just the filename (symlink is at root)
            import copy
            workflow = copy.deepcopy(base_workflow)
            workflow = self.update_workflow_image(workflow, image_path.name)
            
            # Submit to queue
            print(f"    📤 \033[93mSubmitting to queue...\033[0m")
            submit_success, result = self.submit_workflow(workflow)
            
            if submit_success:
                print(f"    ✅ \033[92mQueued\033[0m (ID: {result})")
                successful += 1
            else:
                print(f"    ❌ \033[93mQueue failed:\033[0m {result}")
                failed += 1
            
            # Small delay between submissions
            if idx < len(images):
                time.sleep(QUEUE_DELAY)
        
        print()
        print("\033[93m" + "=" * 50 + "\033[0m")
        print("\033[1;33mSummary\033[0m")
        print("\033[93m" + "=" * 50 + "\033[0m")
        print(f"📁 \033[93mInput folder:\033[0m {self.source_folder}")
        print(f"⚙️  \033[93mWorkflow:\033[0m {Path(self.workflow_path).name}")
        print(f"🔗 \033[93mSymlinks created:\033[0m {symlinked}")
        print(f"✅ \033[92mSuccessfully queued:\033[0m {successful}")
        if failed > 0:
            print(f"❌ \033[93mFailed:\033[0m {failed}")
        
        # Check queue status
        running, pending = self.get_queue_status()
        print(f"📊 \033[93mQueue status:\033[0m {running} running, {pending} pending")
        print()
        print("💡 \033[93mComfyUI will process these images one by one.\033[0m")
        print("   \033[93mMonitor progress in the ComfyUI interface.\033[0m")
        
        # Cleanup symlinks if requested
        if cleanup_after:
            self.cleanup_symlinks()
        else:
            print()
            print("📌 \033[93mNote: Symlinks remain in ComfyUI input folder\033[0m")
            print(f"   \033[93mLocation:\033[0m {self.comfyui_input_folder}")
        
        print("\033[93m" + "=" * 50 + "\033[0m")
        print()
        
        return True


def main():
    """Main entry point"""
    while True:
        os.system('clear')
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mComfyUI Batch Processor\033[0m")
        print("Process images through ComfyUI workflows")
        print("\033[92m==================================================\033[0m")
        print()
        
        # 1. Get source folder
        source_folder = djj.get_path_input("📁 Enter source folder path")
        print()
        
        # Ask about subfolders
        include_subfolders = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        
        # 2. Get workflow path
        workflow_mode = djj.prompt_choice(
            "\033[93mWorkflow selection:\033[0m\n1. Load from default folder\n2. Custom path",
            ['1', '2'],
            default='1'
        )
        print()
        
        if workflow_mode == '1':
            # Select from default folder
            workflow_path = select_workflow_from_folder(DEFAULT_WORKFLOW_FOLDER)
            if not workflow_path:
                print("❌ \033[93mNo workflow selected. Exiting.\033[0m")
                action = djj.what_next()
                if action == 'exit':
                    break
                else:
                    continue
        else:
            # Custom path
            workflow_path = djj.get_path_input("📄 Enter workflow JSON path (API format)")
            print()
        
        # 3. Get load image node ID
        load_image_node = djj.get_string_input(
            "\033[93m🔢 Enter Load Image node ID (e.g., '8' or '189'):\033[0m\n > ",
            default=None
        )
        print()
        
        # 4. Ask about cleanup
        cleanup_after = djj.prompt_choice(
            "\033[93mCleanup symlinks after processing?\033[0m\n1. Yes\n2. No (leave for review)",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        
        # Get next job ID
        job_id = get_next_job_id()
        print(f"🆔 \033[93mJob ID:\033[0m {job_id}")
        print()
        
        # Create processor
        processor = ComfyUIBatchProcessor(
            workflow_path=workflow_path,
            source_folder=source_folder,
            comfyui_input_folder=COMFYUI_INPUT_FOLDER,
            load_image_node_id=load_image_node,
            job_id=job_id
        )
        
        # Get image list for logging
        images = processor.get_images(include_subfolders)
        
        if not images:
            print("❌ \033[93mNo images found. Skipping.\033[0m")
            action = djj.what_next()
            if action == 'exit':
                break
            else:
                continue
        
        # Log the job
        log_file = log_job(
            job_id=job_id,
            source_folder=source_folder,
            workflow_path=workflow_path,
            num_files=len(images),
            file_list=[str(img) for img in images]
        )
        
        print(f"📝 \033[93mLogged to:\033[0m {log_file}")
        print()
        
        # Create processor and run
        print("\033[1;33m🚀 Starting batch process...\033[0m")
        print()
        
        success = processor.process_all_images(
            include_subfolders=include_subfolders,
            cleanup_after=cleanup_after
        )
        
        if not success:
            print()
            print("❌ \033[93mBatch processing encountered errors\033[0m")
            print()
        
        # What next?
        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()