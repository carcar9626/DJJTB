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
        
        # Build ffmpeg command exactly like pairing script but for multiple images
        cmd = ["ffmpeg", "-y"]
        
        # Add all images as inputs with proper duration
        for img_path in images:
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
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "veryfast",
            "-r", "30",
            "-t", str(final_duration),
            "-fps_mode", "cfr",
            output_file
        ])
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error creating slideshow with transitions: {e.stderr}")
            print("\033[93mError creating slideshow. Check slideshow_errors.log for details.\033[0m", file=sys.stderr)
            return None, len(images)
            
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
        
        # Create video using ffmpeg - FIXED TIMING
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-framerate', f'1/{duration_per_slide}',
            '-i', os.path.join(temp_dir, 'slide_%04d.png'),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
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
        print("\033[1;93mSlideshow Maker\033[0m")
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
            folder_path = djj.get_path_input("\033[93mEnter folder path\033[0m")
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
            file_paths = input("📁 \033[93mEnter image paths (space-separated):\033[0m\n -> ").strip()
            
            if not file_paths:
                print("❌ \033[1;5;93mNo file paths provided.\033[0m")
                continue
            
            images = collect_images_from_paths(file_paths)
            # Set folder_path to parent of first image for output folder logic
            if images:
                folder_path = str(pathlib.Path(images[0]).parent)
            print()

        if not images:
            print("\033[1;5;93m❌ No valid image files found. Try again.\033[0m\n")
            continue

        print("Scanning for images...")
        print(f"✅ {len(images)} \033[93mimages found\033[0m")
        print()
        
        # Prompt for orientation
        orientation_choice = djj.prompt_choice(
            "\033[93mSlideshow Orientation:\033[0m\n1. Landscape (1920x1080)\n2. Portrait (1080x1920)\n",
            ['1', '2'],
            default='2'
        )
        orientation = 'landscape' if orientation_choice == '1' else 'portrait'
        print()
        
        # Transition option - NEW!
        use_transitions = djj.prompt_choice(
            "\033[93mAdd dissolve transitions?\033[0m\n1. Yes\n2. No\n",
            ['1', '2'],
            default='2'
        ) == '1'
        print()
        
        # Background options (skip if using transitions)
        background_type = 'blurred'
        background_color = (0, 0, 0)
        background_opacity = 0.8
        background_blur_radius = 8
        
        if not use_transitions:
            # Background type selection
            background_choice = djj.prompt_choice(
                "Background type:\n1. Blurred (from image)\n2. Solid color\n",
                ['1', '2'],
                default='1'
            )
            print()
            
            if background_choice == '1':
                # Blurred background options
                bg_opacity_input = input("Background opacity [0.0-1.0, default: 0.8]:\n -> ").strip()
                try:
                    background_opacity = float(bg_opacity_input) if bg_opacity_input else 0.8
                    background_opacity = max(0.0, min(1.0, background_opacity))
                except ValueError:
                    background_opacity = 0.8
                    print("Using default opacity: 0.8")
                print()

                bg_blur_input = input("Background blur radius [1-50, default: 8]:\n -> ").strip()
                try:
                    background_blur_radius = int(bg_blur_input) if bg_blur_input else 8
                    background_blur_radius = max(1, min(50, background_blur_radius))
                except ValueError:
                    background_blur_radius = 8
                    print("Using default blur: 8")
                print()
            else:
                # Solid color background
                background_type = 'solid'
                color_input = input("Background color [R,G,B format like 0,0,0 for black, default: 0,0,0]:\n -> ").strip()
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

                bg_opacity_input = input("Background opacity [0.0-1.0, default: 1.0]:\n -> ").strip()
                try:
                    background_opacity = float(bg_opacity_input) if bg_opacity_input else 1.0
                    background_opacity = max(0.0, min(1.0, background_opacity))
                except ValueError:
                    background_opacity = 1.0
                    print("Using default opacity: 1.0")
                print()
        
        # Prompt for duration per slide
        while True:
            try:
                duration_input = input("Enter slide duration in seconds [default: 5]:\n -> ").strip()
                if not duration_input:
                    duration_per_slide = 5
                    break
                duration_per_slide = int(duration_input)
                if duration_per_slide > 0:
                    break
                else:
                    print("\033[5;93mPlease enter a positive number.\033[0m")
            except ValueError:
                print("\033[5;93mPlease enter a valid number.\033[0m")
        
        print()
        print("\033[1;93mProcessing...\033[0m")
        
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
        print()
        print("\033[93mSlideshow Creation Summary\033[0m")
        print("-------------")
        print(f"Successfully processed: {successful} images")
        if output_file:
            print(f"Output video: {output_file}")
            print(f"Output folder: {os.path.dirname(output_file)}")
        else:
            print("Failed to create video. Check slideshow_errors.log for details.")
        print()
        
        # Open output folder
        if output_file:
            djj.prompt_open_folder(os.path.dirname(output_file))
        
        # Prompt to go again
        action = djj.what_next()
        if action == 'exit':
            break

    os.system('clear')