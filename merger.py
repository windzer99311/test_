#!/usr/bin/env python3
"""
Easy Merger - Lightning-fast audio/video merger with simple interactive prompts
Just run this script and answer two simple questions!
"""

import os
import sys
import time
import subprocess

# ANSI color codes for prettier output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
ENDC = '\033[0m'


def merge_files(video_path, audio_path, output_path):
    """Merge video and audio files with maximum speed"""
    # No print statements for a cleaner UI in Streamlit
    
    # Start timing
    start_time = time.time()

    # Try to find ffmpeg in system path first (for Streamlit Cloud and other platforms)
    # But fall back to the Replit path if needed
    ffmpeg_paths = [
        "ffmpeg",  # System path (Streamlit Cloud)
        "/usr/bin/ffmpeg",  # Common Linux path
        "/nix/store/3zc5jbvqzrn8zmva4fx5p0nh4yy03wk4-ffmpeg-6.1.1-bin/bin/ffmpeg"  # Replit path
    ]
    
    # Find the first working ffmpeg path
    ffmpeg_path = None
    for path in ffmpeg_paths:
        try:
            subprocess.run(
                [path, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            ffmpeg_path = path
            break
        except (FileNotFoundError, subprocess.SubprocessError):
            continue
            
    # If no ffmpeg found, return error
    if ffmpeg_path is None:
        return False
    cmd = [
        ffmpeg_path,
        "-y",  # Always overwrite
        "-v", "warning",  # Minimal output for speed
        "-stats",  # Show progress stats
        "-i", video_path,  # Video input
        "-i", audio_path,  # Audio input
        "-c:v", "copy",  # Copy video codec (no re-encoding)
        "-c:a", "copy",  # Copy audio codec (no re-encoding)
        "-map", "0:v?",  # Map all video streams if present
        "-map", "1:a?",  # Map all audio streams if present
        "-max_muxing_queue_size", "4096",  # Extra large muxing queue
        "-movflags", "faststart",  # Optimize for streaming
        output_path  # Output file
    ]

    try:
        # Run the FFmpeg process
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Check if successful
        if process.returncode != 0:
            # Silently fail without print statements
            return False

        # Calculate processing stats (but don't print them)
        end_time = time.time()
        processing_time = end_time - start_time

        # Success!
        return True

    except Exception as e:
        # Silent failure
        return False


def start_merg(video_path, audio_path):
    """Main function - streamlined for Streamlit use"""

    # Try to find ffmpeg in system path first (for Streamlit Cloud and other platforms)
    # But fall back to the Replit path if needed
    ffmpeg_paths = [
        "ffmpeg",  # System path (Streamlit Cloud)
        "/usr/bin/ffmpeg",  # Common Linux path
        "/nix/store/3zc5jbvqzrn8zmva4fx5p0nh4yy03wk4-ffmpeg-6.1.1-bin/bin/ffmpeg"  # Replit path
    ]
    
    # Find the first working ffmpeg path
    ffmpeg_path = None
    for path in ffmpeg_paths:
        try:
            subprocess.run(
                [path, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            ffmpeg_path = path
            break
        except (FileNotFoundError, subprocess.SubprocessError):
            continue
            
    # If no ffmpeg found, return error
    if ffmpeg_path is None:
        return 1

    # Remove quotes if the files have them
    if video_path.startswith('"') and video_path.endswith('"'):
        video_path = video_path[1:-1]
    
    if audio_path.startswith('"') and audio_path.endswith('"'):
        audio_path = audio_path[1:-1]

    # Check if files exist
    if not os.path.exists(video_path) or not os.path.exists(audio_path):
        return False

    # Auto-generate output filename
    video_dir = os.path.dirname(video_path) or '.'
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    video_ext = os.path.splitext(video_path)[1]
    output_path = os.path.join(video_dir, f"{video_name}_video{video_ext}")

    # Do the merge
    success = merge_files(video_path, audio_path, output_path)

    # Clean up files on success
    if success:
        try:
            os.remove(video_path)
            os.remove(audio_path)
        except:
            pass  # Ignore cleanup errors
        
    # Return status without exit (let Streamlit handle the app lifecycle)
    return success


