# ═══════════════════════════════════════════════════════════════
# СЛОВАРЬ ПЕРЕВОДОВ
# ═══════════════════════════════════════════════════════════════
LANGUAGES = {
    'theme_label': {'ru': "Тема оформления", 'en': "Appearance"},
    'window_title': {'ru': "Конвертатор", 'en': "Converter"},
    'input_file_label': {'ru': "Выберите файл:", 'en': "Select File:"},
    'output_file_label': {'ru': "Сохранить как:", 'en': "Save As:"},
    'select_file_button': {'ru': "Выбрать", 'en': "Select"},
    'save_as_button': {'ru': "Сохранить как", 'en': "Save As"},
    'start_button': {'ru': "Начать конвертацию", 'en': "Start Conversion"},
    'stop_button': {'ru': "Остановить", 'en': "Stop"},
    'format_label': {'ru': "Формат выходного файла:", 'en': "Output Format:"},
    'quality_label': {'ru': "Качество:", 'en': "Quality:"},
    'lossless_checkbox': {'ru': "Без потери качества", 'en': "Lossless"},
    'status_label': {'ru': "Статус:", 'en': "Status:"},
    'video_codec_label': {'ru': "Кодек видео:", 'en': "Video Codec:"},
    'audio_codec_label': {'ru': "Кодек аудио:", 'en': "Audio Codec:"},
    'file_dialog_title': {'ru': "Открыть файл", 'en': "Open File"},
    'save_dialog_title': {'ru': "Сохранить как", 'en': "Save As"},
    'no_file_selected': {'ru': "Нет выбранного файла", 'en': "No file selected"},
    'no_output_path': {'ru': "Нет пути сохранения", 'en': "No output path"},
    'conversion_complete': {'ru': "✅ Конвертация завершена!", 'en': "✅ Conversion complete!"},
    'conversion_error': {'ru': "❌ Ошибка конвертации!", 'en': "❌ Conversion error!"},
    'clear_log': {'ru': "Очистить лог", 'en': "Clear Log"},
    'save_log': {'ru': "Сохранить лог", 'en': "Save Log"},
    'log_save_error': {'ru': "Ошибка сохранения лога", 'en': "Error saving log"},
    'media_type_video': {'ru': "Видео", 'en': "Video"},
    'media_type_audio': {'ru': "Аудио", 'en': "Audio"},
    'media_type_unknown': {'ru': "Неизвестно", 'en': "Unknown"},
    'audio_tracks_detected': {'ru': "Обнаружено аудиодорожек: ", 'en': "Audio tracks detected: "},
    'simple_mode': {'ru': "Простой режим", 'en': "Simple Mode"},
    'advanced_mode': {'ru': "Продвинутый режим", 'en': "Advanced Mode"},
    'audio_mode': {'ru': "Аудио режим", 'en': "Audio Mode"},
    'video_mode': {'ru': "Видео режим", 'en': "Video Mode"},
    'audio_bitrate_label': {'ru': "Битрейт аудио:", 'en': "Audio bitrate:"},
    'save_log_dialog_title': {'ru': "Сохранить лог FFmpeg", 'en': "Save FFmpeg Log"},
    'log_file_filter': {'ru': "Текстовые файлы (*.txt);;Все файлы (*)", 'en': "Text files (*.txt);;All files (*)"},
    'keep_all_tracks': {'ru': "Сохранить все дорожки", 'en': "Keep all tracks"},
    'copy_metadata': {'ru': "Копировать метаданные", 'en': "Copy metadata"},
    'progress_label': {'ru': "Прогресс:", 'en': "Progress:"},
    'ready_status': {'ru': "Готово к работе", 'en': "Ready"},
    'ffmpeg_args_label': {'ru': "Аргументы FFmpeg:", 'en': "FFmpeg arguments:"},
    'format_manual_placeholder': {'ru': "Формат вручную (например, mkv)", 'en': "Format manually (e.g. mkv)"},
    'log_placeholder': {'ru': "Вывод FFmpeg и диагностика конвертации", 'en': "FFmpeg output and conversion diagnostics"},
    'input_missing_error': {'ru': "Входной файл не выбран или не существует.", 'en': "Input file is not selected or does not exist."},
    'output_missing_error': {'ru': "Сначала выберите путь сохранения выходного файла.", 'en': "Please select an output file path first."},
    'format_missing_error': {'ru': "Не указан формат выходного файла.", 'en': "Output format is not specified."},
}

VIDEO_FORMATS = ['mp4', 'avi', 'mkv', 'mov', 'webm']
AUDIO_FORMATS = ['mp3', 'wav', 'flac', 'aac', 'ogg']

CODEC_INFO = {
    'libx264': {'type': 'cpu', 'param': 'crf', 'min': 0, 'max': 51, 'default': 23},
    'libx265': {'type': 'cpu', 'param': 'crf', 'min': 0, 'max': 51, 'default': 28},
    'h264_nvenc': {'type': 'gpu', 'param': 'cq', 'min': 0, 'max': 51, 'default': 23},
    'h264_amf': {'type': 'gpu', 'param': 'cq', 'min': 0, 'max': 51, 'default': 23},
    'h264_qsv': {'type': 'gpu', 'param': 'cq', 'min': 0, 'max': 51, 'default': 23},
    'hevc_nvenc': {'type': 'gpu', 'param': 'cq', 'min': 0, 'max': 51, 'default': 28},
    'libvpx-vp9': {'type': 'cpu', 'param': 'crf', 'min': 0, 'max': 63, 'default': 30},
    'mpeg4': {'type': 'cpu', 'param': 'qscale', 'min': 1, 'max': 31, 'default': 5},
}

AUDIO_CODEC_INFO = {
    'aac': {'default_bitrate': '192k', 'lossless': False},
    'mp3': {'default_bitrate': '192k', 'lossless': False},
    'flac': {'default_bitrate': None, 'lossless': True},
    'ogg': {'default_bitrate': '192k', 'lossless': False},
    'wav': {'default_bitrate': None, 'lossless': True},
}

CODECS = list(CODEC_INFO.keys())
AUDIO_CODECS = list(AUDIO_CODEC_INFO.keys())