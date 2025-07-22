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



# --- Slideshow Functions ---
def prepare_slides(input_path, orientation, duration_per_slide, include_subfolders, background_opacity=25, background_blur_radius=8):
    """Prepare images for slideshow by adding blurred backgrounds and create a video."""
    # Determine dimensions based on orientation
    if orientation == 'landscape':
        canvas_width, canvas_height = 1920, 1080
    else:  # portrait
        canvas_width, canvas_height = 1080, 1920
    
    # Ensure output directory exists at input_path/Output/Slideshow
    input_path_resolved = str(pathlib.Path(input_path).resolve())
    output_dir = os.path.join(input_path_resolved, "Output", "Slideshow")
    os.makedirs(output_dir, exist_ok=True)
    
    # Set up logging
    setup_logging(output_dir)
    
    # Collect images
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.tiff')
    images = []
    input_path_obj = pathlib.Path(input_path)
    if input_path_obj.is_dir():
        pattern = '**/*' if include_subfolders else '*'
        images = [f for f in input_path_obj.glob(pattern) if f.suffix.lower() in image_extensions and f.is_file()]
    else:
        print("\033[33mError: Input must be a directory.\033[0m", file=sys.stderr)
        return None, 0
    
    if not images:
        print("\033[33mNo images found in the directory.\033[0m", file=sys.stderr)
        return None, 0
    
    print ()
    print ("\033[33mScanning for images...\033[0m")
    print(f"{len(images)} \033[33mimages found\033[0m")
    print ()
    
    # Calculate total duration and warn if over 15 minutes
    total_duration = len(images) * duration_per_slide
    if total_duration > 900:  # 15 minutes in seconds
        print(f"\n\033[33mWarning: The resulting video will be \033[0m{total_duration // 60} \033[33mminutes and\033[0m {total_duration % 60} \033[33mseconds long, exceeding 15 minutes.\033[0m")
        choice = input("\033[33mDo you want to continue? \033[0m\ny for Yes, any other key for No: ").strip().lower()
        if choice != 'y':
            print("\033[33mOperation cancelled.\033[0m")
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
            
            # Create blurred background
            bg_img = img.copy()
            bg_img = bg_img.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=background_blur_radius))
            # Apply opacity
            alpha = Image.new('L', bg_img.size, int(255 * background_opacity))
            bg_img.putalpha(alpha)
            
            # Paste background
            canvas.paste(bg_img, (0, 0), bg_img)
            
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
            sys.stdout.write(f"\r\033[33mPreparing slides \033[0m{i}/{len(images)}...")
            sys.stdout.flush()
        except Exception as e:
            logging.error(f"Error processing {img_path.name}: {e}")
            sys.stdout.write(f"\r\033[33mPreparing slide \033[0m{i}/{len(images)}... \033[33m(failed)\033[0m")
            sys.stdout.flush()
            continue
    print ()
    print ("\n\033[33mCreating Slideshow...\033[0m")
    print ("-------------")
    # Clear processing line
    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()
    
    if successful == 0:
        print("\033[33mNo images were processed successfully.\033[0m", file=sys.stderr)
        return None, 0
    
    # Create unique output filename
    input_folder_name = os.path.basename(input_path_resolved)
    base_output_file = os.path.join(output_dir, f"{input_folder_name}_slideshow.mp4")
    output_file = base_output_file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    counter = 1
    while os.path.exists(output_file):
        output_file = f"{os.path.splitext(base_output_file)[0]}_{timestamp}_{counter}.mp4"
        counter += 1
    
    # Create video using ffmpeg with explicit total duration
    ffmpeg_cmd = [
        'ffmpeg', '-y',  # Overwrite temporary files if they exist
        '-framerate', '1',  # Initial framerate (for image sequence)
        '-i', os.path.join(temp_dir, 'slide_%04d.png'),  # Input pattern
        '-c:v', 'libx264',  # Video codec
        '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
        '-t', str(total_duration),  # Total duration in seconds
        output_file
    ]
    
    try:
        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error creating video: {e.stderr}")
        print("\033[33mError creating video. Check slideshow_errors.log for details.\033[0m", file=sys.stderr)
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
        # Prompt for input path
        max_attempts = 5
        attempt = 0
        input_path = None
        while attempt < max_attempts:
            input_path = input("\033[33mEnter path: \033[0m\n -> ").strip()
            input_path = input_path.strip("'").strip('"').strip()
            try:
                normalized_path = str(pathlib.Path(input_path).resolve())
                if os.path.exists(normalized_path) and os.path.isdir(normalized_path):
                    input_path = normalized_path
                    break
                print(f"\033[33mError: \033[0m'{normalized_path}' \033[33mdoes not exist or is not a directory. Ensure the path is correct and the external drive (if any) is mounted.\033[0m", file=sys.stderr)
            except Exception as e:
                print(f"\033[33mError resolving path \033[0m'{input_path}': {e}. \033[33mPlease try again.\033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        print ()
        # Prompt for subfolder inclusion
        include_subfolders = djj.prompt_choice("\033[33mInclude subfolders?\033[0m \n1. Yes, 2. No ", ['1', '2'], default='2') == '1'
        
        # Prompt for orientation
        attempt = 0
        orientation = None
        while attempt < max_attempts:
            orient_choice = input("\033[33mSlideshow Orientation\033[0m \n(1. Landscape, 2. Portrait): ").strip()
            if orient_choice == '1':
                orientation = 'landscape'
                break
            elif orient_choice == '2':
                orientation = 'portrait'
                break
            print("\033[33mPlease enter \033[0m'1' f\033[33mor Landscape \033[0mor '2' \033[33mfor Portrait only.\033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        
        # Prompt for duration per slide
        attempt = 0
        duration_per_slide = None
        while attempt < max_attempts:
            try:
                duration_input = input("\033[33mEnter slide duration: \033[0m\nin seconds: ").strip()
                duration_per_slide = int(duration_input)
                if duration_per_slide > 0:
                    break
                print("\033[33mPlease enter a positive integer.\033[0m \n(1 for 1 second per slide): ", file=sys.stderr)
            except ValueError:
                print("\033[33mPlease enter a valid integer. \033[0m\n(1 for 1 second per slide): ", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[33mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        print ()
        print ("-------------")
        print()
        # Create slideshow
        output_file, successful = prepare_slides(
            input_path=input_path,
            orientation=orientation,
            duration_per_slide=duration_per_slide,
            include_subfolders=include_subfolders,
            background_opacity=10,
            background_blur_radius=8
        )
        
        # Display results
        print("\n" * 2)
        print("\033[33mSlideshow Creation Summary\033[0m")
        print ("-------------")
        print(f"\033[33mSuccessfully processed: \033[0m{successful}\033[33m images\033[0m")
        if output_file:
            print(f"\033[33mOutput video:\033[0m {output_file}")
            print(f"\033[33mOutput folder:\033[0m {os.path.dirname(output_file)}")
        else:
            print("\033[33mFailed to create video. Check slideshow_errors.log for details.\033[0m")
        print("\n" * 2)
        
        # Open output folder
        if output_file:
            try:
                subprocess.run(['open', os.path.dirname(output_file)], check=True)
            except subprocess.CalledProcessError as e:
                print(f"\033[33mError opening output folder:\033[0m {e}", file=sys.stderr)
        
        # Prompt to go again
        action = djj.what_next()
        if action == 'exit':
            break
os.system('clear')