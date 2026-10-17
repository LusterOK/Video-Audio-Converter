import sys
import os
import shutil
import subprocess
import re
import uuid
import queue
import threading
from PySide6.QtCore import QThread, Signal
from core.worker_utils import ensure_safe_output_path, parse_extra_ffmpeg_args, pcm_encoder_for_sample_fmt, ffmpeg_missing_message
from config import AUDIO_FORMATS, CODEC_INFO

class VideoConverterThread(QThread):
    status_update = Signal(str)
    progress_update = Signal(int)
    log_update = Signal(str)
    conversion_finished = Signal(bool, str)
    
    def __init__(self, input_file, output_file, format_, video_codec, audio_codec, 
                 quality, lossless, keep_all_tracks, audio_tracks_count, ffmpeg_args="", copy_metadata=True):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.format_ = format_
        self.video_codec = video_codec
        self.audio_codec = audio_codec
        self.quality = quality
        self.lossless = lossless
        self.keep_all_tracks = keep_all_tracks
        self.audio_tracks_count = audio_tracks_count
        self.ffmpeg_args = ffmpeg_args.strip()
        self.copy_metadata = copy_metadata
        self.process = None
        self.is_running = False
        self.is_stopped = False
        self.total_duration = None
        self._working_output_file = None
        self._output_committed = False
        self._cancel_event = threading.Event()
        self._terminate_lock = threading.Lock()
    
    def run(self):
        self.is_running = True
        self._output_committed = False
        try:
            if self._cancel_event.is_set():
                self.is_stopped = True
                self.conversion_finished.emit(False, "Конвертация остановлена пользователем")
                return
            if not os.path.exists(self.input_file) or os.path.getsize(self.input_file) == 0:
                self.conversion_finished.emit(False, "Входной файл недоступен или пуст.")
                return
            if not shutil.which("ffmpeg"):
                self.conversion_finished.emit(False, ffmpeg_missing_message())
                return
            if not os.path.splitext(self.output_file)[1]:
                self.output_file = f"{self.output_file}.{self.format_.lower().lstrip('.')}"
            ensure_safe_output_path(self.input_file, self.output_file)
            self.get_duration()
            output_dir = os.path.dirname(os.path.abspath(self.output_file))
            output_name, output_ext = os.path.splitext(os.path.basename(self.output_file))
            self._working_output_file = os.path.join(
                output_dir, f"{output_name}.partial-{uuid.uuid4().hex}{output_ext}"
            )
            command = self.build_ffmpeg_command()
            self.log_update.emit(f"[COMMAND] {' '.join(command)}\n")

            if self._cancel_event.is_set():
                self.is_stopped = True
                self.conversion_finished.emit(False, "Конвертация остановлена пользователем")
                return

            self.process = subprocess.Popen(
                command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                text=True, bufsize=1, universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            output_queue = queue.Queue()

            def read_stderr():
                try:
                    for stderr_line in iter(self.process.stderr.readline, ""):
                        output_queue.put(stderr_line)
                finally:
                    try:
                        self.process.stderr.close()
                    except Exception:
                        pass

            reader = threading.Thread(target=read_stderr, name="ffmpeg-stderr-reader", daemon=True)
            reader.start()
            while True:
                if self._cancel_event.is_set() and self.process.poll() is None:
                    self.terminate_process()
                try:
                    line = output_queue.get(timeout=0.05)
                except queue.Empty:
                    line = None
                if line:
                    line = line.rstrip()
                    self.log_update.emit(f"[FFMPEG] {line}\n")
                    if (progress := self.parse_progress(line)) is not None:
                        self.progress_update.emit(progress)
                if self.process.poll() is not None and not reader.is_alive() and output_queue.empty():
                    break
            reader.join(timeout=1)
            return_code = self.process.wait()

            if self._cancel_event.is_set() or self.is_stopped:
                self.conversion_finished.emit(False, "Конвертация остановлена пользователем")
                return

            if return_code == 0 and self._working_output_file and os.path.isfile(self._working_output_file) and os.path.getsize(self._working_output_file) > 0:
                os.replace(self._working_output_file, self.output_file)
                self._output_committed = True
                self.progress_update.emit(100)
                self.conversion_finished.emit(True, "Конвертация успешно завершена")
            else:
                self.conversion_finished.emit(False, f"Ошибка FFmpeg с кодом: {return_code}")
        except Exception as e:
            self.conversion_finished.emit(False, str(e))
        finally:
            if self.process and self.process.poll() is None:
                self.terminate_process()
            self.is_running = False
            if not self._output_committed and self._working_output_file:
                try:
                    if os.path.exists(self._working_output_file):
                        os.remove(self._working_output_file)
                except OSError:
                    pass

    def get_duration(self):
        try:
            ffprobe_path = shutil.which("ffprobe")
            if not ffprobe_path: return
            cmd = [ffprobe_path, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', self.input_file]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                self.total_duration = float(res.stdout.strip())
        except Exception:
            pass

    def build_ffmpeg_command(self):
        is_audio = self.format_ in AUDIO_FORMATS
        extra_args = parse_extra_ffmpeg_args(self.ffmpeg_args, lossless=self.lossless)
        command = ['ffmpeg', '-i', self.input_file, '-progress', 'pipe:2']
        command.extend(['-map_metadata', '0' if self.copy_metadata else '-1'])
        
        if self.keep_all_tracks:
            command.extend(['-map', '0:v?', '-map', '0:a?'])
        
        if is_audio:
            audio_format = os.path.splitext(self.output_file)[1].lstrip('.').lower() or self.format_.lower().lstrip('.')
            if self.lossless and audio_format not in {'flac', 'wav'}:
                raise ValueError(
                    f"Формат {audio_format.upper()} использует кодирование с потерями. "
                    "Для режима без потери качества выберите FLAC или WAV."
                )
            audio_encoder = {'flac': 'flac', 'wav': 'pcm_s16le'}.get(audio_format, self.audio_codec or 'aac')
            command.extend(['-vn', '-c:a', audio_encoder])
        else:
            v_codec = self.video_codec or 'libx264'
            command.extend(['-c:v', v_codec])

            if self.lossless:
                lossless_video_args = {
                    'libx264': ['-crf', '0'],
                    'libx265': ['-x265-params', 'lossless=1'],
                    'libvpx-vp9': ['-lossless', '1'],
                }
                if v_codec not in lossless_video_args:
                    raise ValueError(
                        f"Для видеокодека {v_codec} режим без потери качества не настроен. "
                        "Выберите libx264, libx265 или libvpx-vp9."
                    )
                command.extend(lossless_video_args[v_codec])
                # Keep the input frame timestamps exactly. FFmpeg's default
                # sync mode can duplicate/drop frames for irregular timestamps.
                command.extend(['-fps_mode', 'passthrough'])
                audio_format = os.path.splitext(self.output_file)[1].lstrip('.').lower() or self.format_.lower().lstrip('.')
                lossless_audio_by_container = {
                    'mp4': 'alac',
                    'mov': 'alac',
                    'mkv': 'flac',
                    'avi': 'pcm_s16le',
                }
                if audio_format not in lossless_audio_by_container:
                    raise ValueError(
                        f"Для контейнера {audio_format.upper()} не настроено совместимое lossless-аудио. "
                        "Выберите MP4, MOV, MKV или AVI."
                    )
                lossless_audio_encoder = lossless_audio_by_container[audio_format]
                if audio_format == 'avi':
                    sample_formats = self.get_input_audio_sample_formats()
                    if self.keep_all_tracks and sample_formats:
                        # Preserve each mapped audio stream's decoded sample precision independently.
                        for audio_index, sample_fmt in enumerate(sample_formats):
                            pcm_encoder = pcm_encoder_for_sample_fmt(sample_fmt)
                            if not pcm_encoder:
                                raise ValueError(
                                    f"Не удалось подобрать PCM-кодек для аудиодорожки {audio_index + 1} "
                                    f"с sample_fmt '{sample_fmt}'."
                                )
                            command.extend([f'-c:a:{audio_index}', pcm_encoder])
                    else:
                        sample_fmt = sample_formats[0] if sample_formats else None
                        lossless_audio_encoder = pcm_encoder_for_sample_fmt(sample_fmt) or 'pcm_s32le'
                        command.extend(['-c:a', lossless_audio_encoder])
                else:
                    command.extend(['-c:a', lossless_audio_encoder])
                # AMR-NB's decoded signal is exactly representable as 16-bit
                # PCM. A 24-bit ALAC round-trip can introduce +/-1 LSB due to
                # float-to-integer rounding; use 16-bit ALAC for AMR-NB input.
                if lossless_audio_encoder == 'alac' and self.get_input_audio_codec() == 'amr_nb':
                    command.extend(['-sample_fmt:a:0', 's16p'])
            else:
                if info := CODEC_INFO.get(v_codec):
                    command.extend([f"-{info['param']}", str(max(info['min'], min(info['max'], self.quality)))])
                else:
                    command.extend(['-crf', str(self.quality)])
                command.extend(['-c:a', self.audio_codec or 'aac'])

        command.extend(extra_args)
            
        command.extend(['-y', self._working_output_file or self.output_file])
        return command

    def get_input_audio_sample_formats(self):
        try:
            ffprobe_path = shutil.which('ffprobe')
            if not ffprobe_path:
                return []
            result = subprocess.run(
                [ffprobe_path, '-v', 'error', '-select_streams', 'a',
                 '-show_entries', 'stream=sample_fmt',
                 '-of', 'default=noprint_wrappers=1:nokey=1', self.input_file],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return [value.strip().lower() for value in result.stdout.splitlines() if value.strip()]
        except Exception:
            pass
        return []

    def get_input_audio_codec(self):
        # Detect the first audio stream codec so lossless audio can preserve
        # the decoded PCM precision where the source codec is known.
        try:
            ffprobe_path = shutil.which('ffprobe')
            if not ffprobe_path:
                return None
            result = subprocess.run(
                [ffprobe_path, '-v', 'error', '-select_streams', 'a:0',
                 '-show_entries', 'stream=codec_name',
                 '-of', 'default=noprint_wrappers=1:nokey=1', self.input_file],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().splitlines()[0].lower()
        except Exception:
            pass
        return None

    def parse_progress(self, line):
        if (m := re.search(r'out_time_(?:us|ms)=(\d+)', line)) and self.total_duration:
            return max(0, min(100, int((int(m.group(1)) / 1000000 / self.total_duration) * 100)))
        return None

    def terminate_process(self):
        with self._terminate_lock:
            process = self.process
            if process and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                except Exception:
                    try:
                        process.kill()
                        process.wait(timeout=2)
                    except Exception:
                        pass

    def stop(self):
        self.is_stopped = True
        self._cancel_event.set()
