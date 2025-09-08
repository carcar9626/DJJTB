import os
import subprocess
import sys
import time
from PIL import Image
import pathlib
import logging
import djjtb.utils as djj

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


def clean_path(path_str):
    """Clean input path by removing quotes and extra spaces."""
    return path_str.strip().strip('\'"')


def is_valid_image(file_path):
    """Check if a file is a valid image."""
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception as e:
        logging.error(f"Invalid image {file_path}: {e}")
        return False

def get_max_size(img1_path, img2_path):
    """Get maximum dimensions of two images, ensuring even numbers."""
    try:
        size1 = Image.open(img1_path).size
        size2 = Image.open(img2_path).size
        width = max(size1[0], size2[0])
        height = max(size1[1], size2[1])
        width = width if width % 2 == 0 else width + 1
        height = height if height % 2 == 0 else height + 1
        return width, height
    except Exception as e:
        logging.error(f"Error getting image sizes for {img1_path} or {img2_path}: {e}")
        return None

def process_pairs(input_path, pic1_duration, pic2_duration, transition_duration, include_sub):
    """Process image pairs into videos with transitions."""
    input_path = pathlib.Path(input_path).resolve()
    if not input_path.exists():
        print("Error: Input path does not exist.", file=sys.stderr)
        return 0, 0

    output_base = os.path.join(str(input_path), "Output", "Paired")
    os.makedirs(output_base, exist_ok=True)
    setup_logging(output_base)

    image_extensions = ('.jpg', '.jpeg', '.png')
    images = []
    if input_path.is_file() and input_path.suffix.lower() in image_extensions:
        images = [input_path]
    elif input_path.is_dir():
        pattern = '**/*' if include_sub else '*'
        images = sorted(
            [f for f in input_path.glob(pattern) if f.suffix.lower() in image_extensions and f.is_file()],
            key=lambda x: str(x).lower()
        )

    print("Scanning for Images...")
    print(f"{len(images)} images found")
    print()
    print("Processing Pairs...")

    if len(images) % 2 != 0:
        print("WARNING: Odd number of files. The last file will be skipped.", file=sys.stderr)

    total_duration = pic1_duration + pic2_duration - transition_duration
    success_count = 0
    error_count = 0
    total_pairs = len(images) // 2

    for i in range(0, len(images) - 1, 2):
        img1_path = images[i]
        img2_path = images[i + 1]
        pair_num = i // 2 + 1

        sys.stdout.write(f"\rProcessing {pair_num}/{total_pairs} pairs ({pair_num/total_pairs*100:.1f}%)...")
        sys.stdout.flush()

        if not (is_valid_image(img1_path) and is_valid_image(img2_path)):
            error_count += 1
            continue

        resolution = get_max_size(img1_path, img2_path)
        if not resolution:
            error_count += 1
            continue
        width, height = resolution

        relative_path = os.path.relpath(img1_path.parent, input_path)
        output_dir = os.path.join(output_base, relative_path) if relative_path != '.' else output_base
        os.makedirs(output_dir, exist_ok=True)

        filename_noext = img1_path.stem.split('_', 1)[1] if '_' in img1_path.stem else img1_path.stem
        out_file = os.path.join(output_dir, f"{filename_noext}_paired.mp4")

        transition_start = pic1_duration - transition_duration
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(pic1_duration), "-i", str(img1_path),
            "-loop", "1", "-t", str(pic2_duration), "-i", str(img2_path),
            "-filter_complex",
            (
                f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=yuva420p,fade=t=out:st={transition_start}:d={transition_duration}:alpha=1,setpts=PTS-STARTPTS[va0];"
                f"[1:v]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=yuva420p,fade=t=in:st=0:d={transition_duration}:alpha=1,setpts=PTS-STARTPTS+{transition_start}/TB[va1];"
                f"[va0][va1]overlay,settb=1/30,trim=duration={total_duration}"
            ),
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "veryfast",
            "-r", "30",
            "-t", str(total_duration),
            "-fps_mode", "cfr",
            str(out_file)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            success_count += 1
        except subprocess.CalledProcessError as e:
            logging.error(f"Error processing pair {img1_path.name} + {img2_path.name}: {e.stderr}")
            error_count += 1

    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()
    return success_count, error_count, output_base

if __name__ == "__main__":
    while True:
        clear_screen()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mImage Pairing\033[0m")
        print("Combines Images into Videos")
        print("\033[92m==================================================\033[0m")
        print()

        max_attempts = 5
        attempt = 0
        input_path = None
        while attempt < max_attempts:
            input_path = input("\033[93mEnter path:\033[0m \n -> ").strip()
            input_path = clean_path(input_path)
            try:
                normalized_path = str(pathlib.Path(input_path).resolve())
                if os.path.exists(normalized_path):
                    input_path = normalized_path
                    break
                print(f"\033[93mError:\033[0m '{normalized_path}' \033[93mdoes not exist. Ensure the path is correct and the external drive (if any) is mounted.\033[0m", file=sys.stderr)
            except Exception as e:
                print(f"\033[93mError resolving path\033[0m '{input_path}': {e}. \033[93mPlease try again.\033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[93mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        print()

        include_sub = djj.prompt_choice("Include subfolders?\n1. Yes, 2. No ", ['1', '2'], default='2') == '1'
        print()

        attempt = 0
        pic1_duration = None
        while attempt < max_attempts:
            try:
                pic1_duration = float(input("\033[93mDuration for first image (seconds)\033[0m [default: 5]: ").strip() or 5)
                if pic1_duration > 0:
                    break
                print("\033[93mPlease enter a positive number.\033[0m", file=sys.stderr)
            except ValueError:
                print("\033[93mPlease enter a valid number.\033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[93mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        print()

        attempt = 0
        pic2_duration = None
        while attempt < max_attempts:
            try:
                pic2_duration = float(input("\033[93mDuration for second image (seconds)\033[0m\n [default: 5]: ").strip() or 5)
                if pic2_duration > 0:
                    break
                print("Please enter a positive number.", file=sys.stderr)
            except ValueError:
                print("\033[93mPlease enter a valid number.\033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[93mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        print()

        attempt = 0
        transition_duration = None
        while attempt < max_attempts:
            try:
                transition_duration = float(input("Transition duration (seconds) /n[default: 1]:  ").strip() or 1)
                print()
                if transition_duration >= 0:
                    break
                print("\033[93mPlease enter a non-negative number.\033[0m", file=sys.stderr)
            except ValueError:
                print("\033[93mPlease enter a valid number.\033[0m", file=sys.stderr)
            attempt += 1
            if attempt == max_attempts:
                print("\033[93mToo many invalid attempts. Exiting.\033[0m", file=sys.stderr)
                sys.exit(1)
        print()

        total_duration = pic1_duration + pic2_duration - transition_duration
        print(f"\033[93mTotal video duration: \033[0m{total_duration} seconds")
        print("-------------")

        success_count, error_count, output_base = process_pairs(
            input_path, pic1_duration, pic2_duration, transition_duration, include_sub
        )

        print("\n" * 1)
        print("\033[93mPairing Summary\033[0m")
        print("-------------")
        print(f"✅ \033[93mSuccessfully processed:\033[0m {success_count} \033[93mpairs\033[0m")
        if error_count:
            print(f"\033[93mFailed pairs:\033[0m {error_count} \033[93m(see pairing_errors.log in output folder)\033[0m")
        print(f"\033[93mOutput folder: \033[0m\n{output_base}")
        print("\n" * 2)

        djj.prompt_open_folder(output_base)

        action = djj.what_next()
        if action == 'exit':
            break