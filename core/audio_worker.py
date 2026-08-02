import sys
import os
import shutil
import subprocess
import re
import shlex
from PySide6.QtCore import QThread, Signal

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
    
    def run(self):
        self.is_running = True
        self.is_stopped = False
        try:
            if not os.path.exists(self.input_file) or os.path.getsize(self.input_file) == 0:
                self.conversion_finished.emit(False, "Входной файл недоступен или пуст.")
                return
            if not shutil.which("ffmpeg"):
                self.conversion_finished.emit(False, "FFmpeg не найден в PATH")
                return
            self.get_duration()
            command = self.build_ffmpeg_command()
            self.log_update.emit(f"[COMMAND] {' '.join(command)}\n")
            
            self.process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1, universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            while self.is_running:
                if self.process is None or self.process.poll() is not None: break
                line = self.process.stderr.readline()
                if line:
                    line = line.rstrip()
                    self.log_update.emit(f"[FFMPEG] {line}\n")
                    if (progress := self.parse_progress(line)) is not None:
                        self.progress_update.emit(progress)
                self.msleep(20)
                
            if self.is_stopped:
                self.terminate_process()
                self.conversion_finished.emit(False, "Конвертация остановлена пользователем")
                return
                
            if self.process:
                self.process.communicate()
                if self.process.returncode == 0:
                    self.conversion_finished.emit(True, "Конвертация успешно завершена")
                else:
                    self.conversion_finished.emit(False, f"Ошибка FFmpeg с кодом: {self.process.returncode}")
        except Exception as e:
            self.conversion_finished.emit(False, str(e))
        finally:
            self.is_running = False
    
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
        command = ['ffmpeg', '-i', self.input_file, '-progress', 'pipe:1']
        if self.copy_metadata:
            command.extend(['-map_metadata', '0', '-metadata', 'encoding=UTF-8'])
            if self.format_ == 'mp3': command.extend(['-id3v2_version', '3'])
            if self.format_ == 'wav': command.extend(['-write_id3v1', '1', '-write_id3v2', '1'])
        command.extend(['-vn', '-c:a', self.audio_codec or 'aac'])
        
        if not self.lossless:
            command.extend(['-b:a', self.bitrate if self.bitrate else '192k'])
                
        if self.ffmpeg_args:
            command.extend(shlex.split(self.ffmpeg_args))
        command.extend(['-y', self.output_file])
        return command

    def parse_progress(self, line):
        if (m := re.search(r'out_time_ms=(\d+)', line)) and self.total_duration:
            return max(0, min(100, int((int(m.group(1)) / 1000000 / self.total_duration) * 100)))
        return None

    def terminate_process(self):
        if self.process:
            try: self.process.terminate()
            except Exception: pass
            self.process = None

    def stop(self):
        self.is_stopped = True
        self.is_running = False
        self.terminate_process()