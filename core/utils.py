import os
import shutil
import subprocess

def detect_media_type_by_extension(file_path):
    audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.opus', '.wma'}
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.webm', '.m4v', '.mpg', '.mpeg', '.ts'}
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext in audio_extensions: return "audio"
    if ext in video_extensions: return "video"
    return "unknown"

def detect_media_type(file_path):
    if not os.path.exists(file_path):
        return "unknown"
    ext_type = detect_media_type_by_extension(file_path)
    if ext_type != "unknown":
        return ext_type
    try:
        ffprobe_path = shutil.which("ffprobe")
        if not ffprobe_path: return "unknown"
        cmd = [ffprobe_path, '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', file_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if result.returncode != 0 or not result.stdout.strip(): return "unknown"
        streams = result.stdout.strip().split('\n')
        if any(s.strip() == 'video' for s in streams): return "video"
        if any(s.strip() == 'audio' for s in streams): return "audio"
        return "unknown"
    except Exception:
        return "unknown"

def get_audio_tracks_count(file_path):
    if not os.path.exists(file_path): return 0
    try:
        ffprobe_path = shutil.which("ffprobe")
        if not ffprobe_path: return 0
        cmd = [ffprobe_path, '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if result.returncode != 0: return 0
        return len([s for s in result.stdout.strip().split('\n') if s.strip()])
    except Exception:
        return 0