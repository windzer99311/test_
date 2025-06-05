import requests,re,os
video_chunk_list=[]
audio_chunk_list=[]
# Folder to store temporary chunk files
TEMP_FOLDER = "temp_download_chunks"

# Create temp folder if it doesn't exist

headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': '*/*',
        'Range': 'bytes=0-1'
    }
def video_file_size(video_url):
    total_size = 0
    try:
        response = requests.get(video_url, headers=headers, stream=True, timeout=5)
        if 'Content-Range' in response.headers:
            content_range = response.headers['Content-Range']
            match = re.search(r'bytes \d+-\d+/(\d+)', content_range)
            if match:
                total_size = int(match.group(1))
        response.close()
    except Exception:
        pass
    # If we still don't have a size, try a HEAD request
    if total_size == 0:
        try:
            response = requests.head(video_url, headers=headers, allow_redirects=True, timeout=5)
            if 'Content-Length' in response.headers:
                total_size = int(response.headers['Content-Length'])
        except Exception:
            pass

    return total_size
def segment_video(total_size, num_segments=32):
    # Calculate how long each segment should be
    segment_duration = total_size //num_segments
    # For very short videos, reduce the number of segments
    if total_size < 60 and num_segments > 10:
        num_segments = max(5, int(total_size / 5))
        segment_duration = total_size / num_segments
    return segment_duration
def auido_file_size(url):
    audio_size = 0
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=5)
        if 'Content-Range' in response.headers:
            content_range = response.headers['Content-Range']
            match = re.search(r'bytes \d+-\d+/(\d+)', content_range)
            if match:
                audio_size = int(match.group(1))
        response.close()
    except Exception:
        pass
    # If we still don't have a size, try a HEAD request
    if audio_size == 0:
        try:
            response = requests.head(url, headers=headers, allow_redirects=True, timeout=5)
            if 'Content-Length' in response.headers:
                audio_size = int(response.headers['Content-Length'])
        except Exception:
            pass

    return audio_size
def segment_audio(audio_size, num_segments=32):
    # Calculate how long each segment should be
    segment_duration = audio_size // num_segments
    # For very short videos, reduce the number of segments
    if audio_size < 60 and num_segments > 10:
        num_segments = max(5, int(audio_size / 5))
        segment_duration = audio_size / num_segments
    return segment_duration

def video_byte_range(video_url, num_segments):
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
    video_size = video_file_size(video_url)
    segment_duration = segment_video(video_size)
    start_byte = 0
    for i in range(num_segments):
        file = f"{TEMP_FOLDER}/video_part{i}.mp4"
        end_byte = start_byte + segment_duration
        if i == num_segments - 1:
            end_byte = video_size
        byte_segment=(start_byte,end_byte,file)
        video_chunk_list.append(byte_segment)
        start_byte = end_byte+1
    return video_chunk_list,video_size

def audio_byte_range(url, num_segments):
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
        print("hii")
    audio_size = auido_file_size(url)
    segment_duration = segment_audio(audio_size)
    start_byte = 0
    for i in range(num_segments):
        file=f"{TEMP_FOLDER}/audio_part{i}.m4a"
        end_byte = start_byte + segment_duration
        if i == num_segments - 1:
            end_byte = audio_size
        byte_segment=(start_byte,end_byte,file)
        audio_chunk_list.append(byte_segment)
        start_byte = end_byte+1
    return audio_chunk_list,audio_size,segment_duration