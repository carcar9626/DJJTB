import os
import random
import subprocess
import sys
import pathlib
import djjtb.utils as djj
from PIL import Image, ImageFilter
from datetime import datetime
os.system('clear')
# Increase Pillow's decompression bomb limit
Image.MAX_IMAGE_PIXELS = 200000000  # Set to 200 million pixels

# --- Shared Functions ---
def collect_images_from_txt():
    """Collect images from txt file (files and folders)."""
    paths = djj.get_paths_from_txt("Enter txt file path")

    if not paths:
        return []

    images = []
    for path in paths:
        path_obj = pathlib.Path(path)
        if path_obj.is_file():
            if path_obj.suffix.lower() in djj.IMAGE_EXTENSIONS:
                images.append(str(path))
        elif path_obj.is_dir():
            images.extend(djj.collect_images_from_folder(str(path), include_subfolders=False))

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

def get_first_image_dimensions(images):
    """Get dimensions of the first valid image in the list."""
    for img_path in images:
        try:
            with Image.open(img_path) as img:
                return img.width, img.height
        except Exception:
            continue
    return None

# --- Slideshow Functions ---
def prepare_slides(images, folder_path, orientation, duration_per_slide, use_transitions=False, background_type='blurred', background_color=(0, 0, 0), background_opacity=0.25, background_blur_radius=8, custom_dims=None):
    """Prepare images for slideshow by adding backgrounds and create a video."""
    # Determine dimensions based on orientation
    if orientation == 'landscape':
        canvas_width, canvas_height = 1920, 1080
    elif orientation == 'portrait':
        canvas_width, canvas_height = 1080, 1920
    elif orientation == 'square':
        canvas_width, canvas_height = 1440, 1440
    elif orientation == 'first_image':
        dims = get_first_image_dimensions(images)
        if dims:
            canvas_width, canvas_height = dims
        else:
            print("\033[93mCouldn't read first image dimensions, falling back to 1920x1080\033[0m")
            canvas_width, canvas_height = 1920, 1080
    elif orientation == 'custom' and custom_dims:
        canvas_width, canvas_height = custom_dims
    else:
        canvas_width, canvas_height = 1080, 1920  # default portrait
    
    # Ensure output directory exists at folder_path/Output/Slideshow
    folder_path_resolved = str(pathlib.Path(folder_path).resolve())
    output_dir = os.path.join(folder_path_resolved, "Output", "Slideshow")
    os.makedirs(output_dir, exist_ok=True)

    # Set up logging
    logger = djj.setup_logging(output_dir, "image_slideshow_maker")

    if not images:
        print("\033[93mNo images found.\033[0m", file=sys.stderr)
        return None, 0
    
    print()
    print("\033[93mScanning for images...\033[0m")
    print(f"{len(images)} \033[93mimages found\033[0m")
    print()
    
    # Calculate total duration
    if use_transitions:
        transition_duration = 1.0  # 1 second dissolve
        total_duration = len(images) * duration_per_slide - (len(images) - 1) * transition_duration
    else:
        total_duration = len(images) * duration_per_slide
        
    if total_duration > 900:  # 15 minutes in seconds
        print(f"\n\033[93mWarning: The resulting video will be \033[0m{total_duration // 60} \033[93mminutes and\033[0m {total_duration % 60} \033[93mseconds long, exceeding 15 minutes.\033[0m")
        choice = input("\033[93mDo you want to continue? \033[0m\ny for Yes, any other key for No: ").strip().lower()
        if choice != 'y':
            print("\033[93mOperation cancelled.\033[0m")
            return None, 0
    
    # Create unique output filename
    folder_name = os.path.basename(folder_path_resolved)
    base_output_file = os.path.join(output_dir, f"{folder_name}_slideshow.mp4")
    output_file = base_output_file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    counter = 1
    while os.path.exists(output_file):
        output_file = f"{os.path.splitext(base_output_file)[0]}_{timestamp}_{counter}.mp4"
        counter += 1
    
    if use_transitions:
        # Use EXACT pairing script logic - process all images with proper duration math
        print("\033[93mCreating slideshow with transitions...\033[0m")
        print("-------------")
        
        transition_duration = 1.0
        # Preprocess each image to apply background (blur or solid)
        print("\033[93mPreprocessing images with background...\033[0m")
        temp_dir = os.path.join(output_dir, "temp_slides_transitions")
        os.makedirs(temp_dir, exist_ok=True)

        processed_images = []
        for i, img_path in enumerate(images, 1):
            try:
                canvas = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
                img = Image.open(img_path)
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')

                if background_type == 'blurred':
                    bg_img = img.copy()
                    bg_img = bg_img.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=background_blur_radius))
                    alpha = Image.new('L', bg_img.size, int(255 * background_opacity))
                    bg_img.putalpha(alpha)
                    canvas.paste(bg_img, (0, 0), bg_img)
                else:
                    color_bg = Image.new('RGBA', (canvas_width, canvas_height), (*background_color, int(255 * background_opacity)))
                    canvas.paste(color_bg, (0, 0), color_bg)

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

                output_filename = os.path.join(temp_dir, f"frame_{i:04d}.png")
                canvas.save(output_filename, 'PNG')
                processed_images.append(output_filename)
                sys.stdout.write(f"\r\033[93mProcessed \033[0m{i}/{len(images)}")
                sys.stdout.flush()
            except Exception as e:
                logger.error(f"Transition-mode preprocessing failed on {os.path.basename(img_path)}: {e}")
                continue
        
        print()
        images = processed_images
        
        # Build ffmpeg command exactly like pairing script but for multiple images
        cmd = ["ffmpeg", "-y"]
        
        # Add all images as inputs with proper duration
        for img_path in images:  # these are now the processed ones
            cmd.extend(["-loop", "1", "-t", str(duration_per_slide), "-i", img_path])
        
        # Build filter complex with proper overlap timing (from pairing script)
        filter_parts = []
        overlay_chain = []
        
        for i in range(len(images)):
            # Scale and format each input
            scale_filter = f"[{i}:v]scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=decrease,pad={canvas_width}:{canvas_height}:(ow-iw)/2:(oh-ih)/2,format=yuva420p"
            
            if i == 0:
                # First image: fade out at the end, no offset
                fade_filter = f"{scale_filter},fade=t=out:st={duration_per_slide-transition_duration}:d={transition_duration}:alpha=1,setpts=PTS-STARTPTS[va{i}]"
                filter_parts.append(fade_filter)
                overlay_chain.append(f"va{i}")
            else:
                # Subsequent images: fade in, offset by (duration - transition) for each previous image
                offset_time = i * (duration_per_slide - transition_duration)
                fade_filter = f"{scale_filter},fade=t=in:st=0:d={transition_duration}:alpha=1,setpts=PTS-STARTPTS+{offset_time}/TB[va{i}]"
                filter_parts.append(fade_filter)
                overlay_chain.append(f"va{i}")
        
        # Chain overlays exactly like pairing script
        if len(images) == 1:
            final_output = overlay_chain[0]
        else:
            current_base = overlay_chain[0]
            for i in range(1, len(overlay_chain)):
                if i == 1:
                    overlay_filter = f"[{current_base}][{overlay_chain[i]}]overlay[ov{i}]"
                    current_base = f"ov{i}"
                else:
                    overlay_filter = f"[{current_base}][{overlay_chain[i]}]overlay[ov{i}]"
                    current_base = f"ov{i}"
                filter_parts.append(overlay_filter)
            final_output = current_base
        
        # Add final trim with exact duration calculation (from pairing script logic)
        final_duration = len(images) * duration_per_slide - (len(images) - 1) * transition_duration
        filter_parts.append(f"[{final_output}]trim=duration={final_duration}")
        
        filter_complex = ";".join(filter_parts)
        
        cmd.extend([
            "-filter_complex", filter_complex,
            "-c:v", "h264_videotoolbox",
            "-b:v", "8M",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-t", str(final_duration),
            "-fps_mode", "cfr",
            output_file
        ])
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for temp_file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, temp_file))
            os.rmdir(temp_dir)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating slideshow with transitions: {e.stderr}")
            print("\033[93mError creating slideshow. Check image_slideshow_maker_log.txt for details.\033[0m", file=sys.stderr)
            return None, len(images)
        # Clean up temporary processed images
        return output_file, len(images)
        
    else:
        # Original method without transitions - prepare processed images first
        temp_dir = os.path.join(output_dir, "temp_slides")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Process each image
        successful = 0
        for i, img_path in enumerate(images, 1):
            try:
                # Create transparent canvas
                canvas = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
                
                # Load image
                img = Image.open(img_path)
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Create background based on type
                if background_type == 'blurred':
                    # Create blurred background from the image itself
                    bg_img = img.copy()
                    bg_img = bg_img.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=background_blur_radius))
                    alpha = Image.new('L', bg_img.size, int(255 * background_opacity))
                    bg_img.putalpha(alpha)
                    canvas.paste(bg_img, (0, 0), bg_img)
                else:
                    # Create solid color background
                    color_bg = Image.new('RGBA', (canvas_width, canvas_height), (*background_color, int(255 * background_opacity)))
                    canvas.paste(color_bg, (0, 0), color_bg)
                
                # Calculate scaling for foreground to fit canvas
                img_ratio = img.width / img.height
                target_width = canvas_width
                target_height = int(target_width / img_ratio)
                
                # If target_height exceeds canvas_height, scale to height
                if target_height > canvas_height:
                    target_height = canvas_height
                    target_width = int(target_height * img_ratio)
                
                # Resize foreground image
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                
                # Center foreground on canvas
                paste_x = (canvas_width - target_width) // 2
                paste_y = (canvas_height - target_height) // 2
                canvas.paste(img, (paste_x, paste_y), img)
                
                # Save processed image
                output_filename = os.path.join(temp_dir, f"slide_{i:04d}.png")
                canvas.save(output_filename, 'PNG')
                successful += 1
                sys.stdout.write(f"\r\033[93mPreparing slides \033[0m{i}/{len(images)}...")
                sys.stdout.flush()
            except Exception as e:
                logger.error(f"Error processing {os.path.basename(img_path)}: {e}")
                sys.stdout.write(f"\r\033[93mPreparing slide \033[0m{i}/{len(images)}... \033[93m(failed)\033[0m")
                sys.stdout.flush()
                continue
        
        print()
        print("\n\033[93mCreating Slideshow...\033[0m")
        print("-------------")
        # Clear processing line
        sys.stdout.write("\r" + " " * 50 + "\r")
        sys.stdout.flush()
        
        if successful == 0:
            print("\033[93mNo images were processed successfully.\033[0m", file=sys.stderr)
            return None, 0
        
        # Create video using ffmpeg - FIXED TIMING
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-framerate', f'1/{duration_per_slide}',
            '-i', os.path.join(temp_dir, 'slide_%04d.png'),
            '-c:v', 'h264_videotoolbox',
            '-b:v', '8M',
            '-pix_fmt', 'yuv420p',
            output_file
        ]
        
        try:
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating video: {e.stderr}")
            print("\033[93mError creating video. Check image_slideshow_maker_log.txt for details.\033[0m", file=sys.stderr)
            return None, successful
        
        # Clean up temporary files
        for temp_file in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, temp_file))
        os.rmdir(temp_dir)
        
        return output_file, successful

# --- Main Execution ---
if __name__ == '__main__':
    while True:
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mSlideshow Maker\033[0m")
        print("Creates Slideshow with Images")
        print("\033[92m==================================================\033[0m")
        print()
        
        # Input mode selection
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
        folder_path = None
        per_folder_mode = False

        if input_mode == '1':
            # Folder mode
            folder_path = djj.get_path_input("\033[93mEnter folder path\033[0m")
            print()
            
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            
            images = djj.collect_images_from_folder(folder_path, include_sub)

        elif input_mode == '2':
            # File paths mode
            file_paths = input("📁 \033[93mEnter image paths (space-separated):\033[0m\n -> ").strip()

            if not file_paths:
                print("❌ \033[1;5;93mNo file paths provided.\033[0m")
                continue

            images = djj.collect_images_from_paths(file_paths)
            # Set folder_path to parent of first image for output folder logic
            if images:
                folder_path = str(pathlib.Path(images[0]).parent)
            print()
            
            # Ask about per-folder mode
            per_folder_choice = djj.prompt_choice(
                "\033[93mCreate separate slideshows per parent folder?\033[0m\n1. Yes\n2. No (combine all)\n",
                ['1', '2'],
                default='2'
            )
            per_folder_mode = (per_folder_choice == '1')
            print()
        
        else:  # input_mode == '3'
            # Txt file mode
            images = collect_images_from_txt()
            
            if not images:
                print("❌ \033[93mNo valid images found.\033[0m")
                continue
            
            # Set folder_path to parent of first image for output folder logic
            if images:
                folder_path = str(pathlib.Path(images[0]).parent)
            print()
            
            # Ask about per-folder mode
            per_folder_choice = djj.prompt_choice(
                "\033[93mCreate separate slideshows per parent folder?\033[0m\n1. Yes\n2. No (combine all)\n",
                ['1', '2'],
                default='2'
            )
            per_folder_mode = (per_folder_choice == '1')
            print()

        if not images:
            print("\033[1;5;93m❌ No valid image files found. Try again.\033[0m\n")
            continue

        print("Scanning for images...")
        print(f"✅ {len(images)} \033[93mimages found\033[0m")
        print()

        # Shuffle option
        shuffle_images = djj.prompt_choice(
            "\033[93mShuffle images order?\033[0m\n1. Yes\n2. No\n",
            ['1', '2'],
            default='1'
        ) == '1'
        print()

        if shuffle_images:
            random.shuffle(images)

        # Prompt for orientation with new options
        orientation_choice = djj.prompt_choice(
            "\033[93mSlideshow Orientation:\033[0m\n"
            "1. Landscape (1920x1080)\n"
            "2. Portrait (1080x1920)\n"
            "3. Square (1440x1440)\n"
            "4. First image dimensions\n"
            "5. Custom (width x height)\n",
            ['1', '2', '3', '4', '5'],
            default='4'
        )

        orientation_map = {
            '1': 'landscape',
            '2': 'portrait',
            '3': 'square',
            '4': 'first_image',
            '5': 'custom'
        }
        orientation = orientation_map[orientation_choice]
        print()

        custom_dims = None
        if orientation == 'custom':
            custom_width = djj.get_int_input("\033[93mCustom width in pixels\033[0m", min_val=1)
            print()
            custom_height = djj.get_int_input("\033[93mCustom height in pixels\033[0m", min_val=1)
            print()
            custom_dims = (custom_width, custom_height)

        # Transition option
        use_transitions = djj.prompt_choice(
            "\033[93mAdd dissolve transitions?\033[0m\n1. Yes\n2. No\n",
            ['1', '2'],
            default='1'
        ) == '1'
        print()
        
        # Background options (always allow configuration)
        background_type = 'blurred'
        background_color = (0, 0, 0)
        background_opacity = 0.8
        background_blur_radius = 8
        
        # Background type selection
        background_choice = djj.prompt_choice(
            "\033[93mBackground type:\033[0m\n1. Blurred (from image)\n2. Solid color\n",
            ['1', '2'],
            default='1'
        )
        print()
        
        if background_choice == '1':
            # Blurred background options
            background_opacity = djj.get_float_input(
                "Background opacity [0.0-1.0, default: 0.8]", min_val=0.0, max_val=1.0, default=0.8
            )
            print()

            background_blur_radius = djj.get_int_input(
                "Background blur radius [1-50, default: 8]", min_val=1, max_val=50, default=8
            )
            print()
        else:
            # Solid color background
            background_type = 'solid'
            color_input = input("Background color [R,G,B like 0,0,0 for black, default: 0,0,0]:\n -> ").strip()
            try:
                if color_input:
                    r, g, b = map(int, color_input.split(','))
                    background_color = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
                else:
                    background_color = (0, 0, 0)
            except ValueError:
                background_color = (0, 0, 0)
                print("Using default color: black (0,0,0)")
            print()

            background_opacity = djj.get_float_input(
                "Background opacity [0.0-1.0, default: 1.0]", min_val=0.0, max_val=1.0, default=1.0
            )
            print()

        # Prompt for duration per slide
        duration_per_slide = djj.get_int_input(
            "Slide duration in seconds [default: 5]", min_val=1, default=5
        )
        print()
        print("\033[1;93mProcessing...\033[0m")
        
        # Handle per-folder mode or single slideshow
        if per_folder_mode:
            # Group images by parent folder
            grouped_images = group_images_by_parent_folder(images)
            print(f"\n\033[93mFound {len(grouped_images)} parent folders\033[0m")
            print()
            
            all_outputs = []
            total_successful = 0
            
            for idx, (parent_folder, folder_images) in enumerate(grouped_images.items(), 1):
                print(f"\033[93m[{idx}/{len(grouped_images)}] Processing: {os.path.basename(parent_folder)}\033[0m")
                print(f"  {len(folder_images)} images")
                
                # Create slideshow for this folder
                output_file, successful = prepare_slides(
                    images=folder_images,
                    folder_path=parent_folder,
                    orientation=orientation,
                    duration_per_slide=duration_per_slide,
                    use_transitions=use_transitions,
                    background_type=background_type,
                    background_color=background_color,
                    background_opacity=background_opacity,
                    background_blur_radius=background_blur_radius,
                    custom_dims=custom_dims
                )
                
                if output_file:
                    all_outputs.append(output_file)
                    total_successful += successful
                
                print()
            
            # Display aggregate results
            print("\033[93m=== Overall Summary ===\033[0m")
            print(f"Slideshows created: {len(all_outputs)}")
            print(f"Total images processed: {total_successful}")
            
            # Open first output folder
            if all_outputs:
                djj.prompt_open_folder(os.path.dirname(all_outputs[0]))
        
        else:
            # Single slideshow mode
            output_file, successful = prepare_slides(
                images=images,
                folder_path=folder_path,
                orientation=orientation,
                duration_per_slide=duration_per_slide,
                use_transitions=use_transitions,
                background_type=background_type,
                background_color=background_color,
                background_opacity=background_opacity,
                background_blur_radius=background_blur_radius,
                custom_dims=custom_dims
            )
            
            # Display results
            print()
            print("\033[93mSlideshow Creation Summary\033[0m")
            print("-------------")
            print(f"Successfully processed: {successful} images")
            if output_file:
                print(f"Output video: {output_file}")
                print(f"Output folder: {os.path.dirname(output_file)}")
            else:
                print("Failed to create video. Check image_slideshow_maker_log.txt for details.")
            print()
            
            # Open output folder
            if output_file:
                djj.prompt_open_folder(os.path.dirname(output_file))
        
        # Prompt to go again
        action = djj.what_next()
        if action == 'exit':
            break

    os.system('clear')