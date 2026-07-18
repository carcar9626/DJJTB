#!/usr/bin/env python3
"""
Transition Helper for DJJTB - Reusable dissolve transition logic
Can be added to djjtb.utils or used as standalone helper
"""
#Usage:
#from transition_helper import create_dissolve_slideshow
#
#success, message = create_dissolve_slideshow(images, output_file)

import subprocess
import logging
import os

def create_dissolve_slideshow(images, output_file, duration_per_slide=4, transition_duration=1.0,
                             canvas_width=1920, canvas_height=1080):
    """
    Create a slideshow with dissolve transitions using proven ffmpeg logic.
    
    Args:
        images: List of image file paths
        output_file: Output video file path
        duration_per_slide: How long each slide shows (seconds)
        transition_duration: Duration of dissolve transition (seconds)
        canvas_width: Output video width
        canvas_height: Output video height
    
    Returns:
        tuple: (success: bool, message: str)
    """
    
    if not images:
        return False, "No images provided"
    
    if len(images) == 1:
        # Single image - no transitions needed
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(duration_per_slide), "-i", images[0],
            "-vf", f"scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=decrease,pad={canvas_width}:{canvas_height}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
            "-r", "30", "-fps_mode", "cfr",
            output_file
        ]
    else:
        # Multiple images - use dissolve transitions
        cmd = ["ffmpeg", "-y"]
        
        # Add all images as inputs
        for img_path in images:
            cmd.extend(["-loop", "1", "-t", str(duration_per_slide), "-i", img_path])
        
        # Build filter complex with proper overlap timing
        filter_parts = []
        overlay_chain = []
        
        for i in range(len(images)):
            # Scale and format each input
            scale_filter = f"[{i}:v]scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=decrease,pad={canvas_width}:{canvas_height}:(ow-iw)/2:(oh-ih)/2,format=yuva420p"
            
            if i == 0:
                # First image: fade out at the end
                fade_filter = f"{scale_filter},fade=t=out:st={duration_per_slide-transition_duration}:d={transition_duration}:alpha=1,setpts=PTS-STARTPTS[va{i}]"
                filter_parts.append(fade_filter)
                overlay_chain.append(f"va{i}")
            else:
                # Subsequent images: fade in, offset by (duration - transition) for each previous
                offset_time = i * (duration_per_slide - transition_duration)
                fade_filter = f"{scale_filter},fade=t=in:st=0:d={transition_duration}:alpha=1,setpts=PTS-STARTPTS+{offset_time}/TB[va{i}]"
                filter_parts.append(fade_filter)
                overlay_chain.append(f"va{i}")
        
        # Chain overlays
        current_base = overlay_chain[0]
        for i in range(1, len(overlay_chain)):
            overlay_filter = f"[{current_base}][{overlay_chain[i]}]overlay[ov{i}]"
            current_base = f"ov{i}"
            filter_parts.append(overlay_filter)
        
        # Calculate exact final duration and add trim
        final_duration = len(images) * duration_per_slide - (len(images) - 1) * transition_duration
        filter_parts.append(f"[{current_base}]trim=duration={final_duration}")
        
        filter_complex = ";".join(filter_parts)
        
        cmd.extend([
            "-filter_complex", filter_complex,
            "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
            "-r", "30", "-t", str(final_duration), "-fps_mode", "cfr",
            output_file
        ])
    
    # Execute ffmpeg command
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True, f"Successfully created slideshow: {output_file}"
    except subprocess.CalledProcessError as e:
        error_msg = f"FFmpeg error: {e.stderr}"
        logging.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logging.error(error_msg)
        return False, error_msg


def calculate_slideshow_duration(num_images, duration_per_slide, transition_duration=1.0):
    """
    Calculate total slideshow duration with transitions.
    
    Args:
        num_images: Number of images in slideshow
        duration_per_slide: Duration each slide is visible
        transition_duration: Duration of each transition
    
    Returns:
        float: Total video duration in seconds
    """
    if num_images <= 1:
        return duration_per_slide
    return num_images * duration_per_slide - (num_images - 1) * transition_duration


# Example usage and test function
if __name__ == "__main__":
    # Test the function
    test_images = [
        "/path/to/image1.jpg",
        "/path/to/image2.jpg",
        "/path/to/image3.jpg"
    ]
    
    output_path = "/path/to/output.mp4"
    
    success, message = create_dissolve_slideshow(
        images=test_images,
        output_file=output_path,
        duration_per_slide=5,
        transition_duration=1.0,
        canvas_width=1920,
        canvas_height=1080
    )
    
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")
    
    # Calculate duration
    total_duration = calculate_slideshow_duration(len(test_images), 5, 1.0)
    print(f"Expected duration: {total_duration} seconds")
