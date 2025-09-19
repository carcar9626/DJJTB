import os
import subprocess
import sys
import pathlib
import logging
import djjtb.utils as djj
from PIL import Image, ImageFilter
from datetime import datetime
os.system('clear')
# Increase Pillow's decompression bomb limit
Image.MAX_IMAGE_PIXELS = 200000000  # Set to 200 million pixels

# --- Shared Functions ---
def setup_logging(output_path):
    """Set up logging to a file in the output folder."""
    log_file = os.path.join(output_path, "slideshow_errors.log")
    logging.basicConfig(
        filename=log_file,
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

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

# --- Slideshow Functions ---
def prepare_slides(images, folder_path, orientation, duration_per_slide, use_transitions=False, background_type='blurred', background_color=(0, 0, 0), background_opacity=0.25, background_blur_radius=8):
    """Prepare images for slideshow by adding backgrounds and create a video."""
    # Determine dimensions based on orientation
    if orientation == 'landscape':
        canvas_width, canvas_height = 1920, 1080
    else:  # portrait
        canvas_width, canvas_height = 1080, 1920
    
    # Ensure output directory exists at folder_path/Output/Slideshow
    folder_path_resolved = str(pathlib.Path(folder_path).resolve())
    output_dir = os.path.join(folder_path_resolved, "Output", "Slideshow")
    os.makedirs(output_dir, exist_ok=True)
    
    # Set up logging
    setup_logging(output_dir)
    
    if not images:
        print("\033[93mNo images found.\033[0m", file=sys.stderr)
        return None, 0
    
    print()
    print("\033[93mScanning for images...\033[0m")
    print(f"{len(images)} \033[93mimages found\033[0m")
    print()
    
    # Calculate total duration (accounting for transitions if enabled)
    transition_duration = 1.0  # 1 second dissolve
    if use_transitions and len(images) > 1:
        # With transitions: each slide shows for duration_per_slide, but overlaps by 1s with next slide
        total_duration = (len(images) * duration_per_slide) - ((len(images) - 1) * transition_duration)
    else:
        total_duration = len(images) * duration_per_slide
    
    if total_duration > 900:  # 15 minutes in seconds
        print(f"\n\033[93mWarning: The resulting video will be \033[0m{total_duration // 60} \033[93mminutes and\033[0m {total_duration % 60} \033[93mseconds long, exceeding 15 minutes.\033[0m")
        choice = input("\033[93mDo you want to continue? \033[0m\ny for Yes, any other key for No: ").strip().lower()
        if choice != 'y':
            print("\033[93mOperation cancelled.\033[0m")
            return None, 0
    
    # Prepare temporary directory for processed images
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
            print()
            sys.stdout.write(f"\r\033[93mPreparing slides \033[0m{i}/{len(images)}...")
            sys.stdout.flush()
        except Exception as e:
            logging.error(f"Error processing {os.path.basename(img_path)}: {e}")
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
    
    # Create unique output filename
    folder_name = os.path.basename(folder_path_resolved)
    base_output_file = os.path.join(output_dir, f"{folder_name}_slideshow.mp4")
    output_file = base_output_file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    counter = 1
    while os.path.exists(output_file):
        output_file = f"{os.path.splitext(base_output_file)[0]}_{timestamp}_{counter}.mp4"
        counter += 1
    
    # Create video using ffmpeg
    if use_transitions and successful > 1:
        # Create slideshow with dissolve transitions - adapted from your working pairing script
        # Build multiple inputs, each slide as a separate looped input
        input_args = []
        for i in range(successful):
            input_args.extend([
                '-loop', '1', '-t', str(duration_per_slide),
                '-i', os.path.join(temp_dir, f'slide_{i+1:04d}.png')
            ])
        
        # Build xfade chain like your pairing script but for multiple slides
        filter_parts = []
        for i in range(successful - 1):
            if i == 0:
                # First transition: [0:v][1:v]xfade
                filter_parts.append(f'[{i}:v][{i+1}:v]xfade=transition=dissolve:duration={transition_duration}:offset={duration_per_slide-transition_duration}[v{i}]')
            else:
                # Chain subsequent transitions: [v0][2:v]xfade, [v1][3:v]xfade, etc.
                filter_parts.append(f'[v{i-1}][{i+1}:v]xfade=transition=dissolve:duration={transition_duration}:offset={duration_per_slide-transition_duration}[v{i}]')
        
        filter_complex = ';'.join(filter_parts)
        final_output = f'[v{successful-2}]' if successful > 2 else '[v0]'
        
        ffmpeg_cmd = [
            'ffmpeg', '-y'
        ] + input_args + [
            '-filter_complex', filter_complex,
            '-map', final_output,
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-crf', '18',
            '-preset', 'veryfast',
            output_file
        ]
    else:
        # Create slideshow without transitions (original method, but fixed)
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-framerate', f'1/{duration_per_slide}',
            '-i', os.path.join(temp_dir, 'slide_%04d.png'),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-crf', '18',
            output_file
        ]
    
    try:
        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error creating video: {e.stderr}")
        print("\033[93mError creating video. Check slideshow_errors.log for details.\033[0m", file=sys.stderr)
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
        print("\033[1;33mSlideshow Maker\033[0m")
        print("Creates Slideshow with Images")
        print("\033[92m==================================================\033[0m")
        print()
        
        # Input mode selection
        input_mode = djj.prompt_choice(
            "\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
            ['1', '2'],
            default='1'
        )
        print()

        images = []
        folder_path = None

        if input_mode == '1':
            # Folder mode
            folder_path = djj.get_path_input("Enter folder path")
            print()
            
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders?\033[0m\n1. Yes\n2. No\n",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            
            images = collect_images_from_folder(folder_path, include_sub)
            
        else:
            # File paths mode
            file_paths = input("📁 \033[93mEnter image paths (space-separated):\n\033[0m -> ").strip()
            
            if not file_paths:
                print("❌ \033[93mNo file paths provided.\033[0m")
                continue
            
            images = collect_images_from_paths(file_paths)
            # Set folder_path to parent of first image for output folder logic
            if images:
                folder_path = str(pathlib.Path(images[0]).parent)
            print()

        if not images:
            print("❌ \033[93mNo valid image files found. Try again.\033[0m\n")
            continue

        print("Scanning for images...")
        print(f"✅ \033[93m{len(images)} images found\033[0m")
        print()
        
        # Prompt for orientation
        orientation_choice = djj.prompt_choice(
            "\033[93mSlideshow Orientation:\033[0m\n1. Landscape (1920x1080)\n2. Portrait (1080x1920)\n",
            ['1', '2'],
            default='1'
        )
        orientation = 'landscape' if orientation_choice == '1' else 'portrait'
        print()
        
        # Prompt for transitions
        use_transitions = djj.prompt_choice(
            "\033[93mAdd dissolve transitions (1s)?\033[0m\n1. Yes\n2. No\n",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        
        # Background type selection
        background_choice = djj.prompt_choice(
            "\033[93mBackground type:\033[0m\n1. Blurred (from image)\n2. Solid color\n",
            ['1', '2'],
            default='1'
        )
        print()
        
        background_type = 'blurred'
        background_color = (0, 0, 0)
        background_opacity = 0.25
        background_blur_radius = 8
        
        if background_choice == '1':
            # Blurred background options
            bg_opacity_input = input("\033[93mBackground opacity [0.0-1.0, default: 0.25]:\n\033[0m -> ").strip()
            try:
                background_opacity = float(bg_opacity_input) if bg_opacity_input else 0.25
                background_opacity = max(0.0, min(1.0, background_opacity))
            except ValueError:
                background_opacity = 0.25
                print("\033[93mUsing default opacity: 0.25\033[0m")
            print()

            bg_blur_input = input("\033[93mBackground blur radius [1-50, default: 8]:\n\033[0m -> ").strip()
            try:
                background_blur_radius = int(bg_blur_input) if bg_blur_input else 8
                background_blur_radius = max(1, min(50, background_blur_radius))
            except ValueError:
                background_blur_radius = 8
                print("\033[93mUsing default blur: 8\033[0m")
            print()
        else:
            # Solid color background
            background_type = 'solid'
            color_input = input("\033[93mBackground color [R,G,B format like 0,0,0 for black, default: 0,0,0]:\n\033[0m -> ").strip()
            try:
                if color_input:
                    r, g, b = map(int, color_input.split(','))
                    background_color = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
                else:
                    background_color = (0, 0, 0)
            except ValueError:
                background_color = (0, 0, 0)
                print("\033[93mUsing default color: black (0,0,0)\033[0m")
            print()

            bg_opacity_input = input("\033[93mBackground opacity [0.0-1.0, default: 1.0]:\n\033[0m -> ").strip()
            try:
                background_opacity = float(bg_opacity_input) if bg_opacity_input else 1.0
                background_opacity = max(0.0, min(1.0, background_opacity))
            except ValueError:
                background_opacity = 1.0
                print("\033[93mUsing default opacity: 1.0\033[0m")
            print()
        
        # Prompt for duration per slide
        while True:
            try:
                duration_input = input("\033[93mEnter slide duration in seconds [default: 3]:\n\033[0m -> ").strip()
                if not duration_input:
                    duration_per_slide = 3
                    break
                duration_per_slide = int(duration_input)
                if duration_per_slide > 0:
                    break
                else:
                    print("\033[93mPlease enter a positive number.\033[0m")
            except ValueError:
                print("\033[93mPlease enter a valid number.\033[0m")
        
        # Show timing info if transitions are enabled
        if use_transitions and len(images) > 1:
            print(f"\033[93mNote: With transitions, each slide will show for {duration_per_slide}s with 1s dissolve overlap.\033[0m")
        print()
        
        print("\n" * 2)
        print("\033[1;33mProcessing...\033[0m")
        
        # Create slideshow
        output_file, successful = prepare_slides(
            images=images,
            folder_path=folder_path,
            orientation=orientation,
            duration_per_slide=duration_per_slide,
            use_transitions=use_transitions,
            background_type=background_type,
            background_color=background_color,
            background_opacity=background_opacity,
            background_blur_radius=background_blur_radius
        )
        
        # Display results
        print("\n" * 2)
        print("\033[93mSlideshow Creation Summary\033[0m")
        print("-------------")
        print(f"\033[93mSuccessfully processed: \033[0m{successful}\033[93m images\033[0m")
        if use_transitions:
            print(f"\033[93mTransitions: \033[0m1s dissolve between slides")
        if output_file:
            print(f"\033[93mOutput video:\033[0m {output_file}")
            print(f"\033[93mOutput folder:\033[0m {os.path.dirname(output_file)}")
        else:
            print("\033[93mFailed to create video. Check slideshow_errors.log for details.\033[0m")
        print("\n" * 2)
        
        # Open output folder
        if output_file:
            try:
                djj.prompt_open_folder(os.path.dirname(output_file))
            except Exception as e:
                # Fallback: ask user if they want to open the folder manually
                print(f"\033[93mCouldn't auto-open folder. Error: {e}\033[0m")
                open_folder = input("\033[93mOpen output folder manually? (y/n): \033[0m").strip().lower()
                if open_folder == 'y':
                    import subprocess
                    import platform
                    folder_path = os.path.dirname(output_file)
                    try:
                        if platform.system() == "Darwin":  # macOS
                            subprocess.run(["open", folder_path])
                        elif platform.system() == "Windows":  # Windows
                            subprocess.run(["explorer", folder_path])
                        else:  # Linux
                            subprocess.run(["xdg-open", folder_path])
                    except Exception as e2:
                        print(f"\033[93mCouldn't open folder: {e2}\033[0m")
                        print(f"\033[93mFolder location: {folder_path}\033[0m")
        
        # Prompt to go again
        action = djj.what_next()
        if action == 'exit':
            break

os.system('clear')