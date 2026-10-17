"""Shared validation helpers for the FFmpeg worker threads."""

import os
import shlex


_ALWAYS_PROTECTED_OPTIONS = {
    "-i", "-f", "-y", "-n", "-progress",
    "-map", "-map_metadata", "-map_chapters",
    "-c", "-codec", "-c:v", "-vcodec", "-c:a", "-acodec",
    "-vn", "-an", "-filter_complex", "-filter_complex_script",
}

_LOSSLESS_PROTECTED_OPTIONS = {
    "-b", "-b:v", "-b:a", "-crf", "-qp", "-q", "-qscale",
    "-lossless", "-x264-params", "-x265-params", "-sample_fmt",
    "-pix_fmt", "-ar", "-ac", "-channel_layout", "-r", "-fps_mode",
    "-vsync", "-s", "-vf", "-af", "-filter", "-filter:v", "-filter:a",
    "-filter_complex", "-t", "-to", "-ss", "-sseof",
}


def ffmpeg_missing_message():
    """Explain how to install FFmpeg on Windows when it is not on PATH."""
    return (
        "FFmpeg не найден в PATH / FFmpeg was not found in PATH.\n\n"
        "Windows: откройте PowerShell или Windows Terminal и выполните:\n"
        "winget install --id Gyan.FFmpeg --exact\n\n"
        "После установки перезапустите приложение. Если winget недоступен, "
        "скачайте сборку с https://www.gyan.dev/ffmpeg/builds/ и добавьте папку "
        "bin с ffmpeg.exe в PATH.\n\n"
        "After installation, restart the app. If winget is unavailable, download "
        "a build from https://www.gyan.dev/ffmpeg/builds/ and add the folder "
        "containing ffmpeg.exe to PATH."
    )


def ensure_safe_output_path(input_file, output_file):
    """Reject in-place conversion and invalid output directories."""
    if os.path.isdir(output_file):
        raise ValueError("Путь сохранения указывает на папку. Выберите имя выходного файла.")

    input_abs = os.path.normcase(os.path.realpath(os.path.abspath(input_file)))
    output_abs = os.path.normcase(os.path.realpath(os.path.abspath(output_file)))
    same_path = input_abs == output_abs
    if not same_path and os.path.exists(output_file):
        try:
            same_path = os.path.samefile(input_file, output_file)
        except OSError:
            pass
    if same_path:
        raise ValueError("Входной и выходной файлы совпадают. Выберите другой путь сохранения.")

    output_dir = os.path.dirname(output_abs)
    if not os.path.isdir(output_dir):
        raise ValueError(f"Папка для сохранения не существует: {output_dir}")


def parse_extra_ffmpeg_args(raw_args, *, lossless=False):
    """Parse advanced FFmpeg args while protecting worker-managed options."""
    try:
        args = shlex.split(raw_args) if raw_args else []
    except ValueError as exc:
        raise ValueError(f"Не удалось разобрать дополнительные аргументы FFmpeg: {exc}") from exc

    protected = set(_ALWAYS_PROTECTED_OPTIONS)
    if lossless:
        protected.update(_LOSSLESS_PROTECTED_OPTIONS)

    for token in args:
        if not token.startswith("-") or token == "-":
            continue
        option = token.split("=", 1)[0].lower()
        conflict = next(
            (base for base in protected if option == base or option.startswith(base + ":")),
            None,
        )
        if conflict:
            if lossless:
                raise ValueError(
                    f"Дополнительный аргумент {token} конфликтует с настройками конвертации без потерь. "
                    "Удалите его из поля аргументов FFmpeg."
                )
            raise ValueError(
                f"Дополнительный аргумент {token} конфликтует с настройками, которыми управляет приложение. "
                "Удалите его из поля аргументов FFmpeg."
            )
    return args


def pcm_encoder_for_sample_fmt(sample_fmt):
    """Return a WAV/AVI PCM encoder that preserves the decoded sample format."""
    mapping = {
        "u8": "pcm_u8", "u8p": "pcm_u8",
        "s16": "pcm_s16le", "s16p": "pcm_s16le",
        "s32": "pcm_s32le", "s32p": "pcm_s32le",
        "flt": "pcm_f32le", "fltp": "pcm_f32le",
        "dbl": "pcm_f64le", "dblp": "pcm_f64le",
    }
    return mapping.get((sample_fmt or "").strip().lower())
