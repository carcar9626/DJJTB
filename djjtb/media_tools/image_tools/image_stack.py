import os
import subprocess
import sys
import pathlib
import logging
import djjtb.utils as djj
from PIL import Image, ImageFilter
from collections import defaultdict

def clear_screen():
    """Clear the terminal screen."""
    os.system('clear')

def setup_logging(output_path):
    """Set up logging to a file in the output folder."""
    log_file = os.path.join(output_path, 'pairing_errors.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def is_valid_image(file_path):
    """Check if a file is a valid image."""
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception as e:
        logging.error(f"Invalid image {file_path}: {e}")
        return False

def collect_images_from_folder(input_path, include_subfolders=False):
    """Collect images from folder(s)."""
    input_path_obj = pathlib.Path(input_path)
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
    
    images = []
    if input_path_obj.is_dir():
        if include_subfolders:
            for root, _, files in os.walk(input_path):
                images.extend(pathlib.Path(root) / f for f in files if pathlib.Path(f).suffix.lower() in image_extensions)
        else:
            images = [f for f in input_path_obj.glob('*') if f.suffix.lower() in image_extensions and f.is_file()]
    
    return sorted([str(v) for v in images], key=str.lower)

def collect_images_from_paths(file_paths):
    """Collect images from space-separated file paths."""
    images = []
    paths = file_paths.strip().split()
    
    for path in paths:
        path = path.strip('\'"')
        path_obj = pathlib.Path(path)
        
        if path_obj.is_file() and path_obj.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'):
            images.append(str(path_obj))
        elif path_obj.is_dir():
            images.extend(collect_images_from_folder(str(path_obj), include_subfolders=False))
    
    return sorted(images, key=str.lower)

def collect_images_from_txt():
    """Collect images from txt file (files and folders)."""
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
    paths = djj.get_paths_from_txt("Enter txt file path")
    
    if not paths:
        return []
    
    images = []
    for path in paths:
        path_obj = pathlib.Path(path)
        if path_obj.is_file():
            if path_obj.suffix.lower() in image_extensions:
                images.append(str(path))
        elif path_obj.is_dir():
            images.extend(collect_images_from_folder(str(path), include_subfolders=False))
    
    return sorted(set(images), key=str.lower)

def group_images_by_parent_folder(image_paths):
    """
    Group images by their immediate parent folder.
    Returns dict: {parent_folder_path: [image_paths]}
    """
    grouped = {}
    for img_path in image_paths:
        parent = str(pathlib.Path(img_path).parent)
        if parent not in grouped:
            grouped[parent] = []
        grouped[parent].append(img_path)
    return grouped

def get_match_key(filename, match_type, num_chars):
    """
    Extract match key from filename based on prefix/suffix.
    
    Args:
        filename: Full filename with extension
        match_type: 'prefix' or 'suffix'
        num_chars: Number of characters to use for matching
    
    Returns:
        Match key string
    """
    # Remove extension first
    name_no_ext = os.path.splitext(filename)[0]
    
    if match_type == 'prefix':
        return name_no_ext[:num_chars] if len(name_no_ext) >= num_chars else name_no_ext
    else:  # suffix
        return name_no_ext[-num_chars:] if len(name_no_ext) >= num_chars else name_no_ext

def group_images_by_match(images, match_type, num_chars):
    """
    Group images by their prefix/suffix match key.
    
    Returns:
        dict: {match_key: [image_paths]}
    """
    groups = defaultdict(list)
    
    for img_path in images:
        filename = os.path.basename(img_path)
        match_key = get_match_key(filename, match_type, num_chars)
        groups[match_key].append(img_path)
    
    return dict(groups)

def create_sequential_groups(images, group_size):
    """
    Create sequential groups of images.
    
    Args:
        images: List of image paths
        group_size: Number of images per group
    
    Returns:
        List of groups (each group is a list of image paths)
    """
    groups = []
    for i in range(0, len(images), group_size):
        group = images[i:i + group_size]
        if len(group) == group_size:  # Only include complete groups
            groups.append(group)
    return groups

def get_max_dimensions(image_paths):
    """Get maximum dimensions from a list of images, ensuring even numbers."""
    try:
        max_width = 0
        max_height = 0
        
        for img_path in image_paths:
            with Image.open(img_path) as img:
                max_width = max(max_width, img.width)
                max_height = max(max_height, img.height)
        
        # Ensure even numbers for video encoding
        max_width = max_width if max_width % 2 == 0 else max_width + 1
        max_height = max_height if max_height % 2 == 0 else max_height + 1
        
        return max_width, max_height
    except Exception as e:
        logging.error(f"Error getting image dimensions: {e}")
        return None

def prepare_image_with_background(img_path, canvas_width, canvas_height, bg_opacity=0.8, bg_blur=8):
    """
    Prepare an image with blurred background to fit canvas dimensions.
    Returns path to temporary processed image.
    """
    try:
        canvas = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
        img = Image.open(img_path)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create blurred background
        bg_img = img.copy()
        bg_img = bg_img.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=bg_blur))
        alpha = Image.new('L', bg_img.size, int(255 * bg_opacity))
        bg_img.putalpha(alpha)
        canvas.paste(bg_img, (0, 0), bg_img)
        
        # Scale and center foreground
        img_ratio = img.width / img.height
        target_width = canvas_width
        target_height = int(target_width / img_ratio)
        if target_height > canvas_height:
            target_height = canvas_height
            target_width = int(target_height * img_ratio)
        
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        paste_x = (canvas_width - target_width) // 2
        paste_y = (canvas_height - target_height) // 2
        canvas.paste(img, (paste_x, paste_y), img)
        
        return canvas
    except Exception as e:
        logging.error(f"Error preparing image {img_path}: {e}")
        return None

def process_image_group(image_group, output_path, durations, transition_duration, base_output_name):
    """
    Process a group of images into a video with transitions.
    
    Args:
        image_group: List of image paths to combine
        output_path: Directory for output video
        durations: List of durations for each image
        transition_duration: Duration of transition between images
        base_output_name: Base name for output file
    
    Returns:
        True if successful, False otherwise
    """
    # Get max dimensions
    resolution = get_max_dimensions(image_group)
    if not resolution:
        return False
    
    canvas_width, canvas_height = resolution
    
    # Create temp directory for preprocessed images
    temp_dir = os.path.join(output_path, "temp_pairing")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Preprocess all images with backgrounds
    processed_images = []
    for i, img_path in enumerate(image_group):
        canvas = prepare_image_with_background(img_path, canvas_width, canvas_height)
        if canvas is None:
            return False
        
        temp_path = os.path.join(temp_dir, f"prep_{i:04d}.png")
        canvas.convert('RGB').save(temp_path, 'PNG')
        processed_images.append(temp_path)
    
    # Build ffmpeg command
    cmd = ["ffmpeg", "-y"]
    
    # Add all images as inputs with their durations
    for i, (img_path, duration) in enumerate(zip(processed_images, durations)):
        cmd.extend(["-loop", "1", "-t", str(duration), "-i", img_path])
    
    # Build filter complex
    filter_parts = []
    overlay_chain = []
    
    for i in range(len(processed_images)):
        scale_filter = f"[{i}:v]scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=decrease,pad={canvas_width}:{canvas_height}:(ow-iw)/2:(oh-ih)/2,format=yuva420p"
        
        if i == 0:
            # First image: fade out at the end
            fade_filter = f"{scale_filter},fade=t=out:st={durations[i]-transition_duration}:d={transition_duration}:alpha=1,setpts=PTS-STARTPTS[va{i}]"
            filter_parts.append(fade_filter)
            overlay_chain.append(f"va{i}")
        else:
            # Subsequent images: fade in, offset by cumulative duration
            offset_time = sum(durations[:i]) - i * transition_duration
            fade_filter = f"{scale_filter},fade=t=in:st=0:d={transition_duration}:alpha=1,setpts=PTS-STARTPTS+{offset_time}/TB[va{i}]"
            filter_parts.append(fade_filter)
            overlay_chain.append(f"va{i}")
    
    # Chain overlays
    if len(processed_images) == 1:
        final_output = overlay_chain[0]
    else:
        current_base = overlay_chain[0]
        for i in range(1, len(overlay_chain)):
            overlay_filter = f"[{current_base}][{overlay_chain[i]}]overlay[ov{i}]"
            filter_parts.append(overlay_filter)
            current_base = f"ov{i}"
        final_output = current_base
    
    # Calculate total duration
    total_duration = sum(durations) - (len(durations) - 1) * transition_duration
    filter_parts.append(f"[{final_output}]trim=duration={total_duration}")
    
    filter_complex = ";".join(filter_parts)
    
    # Output file
    output_file = os.path.join(output_path, f"{base_output_name}_paired.mp4")
    
    cmd.extend([
        "-filter_complex", filter_complex,
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "veryfast",
        "-r", "30",
        "-t", str(total_duration),
        "-fps_mode", "cfr",
        output_file
    ])
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Clean up temp files
        for temp_file in processed_images:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
        
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error creating video: {e.stderr}")
        return False

def process_all_groups(groups, durations, transition_duration, use_parent_output=False, output_subfolder="Paired"):
    """
    Process all image groups into videos.
    
    Args:
        groups: List of image groups to process
        durations: List of durations for each image in group
        transition_duration: Transition duration between images
        use_parent_output: If True, output to each image's parent/Output/Paired
    
    Returns:
        (success_count, error_count, output_folders)
    """
    success_count = 0
    error_count = 0
    total_groups = len(groups)
    output_folders = set()
    
    for idx, group in enumerate(groups, 1):
        sys.stdout.write(f"\r\033[93mProcessing \033[0m{idx}/{total_groups} \033[93mgroups\033[0m ({idx/total_groups*100:.1f}%)...")
        sys.stdout.flush()
        
        # Validate all images in group
        if not all(is_valid_image(img) for img in group):
            error_count += 1
            continue
        
        # Determine output location
        first_img = pathlib.Path(group[0])
        parent_folder = str(first_img.parent)
        output_dir = os.path.join(parent_folder, "Output", output_subfolder)
        
        os.makedirs(output_dir, exist_ok=True)
        output_folders.add(output_dir)
        
        # Create base output name from first image
        filename_noext = first_img.stem.split('_', 1)[1] if '_' in first_img.stem else first_img.stem
        
        # Process the group
        if process_image_group(group, output_dir, durations, transition_duration, filename_noext):
            success_count += 1
        else:
            error_count += 1
    
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()
    
    return success_count, error_count, list(output_folders)


if __name__ == "__main__":
    while True:
        clear_screen()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mImage Stack\033[0m")
        print("Collage Sequential Groups")
        print("\033[92m==================================================\033[0m")
        print()

        # ── Input ────────────────────────────────────────────────────────────
        input_mode = djj.prompt_choice(
            "\033[93mInput mode:\033[0m\n"
            "1. Folder path\n"
            "2. Space-separated file paths\n"
            "3. Path list from txt file\n",
            ['1', '2', '3'],
            default='1'
        )
        print()

        images = []
        input_path = None
        include_subfolders = False

        if input_mode == '1':
            input_path = djj.get_path_input("Enter folder path")
            print()
            include_subfolders = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'], default='2'
            ) == '1'
            print()
            images = collect_images_from_folder(input_path, include_subfolders)

        elif input_mode == '2':
            file_paths = input("📁 \033[93mEnter image paths (space-separated):\033[0m\n -> ").strip()
            if not file_paths:
                print("❌ \033[1;5;93mNo file paths provided.\033[0m")
                continue
            images = collect_images_from_paths(file_paths)
            if images:
                input_path = str(pathlib.Path(images[0]).parent)
            print()

        else:
            images = collect_images_from_txt()
            if not images:
                print("❌ \033[93mNo valid images found.\033[0m")
                continue
            if images:
                input_path = str(pathlib.Path(images[0]).parent)
            print()

        if not images:
            print("❌ \033[93mNo valid image files found. Try again.\033[0m\n")
            continue

        print(f"✅ {len(images)} \033[93mimages found\033[0m")
        print()

        # ── Top-level mode ───────────────────────────────────────────────────
        top_mode = djj.prompt_choice(
            "\033[93mMode:\033[0m\n"
            "1. Pairing only\n"
            "2. Collage only\n"
            "3. Collage then Pair\n",
            ['1', '2', '3'],
            default='2'
        )
        print()

        # ── Shared: group size (all modes need it) ───────────────────────────
        while True:
            try:
                gs = input("\033[93mImages per group\033[0m [default: 2]:\n -> ").strip()
                group_size = int(gs) if gs else 2
                if group_size > 0:
                    break
                print("\033[93mPlease enter a positive number.\033[0m")
            except ValueError:
                print("\033[93mPlease enter a valid number.\033[0m")
        print()

        # ── Collage settings (modes 2 and 3) ─────────────────────────────────
        direction = None
        longest_edge = None

        if top_mode in ['2', '3']:
            direction_choice = djj.prompt_choice(
                "\033[93mStack direction:\033[0m\n1. Horizontal\n2. Vertical\n",
                ['1', '2'], default='1'
            )
            direction = 'H' if direction_choice == '1' else 'V'
            print()

            edge_choice = djj.prompt_choice(
                "\033[93mLongest edge:\033[0m\n"
                "1. 1920px\n"
                "2. Custom\n"
                "3. 2× shorter edge of first image\n",
                ['1', '2', '3'], default='1'
            )
            if edge_choice == '1':
                longest_edge = 1920
            elif edge_choice == '2':
                longest_edge = djj.get_int_input("Enter longest edge in px", min_val=256, max_val=8192)
            else:
                from PIL import Image as _PIL_Edge
                with _PIL_Edge.open(images[0]) as _im:
                    _w, _h = _im.size
                longest_edge = min(_w, _h) * 2
                print(f"\033[93mFirst image: {_w}×{_h} → shorter edge {min(_w, _h)} × 2 = {longest_edge}px\033[0m")
            print()

        # ── Pairing settings (modes 1 and 3) ─────────────────────────────────
        pairing_mode = None
        match_type = None
        num_chars = None
        durations = []
        transition_duration = 1.0

        if top_mode in ['1', '3']:
            pairing_mode = djj.prompt_choice(
                "\033[93mPairing mode:\033[0m\n"
                "1. Manual (sequential groups)\n"
                "2. Auto-match (by prefix/suffix)\n",
                ['1', '2'], default='1'
            )
            print()

            if pairing_mode == '2':
                match_type_choice = djj.prompt_choice(
                    "\033[93mMatch by:\033[0m\n1. Prefix\n2. Suffix\n",
                    ['1', '2'], default='1'
                )
                match_type = 'prefix' if match_type_choice == '1' else 'suffix'
                print()
                while True:
                    try:
                        nc = input(f"\033[93mNumber of characters for {match_type} match\033[0m [default: 4]:\n -> ").strip()
                        num_chars = int(nc) if nc else 4
                        if num_chars > 0:
                            break
                        print("\033[93mPlease enter a positive number.\033[0m")
                    except ValueError:
                        print("\033[93mPlease enter a valid number.\033[0m")
                print()

            for i in range(group_size):
                while True:
                    try:
                        d = input(f"\033[93mDuration for image {i+1} (seconds)\033[0m [default: 5]:\n -> ").strip()
                        duration = float(d) if d else 5.0
                        if duration > 0:
                            break
                        print("\033[93mPlease enter a positive number.\033[0m")
                    except ValueError:
                        print("\033[93mPlease enter a valid number.\033[0m")
                durations.append(duration)
                print()

            while True:
                try:
                    t = input("\033[93mTransition duration (seconds)\033[0m [default: 1]:\n -> ").strip()
                    transition_duration = float(t) if t else 1.0
                    if transition_duration >= 0:
                        break
                    print("\033[93mPlease enter a non-negative number.\033[0m")
                except ValueError:
                    print("\033[93mPlease enter a valid number.\033[0m")
            print()

            total_dur = sum(durations) - (len(durations) - 1) * transition_duration
            print(f"\033[93mTotal video duration:\033[0m {total_dur}s")
            print("-------------")
            print()

        # ── Setup logging ────────────────────────────────────────────────────
        log_root = input_path or str(pathlib.Path(images[0]).parent)
        log_output = os.path.join(log_root, "Output", "Paired")
        os.makedirs(log_output, exist_ok=True)
        setup_logging(log_output)

        # ── Processing ───────────────────────────────────────────────────────
        working_images = images
        output_subfolder = "Paired"

        if top_mode in ['2', '3']:
            comp_dir = os.path.join(log_root, "Output", "Comp")
            collage_paths = djj.create_collage(
                working_images, direction, longest_edge, comp_dir, group_size
            )
            print()

            if top_mode == '2':
                # Collage only — open folder and finish
                if collage_paths:
                    djj.prompt_open_folder(comp_dir)
                action = djj.what_next()
                if action == 'exit':
                    break
                continue

            # Mode 3: feed collages into pairing
            if not collage_paths:
                print("\033[93m❌ No collages were created. Cannot continue to pairing.\033[0m")
                action = djj.what_next()
                if action == 'exit':
                    break
                continue

            working_images = collage_paths
            output_subfolder = "Comp_Paired"
            print(f"\033[93m{len(working_images)} collage(s) ready for pairing\033[0m")
            print()

        # ── Pairing (modes 1 and 3) ──────────────────────────────────────────
        process_by_folder = (include_subfolders and input_mode == '1') or (input_mode in ['2', '3'])

        if process_by_folder:
            folder_groups_map = group_images_by_parent_folder(working_images)
            print(f"\033[93mProcessing {len(folder_groups_map)} folders separately...\033[0m")
            print()

            total_success = 0
            total_error = 0
            all_output_folders = []

            for folder_path, folder_images in folder_groups_map.items():
                if pairing_mode == '1':
                    groups = create_sequential_groups(folder_images, group_size)
                else:
                    matched = group_images_by_match(folder_images, match_type, num_chars)
                    groups = [v[:group_size] for v in matched.values() if len(v) >= group_size]

                if groups:
                    success, error, outputs = process_all_groups(
                        groups, durations, transition_duration,
                        use_parent_output=True, output_subfolder=output_subfolder
                    )
                    total_success += success
                    total_error += error
                    all_output_folders.extend(outputs)

            success_count = total_success
            error_count = total_error
            output_folders = all_output_folders

        else:
            if pairing_mode == '1':
                groups = create_sequential_groups(working_images, group_size)
            else:
                matched = group_images_by_match(working_images, match_type, num_chars)
                groups = [v[:group_size] for v in matched.values() if len(v) >= group_size]

            if not groups:
                print("\033[93mNo complete groups found.\033[0m")
                continue

            print(f"\033[93mFound {len(groups)} complete groups\033[0m")
            print()

            success_count, error_count, output_folders = process_all_groups(
                groups, durations, transition_duration,
                use_parent_output=True, output_subfolder=output_subfolder
            )

        # ── Summary ──────────────────────────────────────────────────────────
        print()
        print("\033[93mPairing Summary\033[0m")
        print("-------------")
        print(f"✅ \033[93mSuccessfully processed:\033[0m {success_count} groups")
        if error_count:
            print(f"\033[93mFailed:\033[0m {error_count} (see pairing_errors.log)")

        if len(output_folders) == 1:
            print(f"\033[93mOutput:\033[0m {output_folders[0]}")
        else:
            print(f"\033[93mOutput folders:\033[0m {len(output_folders)}")
            for f in output_folders[:3]:
                print(f"  - {f}")
            if len(output_folders) > 3:
                print(f"  ... and {len(output_folders) - 3} more")
        print()

        if output_folders:
            djj.prompt_open_folder(output_folders[0])

        action = djj.what_next()
        if action == 'exit':
            break

    clear_screen()