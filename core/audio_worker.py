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

class AudioConverterThread(QThread):
    status_update = Signal(str)
    progress_update = Signal(int)
    log_update = Signal(str)
    conversion_finished = Signal(bool, str)
    
    def __init__(self, input_file, output_file, format_, audio_codec, 
                 bitrate, quality, lossless, copy_metadata=True, ffmpeg_args=""):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.format_ = format_
        self.audio_codec = audio_codec
        self.bitrate = bitrate
        self.quality = quality
        self.lossless = lossless
        self.copy_metadata = copy_metadata
        self.ffmpeg_args = ffmpeg_args.strip()
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
            if getattr(self, "codec_warning", None):
                self.log_update.emit(f"[WARNING] {self.codec_warning}\n")
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
        # The output container determines which audio encoders are valid.
        format_name = os.path.splitext(self.output_file)[1].lstrip('.').lower() or self.format_.lower().lstrip('.')
        encoder_by_format = {
            'mp3': 'libmp3lame',
            'wav': 'pcm_s16le',
            'flac': 'flac',
            'aac': 'aac',
            'ogg': 'libvorbis',
        }
        aliases = {
            'mp3': {'mp3', 'libmp3lame'},
            'wav': {'wav', 'pcm_s16le'},
            'flac': {'flac'},
            'aac': {'aac'},
            'ogg': {'ogg', 'vorbis', 'libvorbis'},
        }
        expected_encoder = encoder_by_format.get(format_name)
        if self.lossless and format_name not in {'flac', 'wav'}:
            raise ValueError(
                f"Формат {format_name.upper()} использует кодирование с потерями. "
                "Для режима без потери качества выберите FLAC или WAV."
            )
        requested_codec = (self.audio_codec or '').strip().lower()
        if expected_encoder and requested_codec not in aliases[format_name]:
            self.codec_warning = (
                f"Кодек '{self.audio_codec}' несовместим с форматом {format_name.upper()}; "
                f"используется совместимый кодек {expected_encoder}."
            )
            effective_codec = expected_encoder
        else:
            self.codec_warning = None
            effective_codec = expected_encoder or self.audio_codec or 'aac'

        extra_args = parse_extra_ffmpeg_args(self.ffmpeg_args, lossless=self.lossless)
        command = ['ffmpeg', '-i', self.input_file, '-progress', 'pipe:2']
        command.extend(['-map_metadata', '0' if self.copy_metadata else '-1'])
        if self.copy_metadata:
            command.extend(['-metadata', 'encoding=UTF-8'])
            if format_name == 'mp3':
                command.extend(['-id3v2_version', '3'])
            if format_name == 'wav':
                command.extend(['-write_id3v1', '1', '-write_id3v2', '1'])
        if self.lossless and format_name == 'wav':
            sample_fmt = self.get_input_audio_sample_fmt()
            lossless_wav_encoder = pcm_encoder_for_sample_fmt(sample_fmt)
            if not lossless_wav_encoder:
                raise ValueError(
                    f"Не удалось подобрать WAV-кодек без потери точности для исходного sample_fmt '{sample_fmt or 'unknown'}'."
                )
            effective_codec = lossless_wav_encoder
        command.extend(['-vn', '-c:a', effective_codec])

        if not self.lossless and format_name in {'mp3', 'aac', 'ogg'}:
            command.extend(['-b:a', self.bitrate if self.bitrate else '192k'])

        command.extend(extra_args)
        command.extend(['-y', self._working_output_file or self.output_file])
        return command

    def get_input_audio_sample_fmt(self):
        try:
            ffprobe_path = shutil.which('ffprobe')
            if not ffprobe_path:
                return None
            result = subprocess.run(
                [ffprobe_path, '-v', 'error', '-select_streams', 'a:0',
                 '-show_entries', 'stream=sample_fmt',
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
