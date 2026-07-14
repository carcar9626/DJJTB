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
    """Extract match key from filename based on prefix/suffix."""
    name_no_ext = os.path.splitext(filename)[0]
    if match_type == 'prefix':
        return name_no_ext[:num_chars] if len(name_no_ext) >= num_chars else name_no_ext
    else:
        return name_no_ext[-num_chars:] if len(name_no_ext) >= num_chars else name_no_ext

def group_images_by_match(images, match_type, num_chars):
    """Group images by their prefix/suffix match key."""
    groups = defaultdict(list)
    for img_path in images:
        filename = os.path.basename(img_path)
        match_key = get_match_key(filename, match_type, num_chars)
        groups[match_key].append(img_path)
    return dict(groups)

def create_sequential_groups(images, group_size):
    """Create sequential groups of images, only including complete groups."""
    groups = []
    for i in range(0, len(images), group_size):
        group = images[i:i + group_size]
        if len(group) == group_size:
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
        max_width = max_width if max_width % 2 == 0 else max_width + 1
        max_height = max_height if max_height % 2 == 0 else max_height + 1
        return max_width, max_height
    except Exception as e:
        logging.error(f"Error getting image dimensions: {e}")
        return None

def prepare_image_with_background(img_path, canvas_width, canvas_height, bg_opacity=0.8, bg_blur=8):
    """Prepare an image with blurred background to fit canvas dimensions."""
    try:
        canvas = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
        img = Image.open(img_path)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        bg_img = img.copy()
        bg_img = bg_img.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=bg_blur))
        alpha = Image.new('L', bg_img.size, int(255 * bg_opacity))
        bg_img.putalpha(alpha)
        canvas.paste(bg_img, (0, 0), bg_img)

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
    """Process a group of images into a dissolve slideshow video."""
    resolution = get_max_dimensions(image_group)
    if not resolution:
        return False

    canvas_width, canvas_height = resolution

    temp_dir = os.path.join(output_path, "temp_pairing")
    os.makedirs(temp_dir, exist_ok=True)

    processed_images = []
    for i, img_path in enumerate(image_group):
        canvas = prepare_image_with_background(img_path, canvas_width, canvas_height)
        if canvas is None:
            return False
        temp_path = os.path.join(temp_dir, f"prep_{i:04d}.png")
        canvas.convert('RGB').save(temp_path, 'PNG')
        processed_images.append(temp_path)

    cmd = ["ffmpeg", "-y"]
    for i, (img_path, duration) in enumerate(zip(processed_images, durations)):
        cmd.extend(["-loop", "1", "-t", str(duration), "-i", img_path])

    filter_parts = []
    overlay_chain = []

    for i in range(len(processed_images)):
        scale_filter = (
            f"[{i}:v]scale={canvas_width}:{canvas_height}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={canvas_width}:{canvas_height}:(ow-iw)/2:(oh-ih)/2,"
            f"format=yuva420p"
        )
        if i == 0:
            fade_filter = (
                f"{scale_filter},"
                f"fade=t=out:st={durations[i]-transition_duration}:d={transition_duration}:"
                f"alpha=1,setpts=PTS-STARTPTS[va{i}]"
            )
        else:
            offset_time = sum(durations[:i]) - i * transition_duration
            fade_filter = (
                f"{scale_filter},"
                f"fade=t=in:st=0:d={transition_duration}:alpha=1,"
                f"setpts=PTS-STARTPTS+{offset_time}/TB[va{i}]"
            )
        filter_parts.append(fade_filter)
        overlay_chain.append(f"va{i}")

    if len(processed_images) == 1:
        final_output = overlay_chain[0]
    else:
        current_base = overlay_chain[0]
        for i in range(1, len(overlay_chain)):
            overlay_filter = f"[{current_base}][{overlay_chain[i]}]overlay[ov{i}]"
            filter_parts.append(overlay_filter)
            current_base = f"ov{i}"
        final_output = current_base

    total_duration = sum(durations) - (len(durations) - 1) * transition_duration
    filter_parts.append(f"[{final_output}]trim=duration={total_duration}")
    filter_complex = ";".join(filter_parts)

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
        for temp_file in processed_images:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
        return output_file
    except subprocess.CalledProcessError as e:
        logging.error(f"Error creating video: {e.stderr}")
        return None


# ─── Join Only Processing ─────────────────────────────────────────────────────

def find_video_for_image(image_path, folder):
    """
    Find a matching video in folder whose stem starts with the image stem.
    Returns the video path string, or None if not found.
    """
    video_exts = ('.mp4', '.mov', '.webm')
    img_stem = pathlib.Path(image_path).stem
    candidates = [
        f for f in os.listdir(folder)
        if pathlib.Path(f).suffix.lower() in video_exts
        and pathlib.Path(f).stem.startswith(img_stem)
    ]
    if candidates:
        return os.path.join(folder, sorted(candidates)[0])
    return None


def position_suffix(position):
    """Return a short filename suffix for the image join position."""
    return {'1': 'lft', '2': 'rgt', '3': 'top', '4': 'btm'}.get(position, 'lft')


def process_join_only_groups(groups, join_position, join_audio):
    """
    Join only mode: takes group[0] from each group, finds a matching video,
    and runs join_image_video(). Gracefully skips if no video found.

    Returns:
        (success_count, skip_count, error_count, joined_folders)
    """
    success_count = 0
    skip_count = 0
    error_count = 0
    total_groups = len(groups)
    joined_folders = set()

    for idx, group in enumerate(groups, 1):
        sys.stdout.write(
            f"\r\033[93mJoining \033[0m{idx}/{total_groups} "
            f"\033[93mgroups\033[0m ({idx/total_groups*100:.1f}%)..."
        )
        sys.stdout.flush()

        first_img = pathlib.Path(group[0])
        parent_folder = str(first_img.parent)
        filename_noext = first_img.stem

        video_path = find_video_for_image(str(first_img), parent_folder)
        if not video_path:
            skip_count += 1
            logging.warning(f"No matching video for {first_img.name} — skipped")
            continue

        joined_dir = os.path.join(parent_folder, "Output", "Joined")
        os.makedirs(joined_dir, exist_ok=True)
        joined_folders.add(joined_dir)

        pos_sfx = position_suffix(join_position)
        joined_output = os.path.join(joined_dir, f"{filename_noext}_joined_{pos_sfx}.mp4")
        join_ok = djj.join_image_video(
            image_path=str(first_img),
            video_path=video_path,
            output_path=joined_output,
            position=join_position,
            audio_choice=join_audio
        )
        if join_ok:
            success_count += 1
        else:
            error_count += 1
            logging.error(f"Join failed for {first_img.name}")

    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()

    return success_count, skip_count, error_count, list(joined_folders)


# ─── Pair + Join Processing ───────────────────────────────────────────────────

def process_all_groups(groups, durations, transition_duration,
                       use_parent_output=False,
                       do_join=False, join_position='1', join_audio='1',
                       do_comp_join=False, comp_join_position='1', comp_join_audio='1',
                       collage_paths_by_stem=None):
    """
    Process all image groups into paired videos, optionally joining:
      - group[0] image + paired video → Output/Joined/
      - collaged image + paired video → Output/Comp_Joined/

    Args:
        groups:               List of image groups
        durations:            Per-image durations
        transition_duration:  Dissolve transition length
        use_parent_output:    Route output to each image's parent folder
        do_join:              Join group[0] image with paired video
        join_position:        Position for join
        join_audio:           Audio choice for join
        do_comp_join:         Join collaged image with paired video
        comp_join_position:   Position for comp join
        comp_join_audio:      Audio choice for comp join
        collage_paths_by_stem: dict mapping first-image stem → collage path,
                               used for Comp_Joined routing

    Returns:
        (success_count, error_count, paired_folders, joined_folders, comp_joined_folders)
    """
    success_count = 0
    error_count = 0
    total_groups = len(groups)
    paired_folders = set()
    joined_folders = set()
    comp_joined_folders = set()

    for idx, group in enumerate(groups, 1):
        sys.stdout.write(
            f"\r\033[93mProcessing \033[0m{idx}/{total_groups} "
            f"\033[93mgroups\033[0m ({idx/total_groups*100:.1f}%)..."
        )
        sys.stdout.flush()

        if not all(is_valid_image(img) for img in group):
            error_count += 1
            continue

        first_img = pathlib.Path(group[0])
        parent_folder = str(first_img.parent)
        filename_noext = first_img.stem

        paired_dir = os.path.join(parent_folder, "Output", "Paired")
        os.makedirs(paired_dir, exist_ok=True)
        paired_folders.add(paired_dir)

        output_file = process_image_group(group, paired_dir, durations, transition_duration, filename_noext)

        if output_file:
            success_count += 1

            # Standard join: group[0] image + paired video
            if do_join:
                joined_dir = os.path.join(parent_folder, "Output", "Joined")
                os.makedirs(joined_dir, exist_ok=True)
                joined_folders.add(joined_dir)
                joined_output = os.path.join(joined_dir, f"{filename_noext}_joined_{position_suffix(join_position)}.mp4")
                join_ok = djj.join_image_video(
                    image_path=group[0],
                    video_path=output_file,
                    output_path=joined_output,
                    position=join_position,
                    audio_choice=join_audio
                )
                if not join_ok:
                    logging.error(f"Join failed for group starting with {group[0]}")

            # Comp join: collaged image + paired video
            if do_comp_join and collage_paths_by_stem:
                collage_img = collage_paths_by_stem.get(filename_noext)
                if collage_img and os.path.exists(collage_img):
                    comp_joined_dir = os.path.join(parent_folder, "Output", "Comp_Joined")
                    os.makedirs(comp_joined_dir, exist_ok=True)
                    comp_joined_folders.add(comp_joined_dir)
                    comp_joined_output = os.path.join(comp_joined_dir, f"{filename_noext}_comp_joined_{position_suffix(comp_join_position)}.mp4")
                    cj_ok = djj.join_image_video(
                        image_path=collage_img,
                        video_path=output_file,
                        output_path=comp_joined_output,
                        position=comp_join_position,
                        audio_choice=comp_join_audio
                    )
                    if not cj_ok:
                        logging.error(f"Comp join failed for group starting with {group[0]}")
        else:
            error_count += 1

    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()

    return success_count, error_count, list(paired_folders), list(joined_folders), list(comp_joined_folders)


# ─── Group builder (shared logic) ────────────────────────────────────────────

def build_groups_for_images(images, pairing_mode, group_size, match_type=None, num_chars=None):
    """Build groups from an image list using sequential or match mode."""
    if pairing_mode == '1':
        return create_sequential_groups(images, group_size)
    else:
        matched = group_images_by_match(images, match_type, num_chars)
        groups = []
        for matched_images in matched.values():
            if len(matched_images) >= group_size:
                groups.append(matched_images[:group_size])
        return groups


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    while True:
        clear_screen()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mImage Pairing\033[0m")
        print("Combines Images into Videos")
        print("\033[92m==================================================\033[0m")
        print()

        # ── Input mode ───────────────────────────────────────────────────────
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
                ['1', '2'],
                default='2'
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
            "2. Joining only\n"
            "3. Collage only\n"
            "4. Collage + Pair\n"
            "5. Collage + Join only\n",
            ['1', '2', '3', '4', '5'],
            default='4'
        )
        print()

        # ── Grouping params (all modes need group size) ───────────────────────
        pairing_mode = djj.prompt_choice(
            "\033[93mGrouping mode:\033[0m\n"
            "1. Sequential (by position)\n"
            "2. Auto-match (by prefix/suffix)\n",
            ['1', '2'],
            default='1'
        )
        print()

        while True:
            try:
                group_size_input = input("\033[93mImages per group\033[0m [default: 3]:\n -> ").strip()
                if not group_size_input:
                    group_size = 3
                    break
                group_size = int(group_size_input)
                if group_size > 0:
                    break
                else:
                    print("\033[93mPlease enter a positive number.\033[0m")
            except ValueError:
                print("\033[93mPlease enter a valid number.\033[0m")
        print()

        match_type = None
        num_chars = None
        if pairing_mode == '2':
            match_type_choice = djj.prompt_choice(
                "\033[93mMatch by:\033[0m\n1. Prefix\n2. Suffix\n",
                ['1', '2'],
                default='1'
            )
            match_type = 'prefix' if match_type_choice == '1' else 'suffix'
            print()
            while True:
                try:
                    nc_input = input(f"\033[93mNumber of characters for {match_type} match\033[0m [default: 4]:\n -> ").strip()
                    if not nc_input:
                        num_chars = 4
                        break
                    num_chars = int(nc_input)
                    if num_chars > 0:
                        break
                    else:
                        print("\033[93mPlease enter a positive number.\033[0m")
                except ValueError:
                    print("\033[93mPlease enter a valid number.\033[0m")
            print()

        # ── Collage params (modes 3 and 4) ────────────────────────────────────
        collage_direction = None
        collage_longest_edge = None

        if top_mode in ('3', '4', '5'):
            collage_direction_choice = djj.prompt_choice(
                "\033[93mCollage direction:\033[0m\n"
                "1. Horizontal (default)\n"
                "2. Vertical\n",
                ['1', '2'],
                default='1'
            )
            collage_direction = 'H' if collage_direction_choice == '1' else 'V'
            print()

            edge_choice = djj.prompt_choice(
                "\033[93mLongest edge size:\033[0m\n"
                "1. 1920px (default)\n"
                "2. Custom\n"
                "3. 2× shorter edge of first image\n",
                ['1', '2', '3'],
                default='1'
            )
            print()

            if edge_choice == '1':
                collage_longest_edge = 1920
            elif edge_choice == '2':
                collage_longest_edge = djj.get_int_input(
                    "\033[93mEnter longest edge in pixels:\033[0m",
                    min_val=100, max_val=9999
                ) or 1920
            else:
                # 2× shorter edge of first image
                try:
                    with Image.open(images[0]) as first_img:
                        shorter = min(first_img.width, first_img.height)
                    collage_longest_edge = shorter * 2
                    print(f"\033[93mUsing {collage_longest_edge}px (2× {shorter}px shorter edge)\033[0m")
                except Exception:
                    collage_longest_edge = 1920
                    print("\033[93m⚠️  Could not read first image dimensions, defaulting to 1920px\033[0m")
            print()

            # Comp join prompt (mode 4 only) — ask before pairing params
            do_comp_join = False
            comp_join_position = '1'
            comp_join_audio = '1'
            if top_mode in ('4', '5'):
                do_comp_join = djj.prompt_choice(
                    "\033[93mAlso join collaged image with paired video?\033[0m\n1. Yes\n2. No\n",
                    ['1', '2'],
                    default='1'
                ) == '1'
                print()

                if do_comp_join:
                    opposite_dir = 'V' if collage_direction == 'H' else 'H'
                    opposite_label = 'Vertical' if collage_direction == 'H' else 'Horizontal'
                    use_opposite = djj.prompt_choice(
                        f"\033[93mUse opposite direction ({opposite_label}) for Comp Join collage?\033[0m\n1. Yes\n2. No (same as main)\n",
                        ['1', '2'],
                        default='1'
                    ) == '1'
                    print()

                    # Flip direction if yes, same size either way
                    # temp collages used for Comp_Joined then discarded silently
                    comp_collage_direction = opposite_dir if use_opposite else collage_direction
                    comp_collage_longest_edge = collage_longest_edge
                    same_collage_params = not use_opposite

                    print("\033[93m🖼️  Comp Join — Image Position:\033[0m")
                    print("1. Left   (video on right)")
                    print("2. Right  (video on left)")
                    print("3. Top    (video on bottom)")
                    print("4. Bottom (video on top)")
                    comp_join_position = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3', '4'], default='1')
                    print()

                    print("\033[93m🔊 Comp Join — Audio:\033[0m")
                    print("1. Keep video's audio")
                    print("2. Strip audio")
                    print("3. Add silent audio track")
                    comp_join_audio = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3'], default='2')
                    print()

        # ── Pairing params (modes 1 and 4) ────────────────────────────────────
        durations = []
        transition_duration = 1.0

        if top_mode in ('1', '4'):
            for i in range(group_size):
                while True:
                    try:
                        dur_input = input(f"\033[93mDuration for image {i+1} (seconds)\033[0m [default: 5]:\n -> ").strip()
                        if not dur_input:
                            duration = 5.0
                            break
                        duration = float(dur_input)
                        if duration > 0:
                            break
                        else:
                            print("\033[93mPlease enter a positive number.\033[0m")
                    except ValueError:
                        print("\033[93mPlease enter a valid number.\033[0m")
                durations.append(duration)
                print()

            while True:
                try:
                    trans_input = input("\033[93mTransition duration (seconds)\033[0m [default: 2]:\n -> ").strip()
                    if not trans_input:
                        transition_duration = 2.0
                        break
                    transition_duration = float(trans_input)
                    if transition_duration >= 0:
                        break
                    else:
                        print("\033[93mPlease enter a non-negative number.\033[0m")
                except ValueError:
                    print("\033[93mPlease enter a valid number.\033[0m")
            print()

            total_duration = sum(durations) - (len(durations) - 1) * transition_duration
            print(f"\033[93mTotal video duration:\033[0m {total_duration:.1f}s")
            print()

        # ── Join params (modes 1 and 4) ───────────────────────────────────────
        do_join = False
        join_position = '1'
        join_audio = '1'

        if top_mode in ('1', '4'):
            do_join = djj.prompt_choice(
                "\033[93mJoin first image with paired video?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'],
                default='1'
            ) == '1'
            print()

            if do_join:
                print("\033[93m🖼️  Image Position:\033[0m")
                print("1. Left   (video on right)")
                print("2. Right  (video on left)")
                print("3. Top    (video on bottom)")
                print("4. Bottom (video on top)")
                join_position = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3', '4'], default='1')
                print()

                print("\033[93m🔊 Audio:\033[0m")
                print("1. Keep video's audio")
                print("2. Strip audio")
                print("3. Add silent audio track")
                join_audio = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3'], default='2')
                print()

        # ── Join Only params (mode 2) ──────────────────────────────────────────
        join_only_position = '1'
        join_only_audio = '1'

        if top_mode in ('2', '5'):
            print("\033[93m🖼️  Image Position:\033[0m")
            print("1. Left   (video on right)")
            print("2. Right  (video on left)")
            print("3. Top    (video on bottom)")
            print("4. Bottom (video on top)")
            join_only_position = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3', '4'], default='1')
            print()

            print("\033[93m🔊 Audio:\033[0m")
            print("1. Keep video's audio")
            print("2. Strip audio")
            print("3. Add silent audio track")
            join_only_audio = djj.prompt_choice("\033[93mChoice\033[0m", ['1', '2', '3'], default='1')
            print()

        # ── Setup logging ─────────────────────────────────────────────────────
        if input_mode == '1':
            log_base = input_path
        else:
            log_base = str(pathlib.Path(images[0]).parent)
        log_output = os.path.join(log_base, "Output", "Paired")
        os.makedirs(log_output, exist_ok=True)
        setup_logging(log_output)

        # ── Build groups ──────────────────────────────────────────────────────
        process_by_folder = (include_subfolders and input_mode == '1') or (input_mode in ['2', '3'])

        if process_by_folder:
            folder_image_map = group_images_by_parent_folder(images)
        else:
            folder_image_map = {input_path: images}

        print(f"\033[93mProcessing {len(folder_image_map)} folder(s)...\033[0m")
        print()

        # ── Tracking totals ───────────────────────────────────────────────────
        total_success = 0
        total_error = 0
        total_skip = 0
        all_paired_folders = []
        all_joined_folders = []
        all_comp_joined_folders = []
        all_collage_folders = []
        _last_collage_out = []   # Mode 3: holds latest collage outputs for re-collage
        _collage_gen = 1         # Mode 3: suffix generation counter (1=_comp, 2=_comp2…)

        # ── Process each folder ───────────────────────────────────────────────
        for folder_path, folder_images in folder_image_map.items():

            groups = build_groups_for_images(folder_images, pairing_mode, group_size, match_type, num_chars)

            if not groups:
                print(f"\033[93m⚠️  No complete groups in {folder_path}, skipping.\033[0m")
                continue

            # ── Mode 1: Pairing only ──────────────────────────────────────────
            if top_mode == '1':
                s, e, pf, jf, cjf = process_all_groups(
                    groups, durations, transition_duration,
                    use_parent_output=True,
                    do_join=do_join, join_position=join_position, join_audio=join_audio
                )
                total_success += s
                total_error += e
                all_paired_folders.extend(pf)
                all_joined_folders.extend(jf)

            # ── Mode 2: Joining only ──────────────────────────────────────────
            elif top_mode == '2':
                s, sk, e, jf = process_join_only_groups(groups, join_only_position, join_only_audio)
                total_success += s
                total_skip += sk
                total_error += e
                all_joined_folders.extend(jf)

            # ── Mode 3: Collage only ──────────────────────────────────────────
            elif top_mode == '3':
                comp_dir = os.path.join(folder_path, "Output", "Comp")
                flat_images = [img for group in groups for img in group]
                collage_out = djj.create_collage(
                    flat_images, collage_direction, collage_longest_edge, comp_dir, group_size
                )
                total_success += len(collage_out)
                all_collage_folders.append(comp_dir)
                # Store latest collage outputs for potential re-collage
                _last_collage_out = list(collage_out)
                _collage_gen = 1  # tracks suffix number: gen 1 = _comp, gen 2 = _comp2 ...

            # ── Mode 4: Collage + Pair ────────────────────────────────────────
            elif top_mode == '4':
                import tempfile
                import shutil as _shutil

                # Step 1: Main collage → Output/Comp/ (always saved)
                comp_dir = os.path.join(folder_path, "Output", "Comp")
                flat_images = [img for group in groups for img in group]
                collage_out = djj.create_collage(
                    flat_images, collage_direction, collage_longest_edge, comp_dir, group_size
                )
                all_collage_folders.append(comp_dir)

                # Step 1b: If comp join uses different params, run a second collage
                # into a temp dir — used only for Comp_Joined then discarded silently
                temp_comp_dir = None
                if do_comp_join and not same_collage_params:
                    temp_comp_dir = tempfile.mkdtemp(prefix="djjtb_comp_join_")
                    alt_collage_out = djj.create_collage(
                        flat_images, comp_collage_direction, comp_collage_longest_edge,
                        temp_comp_dir, group_size
                    )
                    collage_paths_by_stem = {}
                    for grp, cpath in zip(groups, alt_collage_out):
                        stem = pathlib.Path(grp[0]).stem
                        collage_paths_by_stem[stem] = cpath
                else:
                    collage_paths_by_stem = {}
                    for grp, cpath in zip(groups, collage_out):
                        stem = pathlib.Path(grp[0]).stem
                        collage_paths_by_stem[stem] = cpath

                # Step 2: Pair original images, with optional joins
                s, e, pf, jf, cjf = process_all_groups(
                    groups, durations, transition_duration,
                    use_parent_output=True,
                    do_join=do_join, join_position=join_position, join_audio=join_audio,
                    do_comp_join=do_comp_join, comp_join_position=comp_join_position,
                    comp_join_audio=comp_join_audio,
                    collage_paths_by_stem=collage_paths_by_stem
                )

                # Discard temp collages if alternate params were used
                if temp_comp_dir and os.path.exists(temp_comp_dir):
                    _shutil.rmtree(temp_comp_dir, ignore_errors=True)
                total_success += s
                total_error += e
                all_paired_folders.extend(pf)
                all_joined_folders.extend(jf)
                all_comp_joined_folders.extend(cjf)

            # ── Mode 5: Collage + Join only ───────────────────────────────────
            elif top_mode == '5':
                import tempfile
                import shutil as _shutil

                # Step 1: Main collage → Output/Comp/ (always saved)
                comp_dir = os.path.join(folder_path, "Output", "Comp")
                flat_images = [img for group in groups for img in group]
                collage_out = djj.create_collage(
                    flat_images, collage_direction, collage_longest_edge, comp_dir, group_size
                )
                all_collage_folders.append(comp_dir)

                # Step 1b: Alternate direction collage for comp join if requested
                temp_comp_dir = None
                if do_comp_join and not same_collage_params:
                    temp_comp_dir = tempfile.mkdtemp(prefix="djjtb_comp_join_")
                    alt_collage_out = djj.create_collage(
                        flat_images, comp_collage_direction, comp_collage_longest_edge,
                        temp_comp_dir, group_size
                    )
                    collage_paths_by_stem = {}
                    for grp, cpath in zip(groups, alt_collage_out):
                        stem = pathlib.Path(grp[0]).stem
                        collage_paths_by_stem[stem] = cpath
                else:
                    collage_paths_by_stem = {}
                    for grp, cpath in zip(groups, collage_out):
                        stem = pathlib.Path(grp[0]).stem
                        collage_paths_by_stem[stem] = cpath

                # Step 2: Join each collaged image with its matching video
                pos_sfx = position_suffix(join_only_position)
                cj_success = 0
                cj_skip = 0
                cj_error = 0
                for grp, cpath in zip(groups, collage_out):
                    stem = pathlib.Path(grp[0]).stem
                    collage_img = collage_paths_by_stem.get(stem, cpath)
                    first_img = pathlib.Path(grp[0])
                    parent_folder = str(first_img.parent)

                    video_path = find_video_for_image(str(first_img), parent_folder)
                    if not video_path:
                        cj_skip += 1
                        logging.warning(f"No matching video for {first_img.name} — skipped")
                        continue

                    comp_joined_dir = os.path.join(parent_folder, "Output", "Comp_Joined")
                    os.makedirs(comp_joined_dir, exist_ok=True)
                    all_comp_joined_folders.append(comp_joined_dir)

                    out_path = os.path.join(comp_joined_dir, f"{stem}_comp_joined_{pos_sfx}.mp4")
                    ok = djj.join_image_video(
                        image_path=collage_img,
                        video_path=video_path,
                        output_path=out_path,
                        position=join_only_position,
                        audio_choice=join_only_audio
                    )
                    if ok:
                        cj_success += 1
                    else:
                        cj_error += 1
                        logging.error(f"Comp join failed for {first_img.name}")

                if temp_comp_dir and os.path.exists(temp_comp_dir):
                    _shutil.rmtree(temp_comp_dir, ignore_errors=True)

                total_success += cj_success
                total_skip += cj_skip
                total_error += cj_error

        # ── Mode 3: Re-collage loop ───────────────────────────────────────────
        # After Collage Only, offer to re-collage the outputs.
        # On Yes: re-ask grouping + collage questions fresh, feed previous
        # outputs in as the new image list, increment the suffix so names
        # go _comp → _comp2 → _comp3 … never _comp_comp_comp.
        while top_mode == '3' and _last_collage_out:
            recap = djj.prompt_choice(
                "\033[93mRe-collage these results?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'],
                default='2'
            )
            print()
            if recap != '1':
                break

            # ── Re-ask grouping params ────────────────────────────────────────
            rc_pairing_mode = djj.prompt_choice(
                "\033[93mGrouping mode:\033[0m\n"
                "1. Sequential (by position)\n"
                "2. Auto-match (by prefix/suffix)\n",
                ['1', '2'],
                default='1'
            )
            print()

            while True:
                try:
                    rc_gs_input = input("\033[93mImages per group\033[0m [default: 3]:\n -> ").strip()
                    if not rc_gs_input:
                        rc_group_size = 3
                        break
                    rc_group_size = int(rc_gs_input)
                    if rc_group_size > 0:
                        break
                    else:
                        print("\033[93mPlease enter a positive number.\033[0m")
                except ValueError:
                    print("\033[93mPlease enter a valid number.\033[0m")
            print()

            rc_match_type = None
            rc_num_chars = None
            if rc_pairing_mode == '2':
                rc_mt_choice = djj.prompt_choice(
                    "\033[93mMatch by:\033[0m\n1. Prefix\n2. Suffix\n",
                    ['1', '2'], default='1'
                )
                rc_match_type = 'prefix' if rc_mt_choice == '1' else 'suffix'
                print()
                while True:
                    try:
                        rc_nc = input(f"\033[93mNumber of characters for {rc_match_type} match\033[0m [default: 4]:\n -> ").strip()
                        if not rc_nc:
                            rc_num_chars = 4
                            break
                        rc_num_chars = int(rc_nc)
                        if rc_num_chars > 0:
                            break
                        else:
                            print("\033[93mPlease enter a positive number.\033[0m")
                    except ValueError:
                        print("\033[93mPlease enter a valid number.\033[0m")
                print()

            # ── Re-ask collage direction ──────────────────────────────────────
            rc_dir_choice = djj.prompt_choice(
                "\033[93mCollage direction:\033[0m\n"
                "1. Horizontal (default)\n"
                "2. Vertical\n",
                ['1', '2'], default='1'
            )
            rc_direction = 'H' if rc_dir_choice == '1' else 'V'
            print()

            # ── Re-ask longest edge ───────────────────────────────────────────
            rc_edge_choice = djj.prompt_choice(
                "\033[93mLongest edge size:\033[0m\n"
                "1. 1920px (default)\n"
                "2. Custom\n"
                "3. 2× shorter edge of first image\n",
                ['1', '2', '3'], default='1'
            )
            print()
            if rc_edge_choice == '1':
                rc_longest_edge = 1920
            elif rc_edge_choice == '2':
                rc_longest_edge = djj.get_int_input(
                    "\033[93mEnter longest edge in pixels:\033[0m",
                    min_val=100, max_val=9999
                ) or 1920
            else:
                try:
                    with Image.open(_last_collage_out[0]) as _rc_img:
                        _shorter = min(_rc_img.width, _rc_img.height)
                    rc_longest_edge = _shorter * 2
                    print(f"\033[93mUsing {rc_longest_edge}px (2× {_shorter}px shorter edge)\033[0m")
                except Exception:
                    rc_longest_edge = 1920
                    print("\033[93m⚠️  Could not read image dimensions, defaulting to 1920px\033[0m")
            print()

            # ── Build groups and run collage ──────────────────────────────────
            # Each round gets its own Comp/ subfolder nested one level deeper.
            # Suffix is always _comp — the folder depth is the generation indicator.
            # create_collage strips any trailing _comp/_compN from the stem so
            # names never chain regardless of how many rounds deep you go.
            _collage_gen += 1
            next_suffix = '_comp'
            recap_dir = os.path.join(all_collage_folders[-1], 'Comp')
            os.makedirs(recap_dir, exist_ok=True)
            all_collage_folders.append(recap_dir)

            rc_groups = build_groups_for_images(
                _last_collage_out, rc_pairing_mode, rc_group_size,
                rc_match_type, rc_num_chars
            )
            if not rc_groups:
                rc_groups = [_last_collage_out]  # fewer files than group_size — one group

            rc_flat = [img for g in rc_groups for img in g]
            new_collage_out = djj.create_collage(
                rc_flat, rc_direction, rc_longest_edge,
                recap_dir, rc_group_size, suffix=next_suffix
            )
            if new_collage_out:
                total_success += len(new_collage_out)
                _last_collage_out = list(new_collage_out)
                print(f"\033[92m✅ {len(new_collage_out)} re-collage(s) created → {next_suffix}\033[0m")
            else:
                print("\033[93m⚠️  Re-collage produced no output.\033[0m")
                break

        # ── Summary ───────────────────────────────────────────────────────────
        print()
        print("\033[93mSummary\033[0m")
        print("-------")

        if top_mode in ('2', '5'):
            print(f"✅ \033[93mJoined:\033[0m {total_success}")
            if total_skip:
                print(f"\033[93m⚠️  Skipped (no video found):\033[0m {total_skip}")
            if total_error:
                print(f"❌ \033[93mFailed:\033[0m {total_error}")
        elif top_mode == '3':
            print(f"✅ \033[93mCollages created:\033[0m {total_success}")
        else:
            print(f"✅ \033[93mGroups processed:\033[0m {total_success}")
            if total_error:
                print(f"❌ \033[93mFailed:\033[0m {total_error} (see pairing_errors.log)")

        def print_folders(label, folders):
            if not folders:
                return
            unique = sorted(set(folders))
            print(f"\n\033[93m{label}:\033[0m")
            for f in unique[:3]:
                print(f"  - {f}")
            if len(unique) > 3:
                print(f"  ... and {len(unique) - 3} more")

        print_folders("📁 Collage output", all_collage_folders)
        print_folders("📁 Paired output", all_paired_folders)
        print_folders("🔗 Joined output", all_joined_folders)
        print_folders("🔗 Comp Joined output", all_comp_joined_folders)
        print()

        # Open the most relevant output folder
        open_folder = (
            all_comp_joined_folders[0] if all_comp_joined_folders else
            all_joined_folders[0] if all_joined_folders else
            all_collage_folders[0] if all_collage_folders else
            all_paired_folders[0] if all_paired_folders else
            None
        )
        if open_folder:
            djj.prompt_open_folder(open_folder)

        action = djj.what_next()
        if action == 'exit':
            break

    clear_screen()