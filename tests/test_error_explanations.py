import unittest
from core.error_explanations import explain_ffmpeg_error


class ErrorExplanationTests(unittest.TestCase):
    def test_unknown_encoder_includes_codec_name(self):
        result = explain_ffmpeg_error(
            "[FFMPEG] Unknown encoder 'yadolbaeb'\n[FFMPEG] Error opening output files: Encoder not found",
            "Ошибка FFmpeg с кодом: 3165764104",
            "ru",
        )
        self.assertIn("yadolbaeb", result)
        self.assertIn("кодек", result)

    def test_permission_error(self):
        self.assertIn("Нет доступа", explain_ffmpeg_error("Permission denied", "", "ru"))

    def test_disk_full_error(self):
        self.assertIn("Недостаточно свободного места", explain_ffmpeg_error("No space left on device", "", "ru"))

    def test_invalid_argument_english(self):
        self.assertIn("incompatible argument", explain_ffmpeg_error("Invalid argument", "", "en"))

    def test_lossless_audio_rejects_lossy_container_with_clear_message(self):
        result = explain_ffmpeg_error(
            "",
            "Формат OGG использует кодирование с потерями. Для режима без потери качества выберите FLAC или WAV.",
            "ru",
        )
        self.assertIn("нельзя сохранить в OGG", result)
        self.assertIn("FLAC или WAV", result)

    def test_unknown_error_falls_back_to_general_message(self):
        self.assertIn("журнале", explain_ffmpeg_error("", "Ошибка FFmpeg с кодом: 999", "ru"))


if __name__ == "__main__":
    unittest.main()
