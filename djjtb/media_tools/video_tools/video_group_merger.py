import os
import sys
import subprocess
import pathlib
import logging
import tempfile
import djjtb.utils as djj

os.system('clear')

def clean_path(path_str):
    return path_str.strip().strip('\'"')

def is_valid_video(filename):
    return filename.lower().endswith(('.mp4', '.mov', '.webm', '.mkv'))

def get_user_group_size():
    try:
        group_size = int(input("How many files to merge per group? \n (default 2): ") or 2)
        if group_size < 2:
            raise ValueError
        return group_size
    except ValueError:
        print("❌ Invalid input. Using default of 2.")
        return 2

def collect_videos_from_folder(input_path, subfolders=False):
    """Collect videos from folder(s)"""
    input_path_obj = pathlib.Path(input_path)
    video_extensions = ('.mp4', '.mkv', '.webm', '.mov')
    
    videos = []
    if input_path_obj.is_dir():
        if subfolders:
            for root, _, files in os.walk(input_path):
                videos.extend(pathlib.Path(root) / f for f in files if pathlib.Path(f).suffix.lower() in video_extensions)
        else:
            videos = [f for f in input_path_obj.glob('*') if f.suffix.lower() in video_extensions and f.is_file()]
    
    return sorted([str(v) for v in videos], key=str.lower)

def collect_videos_from_paths(file_paths):
    """Collect videos from space-separated file paths"""
    videos = []
    paths = file_paths.strip().split()
    
    for path in paths:
        path = clean_path(path)
        path_obj = pathlib.Path(path)
        
        if path_obj.is_file() and is_valid_video(path_obj.name):
            videos.append(str(path_obj))
        elif path_obj.is_dir():
            # Get videos from this directory
            dir_videos = collect_videos_from_folder(str(path_obj), subfolders=False)
            videos.extend(dir_videos)
    
    return sorted(videos, key=str.lower)

def get_output_directory(videos, is_folder_mode=True, first_folder=None):
    """Determine output directory based on input mode"""
    if is_folder_mode and first_folder:
        return os.path.join(first_folder, "Output", "VideoMerger")
    elif videos:
        # Use parent directory of first video
        first_video_dir = os.path.dirname(videos[0])
        return os.path.join(first_video_dir, "Output", "VideoMerger")
    else:
        return os.path.join(os.getcwd(), "Output", "VideoMerger")

def get_video_info(video_path):
    """Get video codec, resolution, and framerate info"""
    cmd = [
        "ffprobe", "-v", "quiet", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,r_frame_rate",
        "-of", "csv=p=0", video_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        parts = result.stdout.strip().split(',')
        codec = parts[0] if len(parts) > 0 else "unknown"
        width = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        height = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
        fps = parts[3] if len(parts) > 3 else "30/1"
        return codec, width, height, fps
    except Exception:
        return "unknown", 0, 0, "30/1"

def get_sizing_method(videos):
    """Get user preference for video sizing method"""
    print(f"📹 Found videos with different sizes. Choose sizing method:")
    
    # Show first few video dimensions for reference
    print("\nSample video dimensions:")
    for i, video in enumerate(videos[:3]):
        _, width, height, _ = get_video_info(video)
        print(f"  {i+1}. {os.path.basename(video)}: {width}x{height}")
    if len(videos) > 3:
        print(f"  ... and {len(videos) - 3} more")
    
    print()
    
    sizing_choice = djj.prompt_choice(
        "\033[93mSizing method:\033[0m\n1. Use first video's dimensions\n2. Fixed target size (1920x1080)\n3. Crop all to fit (16:9 or 9:16)\n",
        ['1', '2', '3'],
        default='1'
    )
    
    if sizing_choice == '3':
        print()
        crop_aspect = djj.prompt_choice(
            "\033[93mCrop aspect ratio:\033[0m\n1. 16:9 (horizontal)\n2. 9:16 (vertical)\n",
            ['1', '2'],
            default='1'
        )
        return 'crop', crop_aspect
    
    # For non-crop methods, ask about background handling
    print()
    use_background = djj.prompt_choice(
        "\033[93mBackground method:\033[0m\n1. Blurred background (no black bars)\n2. Black padding (simple/fast)\n",
        ['1', '2'],
        default='1'
    ) == '1'
    
    method_map = {
        '1': 'first_video',
        '2': 'fixed_1920x1080'
    }
    
    base_method = method_map[sizing_choice]
    final_method = f"{base_method}_blur" if use_background else f"{base_method}_pad"
    
    return final_method, None

def build_crop_filter(crop_aspect, width, height):
    """Build crop filter like the cropper script"""
    if crop_aspect == '1':  # 16:9 horizontal
        target_w = int((16 / 9) * height)
        if target_w <= width:
            offset_x = (width - target_w) // 2
            return f"crop={target_w}:{height}:{offset_x}:0", target_w, height
        else:
            # Video is already narrower than 16:9, crop height instead
            target_h = int((9 / 16) * width)
            offset_y = (height - target_h) // 2
            return f"crop={width}:{target_h}:0:{offset_y}", width, target_h
    else:  # 9:16 vertical
        target_w = int((9 / 16) * height)
        if target_w <= width:
            offset_x = (width - target_w) // 2
            return f"crop={target_w}:{height}:{offset_x}:0", target_w, height
        else:
            # Video is already narrower than 9:16, crop height instead
            target_h = int((16 / 9) * width)
            offset_y = (height - target_h) // 2
            return f"crop={width}:{target_h}:0:{offset_y}", width, target_h

def will_need_padding_after_crop(crop_aspect, width, height, target_width, target_height):
    """Check if video will still need padding after cropping"""
    crop_filter, cropped_w, cropped_h = build_crop_filter(crop_aspect, width, height)
    
    # Calculate what the final scaled size would be
    crop_ratio = cropped_w / cropped_h
    target_ratio = target_width / target_height
    
    # If ratios don't match closely, we'll get padding
    ratio_diff = abs(crop_ratio - target_ratio)
    return ratio_diff > 0.05  # 5% tolerance for "close enough"

def create_background_video(video_path, output_path, target_width, target_height, opacity=0.7, blur_radius=8):
    """Create a blurred background video like the collage script"""
    temp_bg_video = os.path.join(os.path.dirname(output_path), f"temp_bg_{os.path.basename(output_path)}")
    
    # Create blurred background that fills the entire target dimensions
    bg_cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
               f"crop={target_width}:{target_height},"
               f"gblur=sigma={blur_radius},"
               f"eq=brightness=-{1-opacity}",  # Darken the background
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-an",  # No audio for background
        temp_bg_video
    ]
    
    result = subprocess.run(bg_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return temp_bg_video
    else:
        print(f"⚠️ Background creation failed: {result.stderr}")
        return None

def simple_merge_all_videos(videos, output_dir):
    """Simple merge: concatenate all videos into one file"""
    os.makedirs(output_dir, exist_ok=True)
    
    logger = djj.setup_logging(output_dir, "simple_merge")
    
    if len(videos) < 2:
        print("❌ Need at least 2 videos to merge")
        return 0, 1, output_dir
    
    print(f"🔄 Merging {len(videos)} videos into one file...")
    
    # Get sizing method choice
    sizing_method, crop_aspect = get_sizing_method(videos)
    print()
    
    # Get target dimensions based on method
    if sizing_method.startswith('first_video'):
        _, target_width, target_height, _ = get_video_info(videos[0])
        print(f"🎯 Using first video dimensions: {target_width}x{target_height}")
    elif sizing_method.startswith('fixed_1920x1080'):
        target_width, target_height = 1920, 1080
        print(f"🎯 Using fixed dimensions: {target_width}x{target_height}")
    elif sizing_method == 'crop':
        # For crop mode, set dimensions based on crop aspect
        if crop_aspect == '1':  # 16:9
            target_width, target_height = 1920, 1080
        else:  # 9:16
            target_width, target_height = 1080, 1920
        aspect_name = "16:9" if crop_aspect == '1' else "9:16"
        print(f"✂️ Cropping all videos to {aspect_name} aspect ratio")
    
    # Show background method being used
    if sizing_method.endswith('_blur'):
        print("🎨 Background settings: 0.7 opacity, 8px blur (no black bars)")
    elif sizing_method.endswith('_pad'):
        print("⬛ Using black padding (faster processing)")
    
    # Create temporary concat list file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        concat_file = f.name
        
        if sizing_method in ['first_video_blur', 'first_video_pad', 'fixed_1920x1080_blur', 'fixed_1920x1080_pad', 'crop']:
            # Process each video to match target dimensions
            temp_videos = []
            for i, video in enumerate(videos):
                print(f"⚙️ Processing video {i+1}/{len(videos)}: {os.path.basename(video)}")
                
                temp_processed = os.path.join(output_dir, f"temp_processed_{i}.mp4")
                temp_videos.append(temp_processed)
                
                # Get current video info
                _, curr_width, curr_height, _ = get_video_info(video)
                
                if sizing_method == 'crop':
                    # Check if this video will still need padding after crop
                    needs_padding = will_need_padding_after_crop(crop_aspect, curr_width, curr_height, target_width, target_height)
                    
                    if needs_padding:
                        print(f"  🎨 Video has edgy dimensions, using blur background instead of crop")
                        # Use background blur method for this weird-ratio video
                        bg_video = create_background_video(video, temp_processed, target_width, target_height)
                        
                        if bg_video:
                            # Overlay original video on background
                            process_cmd = [
                                "ffmpeg", "-y",
                                "-i", bg_video,  # Background layer
                                "-i", video,     # Original video
                                "-filter_complex",
                                f"[1:v]scale='if(gt(iw/ih,{target_width}/{target_height}),{target_width},-2)':'if(gt(iw/ih,{target_width}/{target_height}),-2,{target_height})'[scaled];"
                                f"[0:v][scaled]overlay=(W-w)/2:(H-h)/2[outv]",
                                "-map", "[outv]", "-map", "1:a?",
                                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                                "-c:a", "aac", "-b:a", "128k",
                                "-r", "30", "-pix_fmt", "yuv420p",
                                temp_processed
                            ]
                        else:
                            # Fallback to regular crop if background fails
                            crop_filter, _, _ = build_crop_filter(crop_aspect, curr_width, curr_height)
                            process_cmd = [
                                "ffmpeg", "-y", "-i", video,
                                "-vf", f"{crop_filter},scale={target_width}:{target_height}",
                                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                                "-c:a", "aac", "-b:a", "128k",
                                "-r", "30", "-pix_fmt", "yuv420p",
                                temp_processed
                            ]
                    else:
                        # Normal crop - no padding expected
                        crop_filter, _, _ = build_crop_filter(crop_aspect, curr_width, curr_height)
                        process_cmd = [
                            "ffmpeg", "-y", "-i", video,
                            "-vf", f"{crop_filter},scale={target_width}:{target_height}",
                            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                            "-c:a", "aac", "-b:a", "128k",
                            "-r", "30", "-pix_fmt", "yuv420p",
                            temp_processed
                        ]
                    
                elif sizing_method.endswith('_blur'):
                    # Use background blur method
                    bg_video = create_background_video(video, temp_processed, target_width, target_height)
                    
                    if bg_video:
                        # Overlay original video on background - properly centered
                        process_cmd = [
                            "ffmpeg", "-y",
                            "-i", bg_video,  # Background layer
                            "-i", video,     # Original video
                            "-filter_complex",
                            # Scale the original video to fit within target dimensions (maintain aspect ratio)
                            f"[1:v]scale='if(gt(iw/ih,{target_width}/{target_height}),{target_width},-2)':'if(gt(iw/ih,{target_width}/{target_height}),-2,{target_height})'[scaled];"
                            # Overlay the scaled video centered on the background
                            f"[0:v][scaled]overlay=(W-w)/2:(H-h)/2[outv]",
                            "-map", "[outv]", "-map", "1:a?",
                            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                            "-c:a", "aac", "-b:a", "128k",
                            "-r", "30", "-pix_fmt", "yuv420p",
                            temp_processed
                        ]
                    else:
                        # Fallback: scale and pad with black
                        process_cmd = [
                            "ffmpeg", "-y", "-i", video,
                            "-vf", f"scale='if(gt(iw/ih,{target_width}/{target_height}),{target_width},-2)':'if(gt(iw/ih,{target_width}/{target_height}),-2,{target_height})',"
                                   f"pad={target_width}:{target_height}:({target_width}-iw)/2:({target_height}-ih)/2:color=black",
                            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                            "-c:a", "aac", "-b:a", "128k",
                            "-r", "30", "-pix_fmt", "yuv420p",
                            temp_processed
                        ]
                        
                else:  # sizing_method.endswith('_pad') - black padding
                    # Scale to fit target dimensions with black padding
                    process_cmd = [
                        "ffmpeg", "-y", "-i", video,
                        "-vf", f"scale='if(gt(iw/ih,{target_width}/{target_height}),{target_width},-2)':'if(gt(iw/ih,{target_width}/{target_height}),-2,{target_height})',"
                               f"pad={target_width}:{target_height}:({target_width}-iw)/2:({target_height}-ih)/2:color=black",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-c:a", "aac", "-b:a", "128k",
                        "-r", "30", "-pix_fmt", "yuv420p",
                        temp_processed
                    ]
                
                result = subprocess.run(process_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"❌ Failed to process video {i+1}")
                    logger.error(f"Failed to process {video}: {result.stderr}")
                    # Clean up temp files
                    for temp_vid in temp_videos:
                        if os.path.exists(temp_vid):
                            os.remove(temp_vid)
                    if sizing_method.endswith('_blur') and 'bg_video' in locals() and bg_video and os.path.exists(bg_video):
                        os.remove(bg_video)
                    return 0, 1, output_dir
                
                # Clean up background temp file (for both blur methods and crop fallbacks)
                if (sizing_method.endswith('_blur') or (sizing_method == 'crop' and 'bg_video' in locals())) and 'bg_video' in locals() and bg_video and os.path.exists(bg_video):
                    os.remove(bg_video)
                
                f.write(f"file '{temp_processed}'\n")
        else:
            # Simple concat without processing - just list the original files
            for video in videos:
                escaped_path = video.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
    
    # Generate output filename
    base_name = os.path.splitext(os.path.basename(videos[0]))[0]
    output_file = os.path.join(output_dir, f"{base_name}_merged_all.mp4")
    
    # Final merge command - always use re-encoding for processed videos
    merge_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c", "copy" if sizing_method == 'simple' else "copy",  # Already processed, just copy
        output_file
    ]
    
    try:
        print("🔄 Final merge in progress...")
        result = subprocess.run(merge_cmd, capture_output=True, text=True, check=True)
        print(f"✅ Successfully merged all videos into: {os.path.basename(output_file)}")
        logger.info(f"Successfully merged {len(videos)} videos to {output_file}")
        
        # Clean up temp files
        if 'temp_videos' in locals():
            for temp_vid in temp_videos:
                if os.path.exists(temp_vid):
                    os.remove(temp_vid)
        
        if os.path.exists(concat_file):
            os.remove(concat_file)
        
        return 1, 0, output_dir
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Merge failed: {e.stderr}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)
        
        # Clean up temp files on error
        if 'temp_videos' in locals():
            for temp_vid in temp_videos:
                if os.path.exists(temp_vid):
                    os.remove(temp_vid)
        
        if os.path.exists(concat_file):
            os.remove(concat_file)
            
        return 0, 1, output_dir

def merge_video_groups(videos, output_dir, group_size):
    """Merge videos into groups with improved stability"""
    os.makedirs(output_dir, exist_ok=True)
    
    logger = djj.setup_logging(output_dir, "group_merge")
    
    total_groups = len(videos) // group_size
    remaining = len(videos) % group_size
    
    if remaining != 0:
        print(f"⚠️ {remaining} file(s) will be skipped (not enough to complete a group of {group_size}).")
    
    print(f"📄 Found {len(videos)} videos. Merging into {total_groups} group(s) of {group_size}...")
    
    # Choose encoding method
    use_re_encoding = djj.prompt_choice(
        "\033[93mMerge method:\033[0m\n1. Re-encode (safer, fixes freezing issues)\n2. Copy streams (faster, but may freeze)\n",
        ['1', '2'],
        default='1'
    ) == '1'
    print()
    
    success_count = 0
    error_count = 0
    
    for g in range(total_groups):
        group_videos = videos[g * group_size : (g + 1) * group_size]
        
        # Create temporary concat list file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            concat_list_path = f.name
            for vid in group_videos:
                escaped_path = vid.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
        
        # Generate output filename based on first video in group
        base_name = os.path.splitext(os.path.basename(group_videos[0]))[0]
        output_file = os.path.join(output_dir, f"{base_name}_group_{g+1:03d}.mp4")
        
        if use_re_encoding:
            # Re-encode for stability - fixes freezing issues
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-r", "30",  # Force consistent framerate
                "-pix_fmt", "yuv420p",  # Ensure compatibility
                output_file
            ]
        else:
            # Stream copy - faster but may have issues
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c", "copy",
                output_file
            ]
        
        try:
            print(f"⚙️ Processing group {g+1}/{total_groups}...")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✅ Group {g+1}: Created {os.path.basename(output_file)}")
            logger.info(f"Group {g+1}: Merged {len(group_videos)} videos to {output_file}")
            success_count += 1
        except subprocess.CalledProcessError as e:
            error_msg = f"Group {g+1} failed: {e.stderr[-200:]}"  # Last 200 chars of error
            print(f"❌ {error_msg}")
            logger.error(f"Group {g+1} failed: {e.stderr}")
            error_count += 1
        finally:
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)
    
    return success_count, error_count, output_dir

def main():
    while True:
        print()
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;93mVideo Merger\033[0m")
        print("Simple merge or group merge videos")
        print("\033[92m==================================================\033[0m")
        print()
        
        # Choose merge type first
        merge_type = djj.prompt_choice(
            "\033[93mMerge type:\033[0m\n1. Simple merge (all videos into one)\n2. Group merge (every N videos into groups)\n",
            ['1', '2'],
            default='1'
        )
        print()
        
        # Get input mode
        input_mode = djj.prompt_choice(
            "\033[93mInput mode:\033[0m\n1. Folder path\n2. Space-separated file paths\n",
            ['1', '2'],
            default='2'
        )
        print()
        
        videos = []
        output_dir = None
        
        if input_mode == '1':
            # Folder mode
            src_dir = input("📁 \033[93mEnter folder path: \n -> \033[0m").strip()
            src_dir = clean_path(src_dir)
            
            if not os.path.isdir(src_dir):
                print(f"❌ \033[93mThe path\033[0m '{src_dir}' \033[93mis not a valid directory\033[0m.")
                continue
            
            print()
            include_sub = djj.prompt_choice(
                "\033[93mInclude subfolders? \033[0m\n1. Yes\n2. No\n",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            
            videos = collect_videos_from_folder(src_dir, include_sub)
            output_dir = get_output_directory(videos, is_folder_mode=True, first_folder=src_dir)
            
        else:
            # File paths mode - improved to handle folders too
            file_paths = input("📁 \033[93mEnter file/folder paths (space-separated): \n -> \033[0m").strip()
            
            if not file_paths:
                print("❌ No file paths provided.")
                continue
            
            videos = collect_videos_from_paths(file_paths)
            output_dir = get_output_directory(videos, is_folder_mode=False)
            print()
        
        if not videos:
            print("❌ \033[93mNo valid video files found.\033[0m")
            continue
        
        print(f"✅ Found {len(videos)} video files")
        # Show first few files
        for i, video in enumerate(videos[:3]):
            print(f"  {i+1}. {os.path.basename(video)}")
        if len(videos) > 3:
            print(f"  ... and {len(videos) - 3} more")
        print()
        
        if merge_type == '1':
            # Simple merge all videos
            success_count, error_count, final_output_dir = simple_merge_all_videos(videos, output_dir)
        else:
            # Group merge
            group_size = get_user_group_size()
            print()
            success_count, error_count, final_output_dir = merge_video_groups(videos, output_dir, group_size)
        
        print(f"\033[93m\n🏁 Done!\033[0m {success_count} \033[93mvideo(s) created, \033[0m{error_count} \033[93merror(s).\033[0m")
        print(f"📁\033[93m Output folder:\033[0m {final_output_dir}")
        print()
        djj.prompt_open_folder(final_output_dir)
         
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()