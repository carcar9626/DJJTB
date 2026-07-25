import os
import subprocess
import sys
import shutil

def prompt_folder():
    folder = input("📂 Enter the path to the folder with .webp files: ").strip()
    if not os.path.isdir(folder):
        print("❌ Invalid folder path.")
        sys.exit(1)
    return os.path.abspath(folder)

def extract_frames(webp_path, dump_dir):
    os.makedirs(dump_dir, exist_ok=True)
    try:
        subprocess.run(
            ["anim_dump", webp_path, os.path.join(dump_dir, "frame_%03d.png")],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except subprocess.CalledProcessError:
        print(f"⚠️ Skipping (not animated or failed): {os.path.basename(webp_path)}")
        return False

def convert_to_mp4(frame_dir, output_path):
    subprocess.run([
        "ffmpeg",
        "-y",
        "-framerate", "25",
        "-i", os.path.join(frame_dir, "frame_%03d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    input_folder = prompt_folder()
    output_folder = os.path.join(input_folder, "MP4")
    os.makedirs(output_folder, exist_ok=True)

    temp_root = os.path.join(input_folder, "_temp_frames")
    os.makedirs(temp_root, exist_ok=True)

    webp_files = [f for f in os.listdir(input_folder) if f.lower().endswith(".webp")]
    if not webp_files:
        print("⚠️ No .webp files found.")
        return

    converted = 0
    for webp_file in webp_files:
        webp_path = os.path.join(input_folder, webp_file)
        base_name = os.path.splitext(webp_file)[0]
        temp_dir = os.path.join(temp_root, base_name)

        if extract_frames(webp_path, temp_dir):
            mp4_path = os.path.join(output_folder, base_name + ".mp4")
            convert_to_mp4(temp_dir, mp4_path)
            converted += 1

    shutil.rmtree(temp_root, ignore_errors=True)

    print(f"✅ Done. {converted} animated .webp files converted to MP4 in: {output_folder}")

    open_choice = input("🔍 Open output folder? (y/n): ").strip().lower()
    if open_choice == 'y':
        subprocess.run(["open", output_folder])

if __name__ == "__main__":
    main()