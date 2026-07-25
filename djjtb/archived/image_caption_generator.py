#!/usr/bin/env python3
"""
Image Caption Generator for DJJTB
Generate dual-format image descriptions: Natural + SD-style prompts
Uses Florence-2 + WD-v1-4 tagger (PyTorch) for accurate Danbooru tags
Version: 2.5 - Clean PyTorch
"""

import os
import sys
import gc
from pathlib import Path
from typing import List, Optional

# Environment and venv paths
VENV_PATH = "/Users/home/Documents/ai_models/watermark_remover/wmrmvenv"
VENV_PYTHON = os.path.join(VENV_PATH, "bin", "python")

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def ensure_venv_and_run():
    if not os.path.exists(VENV_PATH):
        print("❌ \033[93mVirtual environment not found at\033[0m", VENV_PATH)
        return False
    
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        current_venv = sys.prefix
        if VENV_PATH in current_venv:
            return True
    
    if os.path.exists(VENV_PYTHON):
        print("\033[93m🔄 Activating watermark remover environment...\033[0m")
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root)
        os.execve(VENV_PYTHON, [VENV_PYTHON] + sys.argv, env)
    else:
        print(f"❌ \033[93mPython executable not found in venv:\033[0m {VENV_PYTHON}")
        return False

try:
    import djjtb.utils as djj
    print("✅ \033[93mDJJTB utils loaded successfully\033[0m")
except ImportError as e:
    print(f"❌ \033[93mFailed to import djjtb.utils:\033[0m {e}")
    sys.exit(1)

MODEL_CACHE_DIR = "/Users/home/Documents/ai_models/Florence"
SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
WD_MODEL = "SmilingWolf/wd-vit-tagger-v3"

FLORENCE_AVAILABLE = None
WD_AVAILABLE = None
DEVICE = None

def setup_model_cache():
    os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
    os.environ['HF_HOME'] = MODEL_CACHE_DIR
    print(f"📁 \033[93mModel cache:\033[0m {MODEL_CACHE_DIR}")

def check_dependencies():
    global FLORENCE_AVAILABLE, WD_AVAILABLE, DEVICE
    
    print("\033[93m🔍 Checking dependencies...\033[0m")
    
    required = {'torch': 'torch', 'transformers': 'transformers', 'PIL': 'Pillow', 'einops': 'einops', 'timm': 'timm'}
    missing = []
    
    for imp, pkg in required.items():
        try:
            __import__('PIL' if imp == 'PIL' else imp)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"❌ \033[93mMissing:\033[0m {', '.join(missing)}")
        import subprocess
        for pkg in missing:
            print(f"   Installing {pkg}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])
    
    try:
        from transformers import AutoProcessor, AutoModelForCausalLM
        FLORENCE_AVAILABLE = True
        print("✅ \033[93mFlorence-2 available\033[0m")
    except:
        FLORENCE_AVAILABLE = False
        return False
    
    try:
        import torch
        if torch.backends.mps.is_available():
            DEVICE = "mps"
            print("✅ \033[93mDevice: MPS\033[0m")
        else:
            DEVICE = "cpu"
            print("✅ \033[93mDevice: CPU\033[0m")
    except:
        DEVICE = "cpu"
    
    # Check WD availability
    try:
        from huggingface_hub import hf_hub_download
        WD_AVAILABLE = True
        print("✅ \033[93mWD tagger available\033[0m")
    except:
        WD_AVAILABLE = False
        print("⚠️  \033[93mWD tagger unavailable (optional)\033[0m")
    
    print()
    return True

def collect_images_from_folder(input_path, subfolders=False):
    input_path_obj = Path(input_path)
    images = []
    if input_path_obj.is_dir():
        if subfolders:
            for root, _, filenames in os.walk(input_path):
                images.extend(Path(root) / f for f in filenames if Path(f).suffix.lower() in SUPPORTED_EXTS)
        else:
            images = [f for f in input_path_obj.glob('*') if f.suffix.lower() in SUPPORTED_EXTS and f.is_file()]
    return sorted([str(f) for f in images], key=str.lower)

def collect_images_from_paths(file_paths):
    images = []
    for path in file_paths.strip().split():
        path = path.strip('\'"')
        path_obj = Path(path)
        if path_obj.is_file() and path_obj.suffix.lower() in SUPPORTED_EXTS:
            images.append(str(path_obj))
        elif path_obj.is_dir():
            images.extend(collect_images_from_folder(path))
    return sorted(images, key=str.lower)

def collect_images_from_txt():
    """Collect images from txt file (files and folders)"""
    try:
        txt_path = djj.get_path_input("Enter txt file path")
        
        if not os.path.exists(txt_path):
            print("❌ \033[93mFile not found\033[0m")
            return []
        
        with open(txt_path, 'r', encoding='utf-8') as f:
            paths = [line.strip() for line in f if line.strip()]
        
        images = []
        for path in paths:
            path_obj = Path(path)
            if path_obj.is_file() and path_obj.suffix.lower() in SUPPORTED_EXTS:
                images.append(str(path_obj))
            elif path_obj.is_dir():
                images.extend(collect_images_from_folder(str(path_obj), include_subfolders=False))
        
        return sorted(set(images), key=str.lower)
    except Exception as e:
        print(f"❌ \033[93mError reading txt file:\033[0m {e}")
        return []

def get_valid_inputs():
    print("\033[1;93m🖼️  Select images to caption\033[0m")
    input_mode = djj.prompt_choice("\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n3. Path list from txt file\n", ['1', '2', '3'], default='1')
    print()
    
    valid_paths = []
    src_path = None
    
    if input_mode == '1':
        src_path = djj.get_path_input("Enter folder path")
        print()
        include_sub = djj.prompt_choice("\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No", ['1', '2'], default='2') == '1'
        print()
        valid_paths = collect_images_from_folder(src_path, include_sub)
    elif input_mode == '2':
        file_paths = input("📁 \033[93mEnter image paths (space-separated):\033[0m\n -> ").strip()
        if not file_paths:
            print("❌ \033[93mNo file paths provided.\033[0m")
            sys.exit(1)
        valid_paths = collect_images_from_paths(file_paths)
        print()
    else:  # input_mode == '3'
        valid_paths = collect_images_from_txt()
        if valid_paths and not src_path:
            src_path = str(Path(valid_paths[0]).parent)
        print()
    
    if not valid_paths:
        print("❌ \033[93mNo valid image files found.\033[0m")
        sys.exit(1)
    
    os.system('clear')
    print("\n" * 2)
    print(f"✅ \033[93mFound\033[0m {len(valid_paths)} \033[93msupported image(s)\033[0m")
    print()
    return valid_paths, input_mode, src_path

def get_caption_options():
    print("\033[1;93m⚙️  Caption Options\033[0m")
    print()
    
    model_choice = djj.prompt_choice("\033[93mModel size:\033[0m\n1. Florence-2-base (Faster, ~0.5GB)\n2. Florence-2-large (Better quality, ~1GB)\n", ['1', '2'], default='1')
    model_name = "microsoft/Florence-2-base" if model_choice == '1' else "microsoft/Florence-2-large"
    print(f"✅ \033[93mSelected:\033[0m {model_name.split('/')[-1]}")
    print()
    
    # Natural caption detail level
    detail_choice = djj.prompt_choice(
        "\033[93mNatural caption detail:\033[0m\n"
        "1. Brief (1 sentence)\n"
        "2. Detailed (2-3 sentences)\n"
        "3. Very detailed (full paragraph)\n",
        ['1', '2', '3'],
        default='3'
    )
    
    detail_map = {
        '1': '<CAPTION>',
        '2': '<DETAILED_CAPTION>',
        '3': '<MORE_DETAILED_CAPTION>'
    }
    natural_task = detail_map[detail_choice]
    print(f"✅ \033[93mDetail level:\033[0m {['Brief', 'Detailed', 'Very detailed'][int(detail_choice)-1]}")
    print()
    
    sd_options = ["1. Regex tags (quick)", "2. Sentence (natural)"]
    if WD_AVAILABLE:
        sd_options.insert(1, "2. WD tagger (accurate booru tags)")
        sd_options[2] = "3. Sentence (natural)"
    
    sd_choice = djj.prompt_choice("\033[93mSD prompt style:\033[0m\n" + "\n".join(sd_options) + "\n", ['1', '2', '3'] if WD_AVAILABLE else ['1', '2'], default='2' if WD_AVAILABLE else '1')
    
    if WD_AVAILABLE:
        sd_mode = {'1': 'regex', '2': 'wd', '3': 'sentence'}[sd_choice]
    else:
        sd_mode = {'1': 'regex', '2': 'sentence'}[sd_choice]
    
    print(f"✅ \033[93mSelected:\033[0m {sd_mode.upper()}")
    print()
    
    batch_input = input("\033[93mBatch size [1-5, default: 2]:\033[0m\n > ").strip()
    batch_size = max(1, min(5, int(batch_input) if batch_input else 2))
    print(f"✅ \033[93mBatch size:\033[0m {batch_size}")
    print()
    
    return {'model_name': model_name, 'natural_task': natural_task, 'sd_mode': sd_mode, 'batch_size': batch_size}

class ImageCaptioner:
    def __init__(self, model_name: str, use_wd: bool = False):
        self.model_name = model_name
        self.model = None
        self.processor = None
        self.device = DEVICE
        self.use_wd = use_wd
        self.wd_model = None
        
        print(f"📥 \033[93mLoading Florence-2...\033[0m")
        self._load_florence()
        
        if use_wd:
            print(f"📥 \033[93mLoading WD tagger...\033[0m")
            self._load_wd()
    
    def _load_florence(self):
        try:
            from transformers import AutoProcessor, AutoModelForCausalLM
            import torch
            
            self.processor = AutoProcessor.from_pretrained(self.model_name, trust_remote_code=True, cache_dir=MODEL_CACHE_DIR)
            self.model = AutoModelForCausalLM.from_pretrained(self.model_name, trust_remote_code=True, torch_dtype=torch.float32, attn_implementation="eager", cache_dir=MODEL_CACHE_DIR)
            
            #if self.device == "mps":
                #self.model = self.model.to("mps")
            
            print(f"   ✅ Florence-2 loaded")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            raise
    
    def _load_wd(self):
        try:
            import torch
            import numpy as np
            from huggingface_hub import hf_hub_download
            from PIL import Image
            
            # Download label file
            label_path = hf_hub_download(WD_MODEL, "selected_tags.csv", cache_dir=MODEL_CACHE_DIR)
            
            # Load labels
            import csv
            self.wd_labels = []
            with open(label_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.wd_labels.append(row['name'])
            
            # Load model using timm
            import timm
            self.wd_model = timm.create_model("hf-hub:SmilingWolf/wd-vit-tagger-v3", pretrained=True).eval()
            
            if self.device == "mps":
                self.wd_model = self.wd_model.to("mps")
            
            # Get transforms
            from timm.data import resolve_data_config
            from timm.data.transforms_factory import create_transform
            config = resolve_data_config(self.wd_model.pretrained_cfg, model=self.wd_model)
            self.wd_transform = create_transform(**config)
            
            print(f"   ✅ WD tagger loaded ({len(self.wd_labels)} tags)")
        except Exception as e:
            print(f"   ❌ WD failed: {e}")
            self.use_wd = False
    
    def generate_caption(self, image_path: str, task: str = "<MORE_DETAILED_CAPTION>") -> str:
        try:
            from PIL import Image
            import torch
            
            image = Image.open(image_path).convert("RGB")
            
            # Process inputs - ensure we get valid tensors
            inputs = self.processor(text=task, images=image, return_tensors="pt")
            
            # Debug: Check if pixel_values exists
            if "pixel_values" not in inputs or inputs["pixel_values"] is None:
                print(f"   ⚠️  Processor didn't create pixel_values - retrying with explicit image")
                inputs = self.processor(text=task, images=[image], return_tensors="pt")
            
            # Move to device (MPS or CPU)
            # if self.device == "mps":
            #     inputs = {k: v.to("mps") if v is not None else None for k, v in inputs.items()}
            
            # Ensure pixel_values exists before generation
            if "pixel_values" not in inputs or inputs["pixel_values"] is None:
                print(f"   ❌ Failed to create pixel_values from image")
                return ""
            
            with torch.no_grad():
                generated_ids = self.model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    max_new_tokens=1024,
                    num_beams=1,
                    do_sample=False
                )
            
            generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
            caption = generated_text.replace(task, "").replace("</s>", "").strip()
            return caption
        except Exception as e:
            import traceback
            print(f"   ❌ Caption failed: {e}")
            print(f"   Stack trace:")
            traceback.print_exc()
            return ""
    
    def generate_wd_tags(self, image_path: str, threshold: float = 0.35) -> str:
        try:
            from PIL import Image
            import torch
            
            if not self.use_wd or self.wd_model is None:
                return ""
            
            image = Image.open(image_path).convert("RGB")
            tensor = self.wd_transform(image).unsqueeze(0)
            
            if self.device == "mps":
                tensor = tensor.to("mps")
            
            with torch.no_grad():
                outputs = self.wd_model(tensor)
                probs = torch.sigmoid(outputs)
            
            # Get tags above threshold
            tags = []
            for idx, prob in enumerate(probs[0]):
                if prob > threshold and idx < len(self.wd_labels):
                    tags.append((self.wd_labels[idx], float(prob)))
            
            tags.sort(key=lambda x: x[1], reverse=True)
            tag_strings = [tag[0].replace('_', ' ') for tag in tags]
            
            return ", ".join(tag_strings) if tag_strings else "1girl, solo"
        except Exception as e:
            print(f"   ❌ WD tagging failed: {e}")
            return ""
    
    def convert_to_sd_prompt(self, caption: str, mode: str = 'regex') -> str:
        if mode == 'sentence':
            import re
            caption = re.sub(r'\bThe image (?:is|shows|depicts)\s+', '', caption, flags=re.IGNORECASE)
            caption = re.sub(r'\s+', ' ', caption).strip()
            return caption[0].upper() + caption[1:] if caption else ""
        
        # Regex mode
        import re
        tags = []
        cl = caption.lower()
        
        if re.search(r'\b(woman|girl)\b', cl):
            tags.append('1girl')
        elif re.search(r'\b(man|boy)\b', cl):
            tags.append('1boy')
        
        if tags and not re.search(r'\b(two|group|multiple)\b', cl):
            tags.append('solo')
        
        for color in ['blonde', 'brown', 'black', 'red', 'white', 'silver', 'pink', 'blue', 'green']:
            if re.search(rf'\b{color}\s+hair\b', cl):
                tags.append(f'{color} hair')
                break
        
        if re.search(r'\blong\s+hair\b', cl):
            tags.append('long hair')
        elif re.search(r'\bshort\s+hair\b', cl):
            tags.append('short hair')
        
        if re.search(r'\blooking.*(camera|viewer)\b', cl):
            tags.append('looking at viewer')
        
        if re.search(r'\bsmil', cl):
            tags.append('smile')
        elif re.search(r'\bserious\b', cl):
            tags.append('serious')
        
        if re.search(r'\bbreast', cl):
            tags.append('breasts')
        if re.search(r'\bnavel\b', cl):
            tags.append('navel')
        
        for item in ['hat', 'shirt', 'dress', 'shorts', 'pants', 'jacket', 'boots']:
            if re.search(rf'\b{item}\b', cl):
                tags.append(item)
        
        if re.search(r'\b(simple|solid)\s+background', cl):
            tags.append('simple background')
        
        for color in ['blue', 'white', 'black', 'gray']:
            if re.search(rf'\b{color}\s+background', cl):
                tags.append(f'{color} background')
                break
        
        return ', '.join(tags) if tags else '1girl, solo'
    
    def cleanup(self):
        if self.model:
            del self.model
            self.model = None
        if self.processor:
            del self.processor
            self.processor = None
        if self.wd_model:
            del self.wd_model
            self.wd_model = None
        
        try:
            import torch
            gc.collect()
            if DEVICE == "mps":
                torch.mps.empty_cache()
        except:
            pass

def process_images_batch(image_paths: List[str], options: dict, src_path: Optional[str]):
    print("\n" * 2)
    print(f"\n\033[1;93m🧠 Processing\033[0m {len(image_paths)} \033[1;93mimage(s)\033[0m")
    print("=" * 50)
    print(f"\033[93m🤖 Model:\033[0m {options['model_name'].split('/')[-1]}")
    print(f"\033[93m🎨 SD mode:\033[0m {options['sd_mode'].upper()}")
    print(f"\033[93m📦 Batch:\033[0m {options['batch_size']}")
    print("=" * 50)
    print()
    
    use_wd = options['sd_mode'] == 'wd'
    captioner = ImageCaptioner(options['model_name'], use_wd=use_wd)
    
    success = 0
    error = 0
    output_folders = set()
    
    batch_size = options['batch_size']
    total_batches = (len(image_paths) + batch_size - 1) // batch_size
    
    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        end = min((batch_idx + 1) * batch_size, len(image_paths))
        batch = image_paths[start:end]
        
        print(f"\033[1;93m📦 Batch {batch_idx + 1}/{total_batches}\033[0m")
        print()
        
        for i, img_path in enumerate(batch):
            idx = start + i + 1
            fname = os.path.basename(img_path)
            print(f"\033[93m[{idx}/{len(image_paths)}]\033[0m {fname}")
            
            try:
                img_dir = Path(img_path).parent
                out_dir = img_dir / "Output" / "Captions"
                out_dir.mkdir(parents=True, exist_ok=True)
                
                stem = Path(img_path).stem
                
                # Separate paths for natural and SD captions
                nat_dir = out_dir / "Natural"
                nat_dir.mkdir(parents=True, exist_ok=True)
                nat_path = nat_dir / f"{stem}.txt"
                
                # SD captions go to Danbooru or Natural based on mode
                if options['sd_mode'] == 'wd':
                    sd_dir = out_dir / "Danbooru"
                else:
                    sd_dir = out_dir / "SD_Prompts"
                
                sd_dir.mkdir(parents=True, exist_ok=True)
                sd_path = sd_dir / f"{stem}.txt"
                
                output_folders.add(nat_dir)
                output_folders.add(sd_dir)
                
                print(f"   📝 Natural...")
                nat_cap = captioner.generate_caption(img_path, options['natural_task'])
                
                if nat_cap:
                    with open(nat_path, 'w', encoding='utf-8') as f:
                        f.write(nat_cap)
                    print(f"   💬 \"{nat_cap[:50]}...\"")
                    
                    print(f"   🎨 SD tags...")
                    if options['sd_mode'] == 'wd':
                        sd_cap = captioner.generate_wd_tags(img_path)
                    else:
                        sd_cap = captioner.convert_to_sd_prompt(nat_cap, options['sd_mode'])
                    
                    with open(sd_path, 'w', encoding='utf-8') as f:
                        f.write(sd_cap)
                    print(f"   🏷️  \"{sd_cap[:50]}...\"")
                    print(f"   ✅ \033[92mSaved\033[0m")
                    success += 1
                else:
                    error += 1
            except Exception as e:
                print(f"   ❌ {e}")
                error += 1
            print()
        
        print(f"\033[93m🧹 Memory cleanup...\033[0m")
        gc.collect()
        try:
            import torch
            if DEVICE == "mps":
                torch.mps.empty_cache()
        except:
            pass
        print()
    
    captioner.cleanup()
    
    print("=" * 50)
    print(f"\033[1;93m🏁 Complete!\033[0m")
    print(f"✅ \033[92mSuccess:\033[0m {success}")
    print(f"❌ \033[93mFailed:\033[0m {error}")
    print("=" * 50)
    
    if len(output_folders) == 1:
        djj.prompt_open_folder(list(output_folders)[0])
    elif len(output_folders) > 1:
        choice = djj.prompt_choice("\033[93mOpen folders?\033[0m\n1. All\n2. First\n3. No", ['1', '2', '3'], default='2')
        if choice == '1':
            import subprocess
            for f in sorted(output_folders)[:5]:
                subprocess.run(['open', str(f)])
        elif choice == '2':
            import subprocess
            subprocess.run(['open', str(sorted(output_folders)[0])])

def main():
    os.system('clear')
    
    if not ensure_venv_and_run():
        return
    
    setup_model_cache()
    
    if not check_dependencies():
        print("\n\033[93mSetup failed\033[0m")
        return
    
    while True:
        print()
        print("\033[92m" + "=" * 50 + "\033[0m")
        print("\033[1;93mImage Caption Generator v2.5\033[0m")
        print("🔹 Natural descriptions (Florence-2)")
        print("🔹 SD tags (Regex / WD tagger / Sentence)")
        print("🤖 Perfect for exploration phase")
        print("\033[92m" + "=" * 50 + "\033[0m")
        print()
        
        try:
            image_paths, input_mode, src_path = get_valid_inputs()
            options = get_caption_options()
            os.system('clear')
            process_images_batch(image_paths, options, src_path)
            
            action = djj.what_next()
            if action == 'exit':
                break
        except KeyboardInterrupt:
            print("\n\033[93mCancelled\033[0m")
            break
        except Exception as e:
            print(f"\n❌ {e}")
            import traceback
            traceback.print_exc()
            break

if __name__ == "__main__":
    main()