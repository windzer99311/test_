# video_info.py - Streamlit GUI for YouTube downloader
import streamlit as st
import os
import subprocess
from pytubefix import YouTube
import time
import sys
import re

# Add current directory to path to help with imports
sys.path.append(os.getcwd())

st.set_page_config(
    page_title="YouTube Downloader",
    page_icon="🎬",
    layout="centered"
)

# Create a persistent session state to track if a file is ready for download
if 'file_ready_for_download' not in st.session_state:
    st.session_state.file_ready_for_download = False
    st.session_state.download_file_path = None
    st.session_state.download_file_name = None
    st.session_state.video_file_path = None
    st.session_state.audio_file_path = None
    st.session_state.file_downloaded = False


# Function to delete the server-side files after download
def delete_server_files():
    """Delete downloaded files from the server after client has downloaded them"""
    files_to_delete = [
        st.session_state.download_file_path,
        st.session_state.video_file_path,
        st.session_state.audio_file_path
    ]

    for file_path in files_to_delete:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {str(e)}")

    # Reset session state
    st.session_state.file_ready_for_download = False
    st.session_state.download_file_path = None
    st.session_state.download_file_name = None
    st.session_state.video_file_path = None
    st.session_state.audio_file_path = None
    st.session_state.file_downloaded = True  # Mark as downloaded, the page will refresh on next interaction


# Function to format file size
def format_size(bytes_size):
    """Convert bytes to human-readable format"""
    if bytes_size is None:
        return "Unknown size"

    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} GB"


# Function to get video details
@st.cache_data(ttl=3600, show_spinner=False)
def get_video_info(url):
    """Extract video information from YouTube URL"""
    try:
        yt = YouTube(url)

        # Get basic video info
        title = yt.title
        thumbnail = yt.thumbnail_url
        duration = time.strftime('%H:%M:%S', time.gmtime(yt.length))

        # Get available video streams
        video_streams = {}
        for stream in yt.streams.filter(progressive=False):
            if stream.resolution:
                res = stream.resolution
                fps = stream.fps
                size_bytes = stream.filesize

                # Get the best quality stream for each resolution
                if res not in video_streams or video_streams[res]['fps'] < fps:
                    video_streams[res] = {
                        'fps': fps,
                        'size': format_size(size_bytes),
                        'size_bytes': size_bytes,
                        'stream': stream
                    }

        # Sort by resolution (highest first)
        sorted_streams = sorted(video_streams.items(),
                                key=lambda x: int(x[0][:-1]) if x[0][:-1].isdigit() else 0,
                                reverse=True)

        # Always get the first audio stream with lowest bitrate
        audio_stream = yt.streams.filter(only_audio=True).order_by('bitrate').asc().first()

        return {
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'video_streams': sorted_streams,
            'audio_stream': audio_stream,
            'yt': yt
        }
    except Exception as e:
        st.error(f"Error retrieving video information: {str(e)}")
        return None


# Function to download video
def download_with_hi_py(video_url, audio_url, title, threads=32):
    """Use download.py to download the video with customizable parameters"""
    try:
        # Create a safe filename from the title
        safe_title = "".join([c if c.isalnum() or c in [' ', '.', '_', '-'] else '_' for c in title])
        safe_title = safe_title.strip().replace(' ', '_')

        # Set output filenames based on the title
        video_output = f"{safe_title}.mp4"
        audio_output = f"{safe_title}.m4a"

        # Create a modified version of download.py with the new URLs and parameters
        hi_py_path = "download.py"  # Use the correct path to download.py in your environment

        with open(hi_py_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace URLs and other settings in the content
        content = content.replace("VIDEO_URL =", f"VIDEO_URL =\"{video_url}\"  #")
        content = content.replace("AUDIO_URL =", f"AUDIO_URL =\"{audio_url}\"  #")
        content = content.replace("THREADS =", f"THREADS = {threads}  #")
        content = content.replace("VIDEO_OUTPUT =", f"VIDEO_OUTPUT = \"{video_output}\"  #")
        content = content.replace("AUDIO_OUTPUT =", f"AUDIO_OUTPUT = \"{audio_output}\"  #")
        # Create a modified file in the current directory instead of using tempfile
        temp_path = "hi_modified.py"
        with open(temp_path, 'w', encoding="utf-8") as f:
            f.write(content)

        # Run the modified script and capture output
        process = subprocess.Popen(
            ["python", temp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"}  # Force Python to use UTF-8 for stdout/stderr
        )

        # Create a single progress placeholder that will be updated
        progress_placeholder = st.empty()

        # Initialize variables for tracking progress
        output_text = ""
        last_video_progress = 0
        last_audio_progress = 0
        video_speed = "0 B/s"
        audio_speed = "0 B/s"
        video_eta = "Calculating..."
        audio_eta = "Calculating..."
        combined_progress = 0  # Track combined progress of video and audio
        status_text = "Preparing download..."  # Initialize status text

        # Display initial progress
        with progress_placeholder.container():
            st.write("Download Progress:")
            st.progress(0)
            st.write(status_text)

        # Read the output line by line
        for line in process.stdout:
            output_text += line

            # We don't display the full log anymore for a cleaner interface

            # Check for Video progress
            video_match = re.search(r'Video: \[.*?\] (\d+\.\d+)% at (.*?)/s ETA: (.*?)(?:\n|$)', line)
            if video_match:
                video_percent = float(video_match.group(1))
                video_speed = video_match.group(2)
                video_eta = video_match.group(3)

                # Store video progress
                last_video_progress = video_percent / 100

                # Update combined progress (video is 60% of total, audio is 40%)
                combined_progress = (last_video_progress * 0.6) + (last_audio_progress * 0.4)

                # Calculate overall percentage
                overall_percent = combined_progress * 100

                # Update combined status text
                status_text = f"Overall: {overall_percent:.1f}% | Video: {video_percent:.1f}% at {video_speed}/s"
                if last_audio_progress > 0:
                    status_text += f" | Audio: {last_audio_progress * 100:.1f}% at {audio_speed}/s"

                # Update progress display
                with progress_placeholder.container():
                    st.write("Download Progress:")
                    st.progress(combined_progress)
                    st.write(status_text)

            # Check for Audio progress
            audio_match = re.search(r'Audio: \[.*?\] (\d+\.\d+)% at (.*?)/s ETA: (.*?)(?:\n|$)', line)
            if audio_match:
                audio_percent = float(audio_match.group(1))
                audio_speed = audio_match.group(2)
                audio_eta = audio_match.group(3)

                # Store audio progress
                last_audio_progress = audio_percent / 100

                # Update combined progress (video is 60% of total, audio is 40%)
                combined_progress = (last_video_progress * 0.6) + (last_audio_progress * 0.4)

                # Calculate overall percentage
                overall_percent = combined_progress * 100

                # Update combined status text
                status_text = f"Overall: {overall_percent:.1f}% | Video: {last_video_progress * 100:.1f}% at {video_speed}/s"
                status_text += f" | Audio: {audio_percent:.1f}% at {audio_speed}/s"

                # Update progress display
                with progress_placeholder.container():
                    st.write("Download Progress:")
                    st.progress(combined_progress)
                    st.write(status_text)

        # No threads to stop in this approach

        # Wait for the process to complete
        process.wait()

        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass  # Ignore errors during cleanup

        if process.returncode == 0:
            # Set progress bar to 100% on successful completion
            with progress_placeholder.container():
                st.write("Download Progress:")
                st.progress(1.0)
                st.write("Download completed! Processing final file...")

            # Prepare the final video for download
            video_path = os.path.abspath(video_output)
            audio_path = os.path.abspath(audio_output)
            final_path = os.path.abspath(
                f"{os.path.splitext(video_output)[0]}_video{os.path.splitext(video_output)[1]}")
            file_name = os.path.basename(final_path)

            # Set up the session state for auto-download and file cleanup
            st.session_state.file_ready_for_download = True
            st.session_state.download_file_path = final_path
            st.session_state.download_file_name = file_name
            st.session_state.video_file_path = video_path
            st.session_state.audio_file_path = audio_path

            # Success message
            st.success("✅ Download completed! Video will begin downloading automatically.")

            # Function to mark download as complete and trigger cleanup
            def on_download_complete():
                st.session_state.file_downloaded = True
                delete_server_files()

            # Auto-download file to the browser
            with open(final_path, "rb") as file:
                download_btn = st.download_button(
                    label=f"⬇️ DOWNLOAD VIDEO TO YOUR DEVICE",
                    data=file,
                    file_name=file_name,
                    mime="video/mp4",
                    key="auto_download_btn",
                    use_container_width=True,
                    help="Click to download the video if it doesn't start automatically",
                    on_click=on_download_complete
                )

            return True
        else:
            st.error("Download failed. Check the logs for details.")
            return False

    except Exception as e:
        st.error(f"Error during download: {str(e)}")
        return False


# Main app UI
st.title("YouTube Downloader")
st.markdown("Enter a YouTube URL to download the video")

# Check if there's a file ready for auto-download from previous run
if st.session_state.file_ready_for_download and st.session_state.download_file_path and os.path.exists(
        st.session_state.download_file_path):
    auto_download_container = st.container()
    with auto_download_container:
        file_path = st.session_state.download_file_path
        file_name = st.session_state.download_file_name

        st.success("✅ Your video is ready! Downloading now...")


        # Create a function to trigger cleanup after download
        def on_persistent_download_complete():
            st.session_state.file_downloaded = True
            delete_server_files()


        with open(file_path, "rb") as file:
            st.download_button(
                label=f"⬇️ DOWNLOAD VIDEO TO YOUR DEVICE",
                data=file,
                file_name=file_name,
                mime="video/mp4",
                key="persistent_download_btn",
                use_container_width=True,
                on_click=on_persistent_download_complete
            )

# URL input
url = st.text_input("YouTube URL", key="url_input")

# Process URL when entered
if url:
    with st.spinner("Fetching video information..."):
        video_info = get_video_info(url)

    if video_info:
        # Display video info
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(video_info['thumbnail'], use_container_width=True)

        with col2:
            st.subheader(video_info['title'])
            st.write(f"Duration: {video_info['duration']}")

        st.markdown("---")

        # Quality selection
        st.subheader("Select Video Quality")

        # Video quality dropdown
        video_options = [f"{res} ({details['fps']}fps, {details['size']})"
                         for res, details in video_info['video_streams']]

        if video_options:
            selected_video_index = st.selectbox(
                "Video Quality",
                options=range(len(video_options)),
                format_func=lambda i: video_options[i],
                key="video_quality"
            )

            # Get selected video stream
            selected_video_res, selected_video_details = video_info['video_streams'][selected_video_index]
            selected_video_stream = selected_video_details['stream']

            # Get the audio stream (always using the lowest bitrate)
            audio_stream = video_info['audio_stream']

            # Show audio info (as information only)
            audio_bitrate = audio_stream.abr if hasattr(audio_stream, 'abr') else 'Unknown'
            audio_size = format_size(audio_stream.filesize)
            st.info(f"Audio: {audio_bitrate} ({audio_size}) - automatically selected")

            # Download button
            if st.button("Download & Process Video", key="download_button"):
                video_url = selected_video_stream.url
                audio_url = audio_stream.url

                st.info("Processing started. Your video will download automatically when complete...")
                st.markdown("### Download Progress")

                # Start the download process with the video title as the filename
                download_with_hi_py(
                    video_url,
                    audio_url,
                    video_info['title']
                )
        else:
            st.warning("No video streams found for this video.")
else:
    st.info("Enter a YouTube URL to get started")

# Display app information
with st.expander("About this app"):
    st.markdown("""
    This app uses:
    - pytubefix to extract YouTube video information
    - Streamlit for the user interface
    - download.py for high-performance downloading

    **Privacy Feature:** After downloading a video to your device, the files are automatically 
    deleted from the server to save space and protect your privacy.
    """)