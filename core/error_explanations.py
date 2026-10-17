"""Human-readable explanations for common FFmpeg conversion failures.

The raw FFmpeg output is deliberately preserved in the application log; this
module only produces a concise, localized summary for the error dialog.
"""
import re


def explain_ffmpeg_error(log_text, error_message="", language="ru"):
    """Return a concise explanation based on FFmpeg's diagnostic output."""
    text = f"{log_text or ''}\n{error_message or ''}"
    low = text.lower()
    ru = (language or "ru").lower().startswith("ru")

    # Capture the specific codec name from FFmpeg's own diagnostic.
    match = re.search(r"unknown encoder\s+['\"]?([^'\"\s]+)", text, re.IGNORECASE)
    if match:
        codec = match.group(1).rstrip(".,:;")
        return (
            f"FFmpeg не знает кодек «{codec}». Проверьте название кодека и доступность нужного энкодера."
            if ru else
            f"FFmpeg does not recognize the codec '{codec}'. Check the codec name and whether that encoder is available."
        )

    match = re.search(r"unknown decoder\s+['\"]?([^'\"\s]+)", text, re.IGNORECASE)
    if match:
        codec = match.group(1).rstrip(".,:;")
        return (
            f"FFmpeg не знает декодер «{codec}». Проверьте формат входного файла и сборку FFmpeg."
            if ru else
            f"FFmpeg does not recognize the decoder '{codec}'. Check the input format and FFmpeg build."
        )

    if ("для режима без потери качества выберите flac или wav" in low or
            "lossless mode requires flac or wav" in low):
        return (
            "Аудио без потерь нельзя сохранить в OGG, MP3 или AAC. Выберите FLAC или WAV."
            if ru else
            "Lossless audio cannot be saved as OGG, MP3, or AAC. Choose FLAC or WAV."
        )

    rules = [
        (("no such file or directory", "could not open input", "error opening input"),
         "Не удалось найти или открыть входной файл. Проверьте путь и убедитесь, что файл существует.",
         "The input file could not be found or opened. Check the path and make sure the file exists."),
        (("permission denied", "access is denied"),
         "Нет доступа к файлу или папке назначения. Проверьте разрешения и не открыт ли файл другой программой.",
         "Access to the file or output folder was denied. Check permissions and whether another app is using the file."),
        (("no space left on device", "not enough space"),
         "Недостаточно свободного места на диске назначения.",
         "There is not enough free space on the destination drive."),
        (("unknown format", "unable to find a suitable output format", "invalid output format"),
         "FFmpeg не распознал формат выходного файла. Проверьте расширение и выбранный формат.",
         "FFmpeg could not identify the output format. Check the file extension and selected format."),
        (("invalid data found when processing input", "could not find codec parameters", "moov atom not found"),
         "Входной файл повреждён, неполный или имеет неподдерживаемый формат.",
         "The input file may be damaged, incomplete, or in an unsupported format."),
        (("error initializing output stream", "error while opening encoder", "error selecting an encoder"),
         "Не удалось запустить кодирование. Проверьте совместимость кодека с форматом и параметрами.",
         "The encoder could not be initialized. Check codec compatibility with the output format and settings."),
        (("bitrate not specified",),
         "Для выбранного аудиокодека требуется указать битрейт или выбрать подходящий кодек.",
         "The selected audio codec requires a bitrate or a different codec."),
        (("width not divisible by 2", "height not divisible by 2", "height not divisible by 2"),
         "Размеры видео не подходят выбранному кодеку. Попробуйте другой кодек или размеры кадра.",
         "The video dimensions are incompatible with the selected codec. Try another codec or frame size."),
        (("file already exists", "already exists. overwrite", "not overwriting"),
         "Выходной файл уже существует и не может быть перезаписан. Выберите другое имя или удалите старый файл.",
         "The output file already exists and cannot be overwritten. Choose another name or remove the existing file."),
        (("invalid argument",),
         "FFmpeg получил неподдерживаемый или несовместимый параметр. Проверьте кодек, формат и дополнительные аргументы.",
         "FFmpeg received an unsupported or incompatible argument. Check the codec, format, and extra arguments."),
        (("unknown encoder", "unknown decoder", "encoder not found", "decoder not found"),
         "Не найден подходящий кодек. Проверьте его название и поддержку в вашей сборке FFmpeg.",
         "A required codec was not found. Check its name and support in your FFmpeg build."),
        (("conversion failed",),
         "FFmpeg завершил конвертацию с ошибкой. Откройте подробности ниже или посмотрите журнал FFmpeg.",
         "FFmpeg reported that conversion failed. Expand the details below or inspect the FFmpeg log."),
    ]
    for needles, ru_text, en_text in rules:
        if any(needle in low for needle in needles):
            return ru_text if ru else en_text

    return (
        "FFmpeg не смог завершить конвертацию. Подробная причина приведена в журнале; проверьте параметры и входной файл."
        if ru else
        "FFmpeg could not complete the conversion. See the log for details and check the settings and input file."
    )
