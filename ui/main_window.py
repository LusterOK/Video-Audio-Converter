import os
from PySide6.QtWidgets import (
    QMainWindow, QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget, 
    QFileDialog, QSlider, QHBoxLayout, QLineEdit, QCheckBox, QStatusBar, 
    QMessageBox, QProgressBar, QTextEdit, QFrame, QRadioButton, QGroupBox, QButtonGroup
)
from PySide6.QtCore import Qt, QSettings, QDateTime

from config import LANGUAGES, VIDEO_FORMATS, AUDIO_FORMATS, CODECS, AUDIO_CODECS, CODEC_INFO
from core.utils import detect_media_type, get_audio_tracks_count
from core.audio_worker import AudioConverterThread
from core.video_worker import VideoConverterThread

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("VideoConverter", "Settings")
        
        self.current_language = self.settings.value("language", "ru")
        self.last_input_path = self.settings.value("last_input_path", "")
        self.last_output_path = self.settings.value("last_output_path", "")
        self.last_quality = int(self.settings.value("last_quality", 23))
        self.last_lossless = self.settings.value("last_lossless", "false") == "true"
        self.last_keep_all_tracks = self.settings.value("last_keep_all_tracks", "true") == "true"
        self.last_mode = self.settings.value("mode", "simple")
        self.last_conversion_mode = self.settings.value("conversion_mode", "video")
        
        self.converter_thread = None
        self.input_media_type = "unknown"
        self.audio_tracks_count = 0
        self.current_mode = self.last_mode
        self.conversion_mode = self.last_conversion_mode
        
        self.resize(850, 980)
        self.setMinimumSize(750, 800)

        self.create_ui_elements()
        self.connect_signals()
        self.load_saved_settings()
        self.update_ui_language(self.current_language)
        self.update_mode_ui()
        self.update_conversion_mode_ui()

    def create_ui_elements(self):
        self.control_panel = QWidget()
        control_layout = QVBoxLayout(self.control_panel)
        control_layout.setSpacing(8)
        
        top_layout = QHBoxLayout()
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Русский", "English"])
        top_layout.addWidget(self.language_combo)
        top_layout.addStretch()
        control_layout.addLayout(top_layout)
        
        mode_switcher_layout = QHBoxLayout()
        self.mode_switcher_label = QLabel()
        mode_switcher_layout.addWidget(self.mode_switcher_label)
        
        self.video_mode_radio = QRadioButton()
        self.video_mode_radio.setChecked(True)
        mode_switcher_layout.addWidget(self.video_mode_radio)
        
        self.audio_mode_radio = QRadioButton()
        mode_switcher_layout.addWidget(self.audio_mode_radio)
        mode_switcher_layout.addStretch()
        control_layout.addLayout(mode_switcher_layout)
        
        mode_layout = QHBoxLayout()
        self.mode_label = QLabel()
        mode_layout.addWidget(self.mode_label)
        
        self.simple_mode_radio = QRadioButton()
        self.simple_mode_radio.setChecked(True)
        mode_layout.addWidget(self.simple_mode_radio)
        
        self.advanced_mode_radio = QRadioButton()
        mode_layout.addWidget(self.advanced_mode_radio)
        mode_layout.addStretch()
        control_layout.addLayout(mode_layout)
        
        input_layout = QHBoxLayout()
        self.input_file_label = QLabel()
        self.select_file_button = QPushButton()
        input_layout.addWidget(self.input_file_label)
        input_layout.addWidget(self.select_file_button)
        control_layout.addLayout(input_layout)
        
        file_info_layout = QHBoxLayout()
        self.selected_file_label = QLabel()
        self.selected_file_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        self.media_type_label = QLabel()
        self.media_type_label.setStyleSheet("font-weight: bold; color: #666; padding-left: 10px;")
        file_info_layout.addWidget(self.selected_file_label)
        file_info_layout.addWidget(self.media_type_label)
        file_info_layout.addStretch()
        control_layout.addLayout(file_info_layout)
        
        tracks_layout = QHBoxLayout()
        self.audio_tracks_label = QLabel()
        self.audio_tracks_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        tracks_layout.addWidget(self.audio_tracks_label)
        tracks_layout.addStretch()
        control_layout.addLayout(tracks_layout)
        
        output_layout = QHBoxLayout()
        self.output_file_label = QLabel()
        self.save_as_button = QPushButton()
        output_layout.addWidget(self.output_file_label)
        output_layout.addWidget(self.save_as_button)
        control_layout.addLayout(output_layout)
        
        self.output_path_label = QLabel()
        self.output_path_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        control_layout.addWidget(self.output_path_label)
        
        format_layout = QHBoxLayout()
        self.format_label = QLabel()
        self.format_combo = QComboBox()
        self.format_combo.addItems(VIDEO_FORMATS)
        
        self.format_line_edit = QLineEdit()
        self.format_line_edit.setVisible(False)
        
        format_layout.addWidget(self.format_label)
        format_layout.addWidget(self.format_combo)
        format_layout.addWidget(self.format_line_edit)
        control_layout.addLayout(format_layout)
        
        # Настройки видео
        self.video_settings_group = QGroupBox()
        video_settings_layout = QVBoxLayout(self.video_settings_group)
        
        quality_layout = QHBoxLayout()
        self.quality_label = QLabel()
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(0, 51)
        self.quality_slider.setValue(23)
        self.quality_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.current_quality_label = QLabel(str(self.quality_slider.value()))
        quality_layout.addWidget(self.quality_label)
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.current_quality_label)
        video_settings_layout.addLayout(quality_layout)
        
        self.lossless_checkbox = QCheckBox()
        video_settings_layout.addWidget(self.lossless_checkbox)
        
        self.keep_all_tracks_checkbox = QCheckBox("Сохранить все дорожки")
        video_settings_layout.addWidget(self.keep_all_tracks_checkbox)
        
        self.copy_metadata_checkbox = QCheckBox("Копировать метаданные")
        self.copy_metadata_checkbox.setChecked(True)
        video_settings_layout.addWidget(self.copy_metadata_checkbox)
        
        codec_layout = QHBoxLayout()
        self.video_codec_label = QLabel()
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(CODECS)
        self.codec_line_edit = QLineEdit("libx264")
        codec_layout.addWidget(self.video_codec_label)
        codec_layout.addWidget(self.codec_combo)
        codec_layout.addWidget(self.codec_line_edit)
        video_settings_layout.addLayout(codec_layout)
        
        audio_codec_layout = QHBoxLayout()
        self.audio_codec_label = QLabel()
        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.addItems(AUDIO_CODECS)
        self.audio_codec_line_edit = QLineEdit("aac")
        audio_codec_layout.addWidget(self.audio_codec_label)
        audio_codec_layout.addWidget(self.audio_codec_combo)
        audio_codec_layout.addWidget(self.audio_codec_line_edit)
        video_settings_layout.addLayout(audio_codec_layout)
        
        control_layout.addWidget(self.video_settings_group)
        
        # Настройки аудио
        self.audio_settings_group = QGroupBox()
        audio_settings_layout = QVBoxLayout(self.audio_settings_group)
        
        audio_only_codec_layout = QHBoxLayout()
        self.audio_only_codec_label = QLabel()
        self.audio_only_codec_combo = QComboBox()
        self.audio_only_codec_combo.addItems(AUDIO_CODECS)
        self.audio_only_codec_line_edit = QLineEdit("aac")
        audio_only_codec_layout.addWidget(self.audio_only_codec_label)
        audio_only_codec_layout.addWidget(self.audio_only_codec_combo)
        audio_only_codec_layout.addWidget(self.audio_only_codec_line_edit)
        audio_settings_layout.addLayout(audio_only_codec_layout)
        
        bitrate_layout = QHBoxLayout()
        self.audio_bitrate_label = QLabel()
        self.audio_bitrate_edit = QLineEdit("192k")
        bitrate_layout.addWidget(self.audio_bitrate_label)
        bitrate_layout.addWidget(self.audio_bitrate_edit)
        audio_settings_layout.addLayout(bitrate_layout)
        
        self.audio_lossless_checkbox = QCheckBox()
        audio_settings_layout.addWidget(self.audio_lossless_checkbox)
        
        self.audio_copy_metadata_checkbox = QCheckBox("Копировать метаданные")
        self.audio_copy_metadata_checkbox.setChecked(True)
        audio_settings_layout.addWidget(self.audio_copy_metadata_checkbox)
        
        control_layout.addWidget(self.audio_settings_group)
        
        ffmpeg_args_layout = QVBoxLayout()
        self.ffmpeg_args_label = QLabel("Аргументы FFmpeg:")
        ffmpeg_args_layout.addWidget(self.ffmpeg_args_label)
        
        self.ffmpeg_args_edit = QTextEdit()
        self.ffmpeg_args_edit.setMaximumHeight(60)
        ffmpeg_args_layout.addWidget(self.ffmpeg_args_edit)
        control_layout.addLayout(ffmpeg_args_layout)
        
        progress_layout = QHBoxLayout()
        self.progress_label = QLabel("Прогресс:")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        control_layout.addLayout(progress_layout)
        
        buttons_layout = QHBoxLayout()
        self.start_button = QPushButton()
        self.clear_log_button = QPushButton()
        self.save_log_button = QPushButton()
        
        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.clear_log_button)
        buttons_layout.addWidget(self.save_log_button)
        control_layout.addLayout(buttons_layout)
        
        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.control_panel)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        self.main_layout.addWidget(separator)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.main_layout.addWidget(self.log_text)
        
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_widget.setLayout(self.main_layout)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def connect_signals(self):
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        self.select_file_button.clicked.connect(self.open_file_dialog)
        self.save_as_button.clicked.connect(self.open_save_as_dialog)
        self.start_button.clicked.connect(self.start_conversion)
        self.clear_log_button.clicked.connect(self.clear_log)
        self.save_log_button.clicked.connect(self.save_log_to_file)
        self.quality_slider.valueChanged.connect(self.update_quality_display)
        self.format_combo.currentIndexChanged.connect(self.on_format_changed)
        self.codec_combo.currentIndexChanged.connect(self.on_codec_changed)
        
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.simple_mode_radio)
        self.mode_group.addButton(self.advanced_mode_radio)
        self.mode_group.buttonClicked.connect(self.on_mode_changed)
        
        self.conversion_group = QButtonGroup(self)
        self.conversion_group.addButton(self.video_mode_radio)
        self.conversion_group.addButton(self.audio_mode_radio)
        self.conversion_group.buttonClicked.connect(self.on_conversion_mode_changed)

    def update_ui_language(self, lang):
        self.current_language = lang
        self.setWindowTitle(LANGUAGES['window_title'][lang])
        self.input_file_label.setText(LANGUAGES['input_file_label'][lang])
        self.output_file_label.setText(LANGUAGES['output_file_label'][lang])
        self.select_file_button.setText(LANGUAGES['select_file_button'][lang])
        self.save_as_button.setText(LANGUAGES['save_as_button'][lang])
        self.start_button.setText(LANGUAGES['start_button'][lang])
        self.clear_log_button.setText(LANGUAGES['clear_log'][lang])
        self.save_log_button.setText(LANGUAGES['save_log'][lang])
        self.format_label.setText(LANGUAGES['format_label'][lang])
        self.quality_label.setText(LANGUAGES['quality_label'][lang])
        self.lossless_checkbox.setText(LANGUAGES['lossless_checkbox'][lang])
        self.audio_lossless_checkbox.setText(LANGUAGES['lossless_checkbox'][lang])
        self.video_codec_label.setText(LANGUAGES['video_codec_label'][lang])
        self.audio_codec_label.setText(LANGUAGES['audio_codec_label'][lang])
        self.audio_only_codec_label.setText(LANGUAGES['audio_codec_label'][lang])
        self.audio_bitrate_label.setText(LANGUAGES['audio_bitrate_label'][lang])
        
        self.mode_switcher_label.setText(LANGUAGES['status_label'][lang])
        self.video_mode_radio.setText(LANGUAGES['video_mode'][lang])
        self.audio_mode_radio.setText(LANGUAGES['audio_mode'][lang])
        
        self.mode_label.setText(LANGUAGES['status_label'][lang])
        self.simple_mode_radio.setText(LANGUAGES['simple_mode'][lang])
        self.advanced_mode_radio.setText(LANGUAGES['advanced_mode'][lang])
        
        self.video_settings_group.setTitle(LANGUAGES['video_mode'][lang])
        self.audio_settings_group.setTitle(LANGUAGES['audio_mode'][lang])

        if not self.selected_file_label.text():
            self.selected_file_label.setText(LANGUAGES['no_file_selected'][lang])
        if not self.output_path_label.text():
            self.output_path_label.setText(LANGUAGES['no_output_path'][lang])

    def save_log_to_file(self):
        lang = self.get_current_language()
        if not (log_content := self.log_text.toPlainText().strip()): return
        file_path, _ = QFileDialog.getSaveFileName(
            self, LANGUAGES['save_log_dialog_title'][lang],
            f"ffmpeg_log_{QDateTime.currentDateTime().toString('yyyyMMdd_hhmmss')}.txt",
            LANGUAGES['log_file_filter'][lang]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f: f.write(log_content)
            except Exception as e:
                QMessageBox.critical(self, LANGUAGES['log_save_error'][lang], str(e))

    def on_mode_changed(self, button):
        self.current_mode = "simple" if button == self.simple_mode_radio else "advanced"
        self.update_mode_ui()
        self.save_settings()

    def on_conversion_mode_changed(self, button=None):
        self.conversion_mode = "video" if self.video_mode_radio.isChecked() else "audio"
        self.update_conversion_mode_ui()
        self.save_settings()

    def update_mode_ui(self):
        is_simple = (self.current_mode == "simple")
        self.codec_line_edit.setVisible(not is_simple)
        self.codec_combo.setVisible(is_simple)
        self.audio_codec_line_edit.setVisible(not is_simple)
        self.audio_codec_combo.setVisible(is_simple)
        self.audio_only_codec_line_edit.setVisible(not is_simple)
        self.audio_only_codec_combo.setVisible(is_simple)
        self.format_line_edit.setVisible(not is_simple)
        self.format_combo.setVisible(is_simple)
        self.ffmpeg_args_label.setVisible(not is_simple)
        self.ffmpeg_args_edit.setVisible(not is_simple)
    
    def update_conversion_mode_ui(self):
        is_video = (self.conversion_mode == "video")
        self.video_settings_group.setVisible(is_video)
        self.audio_settings_group.setVisible(not is_video)
        
        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        self.format_combo.addItems(VIDEO_FORMATS if is_video else AUDIO_FORMATS)
        self.format_combo.blockSignals(False)
        self.on_format_changed()

    def on_format_changed(self):
        format_name = self.get_current_format()
        current_path = self.output_path_label.text()
        if current_path and current_path not in ["Нет пути сохранения", "No output path"]:
            base = os.path.splitext(current_path)[0]
            self.output_path_label.setText(f"{base}.{format_name}")
        self.save_settings()

    def get_current_format(self):
        if self.current_mode == "advanced" and (manual := self.format_line_edit.text().strip()):
            return manual
        return self.format_combo.currentText()

    def on_codec_changed(self):
        codec = self.get_video_codec()
        if codec in CODEC_INFO:
            info = CODEC_INFO[codec]
            self.quality_slider.setRange(info['min'], info['max'])
        self.update_quality_display()

    def load_saved_settings(self):
        self.language_combo.setCurrentIndex(0 if self.current_language == "ru" else 1)
        self.video_mode_radio.setChecked(self.last_conversion_mode == "video")
        self.audio_mode_radio.setChecked(self.last_conversion_mode == "audio")
        self.simple_mode_radio.setChecked(self.last_mode == "simple")
        self.advanced_mode_radio.setChecked(self.last_mode == "advanced")
        
        if self.last_input_path and os.path.exists(self.last_input_path):
            self.selected_file_label.setText(self.last_input_path)
            self.detect_and_display_media_type(self.last_input_path)
            self.detect_and_display_audio_tracks(self.last_input_path)
            
        if self.last_output_path:
            self.output_path_label.setText(self.last_output_path)
            
        self.quality_slider.setValue(self.last_quality)
        self.lossless_checkbox.setChecked(self.last_lossless)
        self.keep_all_tracks_checkbox.setChecked(self.last_keep_all_tracks)

    def save_settings(self):
        self.settings.setValue("language", "ru" if self.language_combo.currentIndex() == 0 else "en")
        self.settings.setValue("mode", self.current_mode)
        self.settings.setValue("conversion_mode", self.conversion_mode)
        self.settings.setValue("last_input_path", self.selected_file_label.text())
        self.settings.setValue("last_output_path", self.output_path_label.text())
        self.settings.setValue("last_format", self.get_current_format())
        self.settings.setValue("last_quality", self.quality_slider.value())
        self.settings.setValue("last_lossless", self.lossless_checkbox.isChecked())
        self.settings.setValue("last_keep_all_tracks", self.keep_all_tracks_checkbox.isChecked())
        self.settings.sync()

    def on_language_changed(self, index):
        self.update_ui_language("ru" if index == 0 else "en")
        self.save_settings()

    def get_current_language(self):
        return self.current_language

    def detect_and_display_media_type(self, file_path):
        self.input_media_type = detect_media_type(file_path)
        lang = self.get_current_language()
        t_str = LANGUAGES.get(f"media_type_{self.input_media_type}", {}).get(lang, "???")
        self.media_type_label.setText(f"[{t_str}]")

    def detect_and_display_audio_tracks(self, file_path):
        self.audio_tracks_count = get_audio_tracks_count(file_path)
        lang = self.get_current_language()
        self.audio_tracks_label.setText(f"{LANGUAGES['audio_tracks_detected'][lang]} {self.audio_tracks_count}")

    def open_file_dialog(self):
        lang = self.get_current_language()
        file_path, _ = QFileDialog.getOpenFileName(self, LANGUAGES['file_dialog_title'][lang], "", "All Files (*)")
        if file_path:
            self.selected_file_label.setText(file_path)
            self.detect_and_display_media_type(file_path)
            self.detect_and_display_audio_tracks(file_path)
            if self.input_media_type == "audio":
                self.audio_mode_radio.setChecked(True)
                self.on_conversion_mode_changed()
            self.save_settings()

    def open_save_as_dialog(self):
        lang = self.get_current_language()
        file_path, _ = QFileDialog.getSaveFileName(self, LANGUAGES['save_dialog_title'][lang], "", "All Files (*)")
        if file_path:
            self.output_path_label.setText(file_path)
            self.save_settings()

    def clear_log(self):
        self.log_text.clear()

    def update_quality_display(self, value=None):
        val = value if value is not None else self.quality_slider.value()
        self.current_quality_label.setText(str(val))
        self.save_settings()

    def get_video_codec(self):
        return self.codec_line_edit.text().strip() if self.current_mode == "advanced" else self.codec_combo.currentText()

    def get_audio_codec(self):
        return self.audio_codec_line_edit.text().strip() if self.current_mode == "advanced" else self.audio_codec_combo.currentText()

    def get_audio_only_codec(self):
        return self.audio_only_codec_line_edit.text().strip() if self.current_mode == "advanced" else self.audio_only_codec_combo.currentText()

    def start_conversion(self):
        if self.converter_thread and self.converter_thread.is_running:
            self.converter_thread.stop()
            return

        input_file = self.selected_file_label.text()
        output_file = self.output_path_label.text()
        
        if not os.path.exists(input_file):
            QMessageBox.critical(self, "Ошибка", "Входной файл не выбран или не существует.")
            return

        format_ = self.get_current_format()
        ffmpeg_args = self.ffmpeg_args_edit.toPlainText().strip() if self.current_mode == "advanced" else ""

        if self.conversion_mode == "audio":
            self.converter_thread = AudioConverterThread(
                input_file, output_file, format_, self.get_audio_only_codec(),
                self.audio_bitrate_edit.text().strip(), 0, self.audio_lossless_checkbox.isChecked(),
                self.audio_copy_metadata_checkbox.isChecked(), ffmpeg_args
            )
        else:
            self.converter_thread = VideoConverterThread(
                input_file, output_file, format_, self.get_video_codec(),
                self.get_audio_codec(), self.quality_slider.value(), self.lossless_checkbox.isChecked(),
                self.keep_all_tracks_checkbox.isChecked(), self.audio_tracks_count, ffmpeg_args
            )

        self.converter_thread.progress_update.connect(self.progress_bar.setValue)
        self.converter_thread.log_update.connect(self.log_text.append)
        self.converter_thread.conversion_finished.connect(self.on_conversion_finished)
        self.converter_thread.start()
        self.start_button.setText(LANGUAGES['stop_button'][self.get_current_language()])

    def on_conversion_finished(self, success, message):
        lang = self.get_current_language()
        self.start_button.setText(LANGUAGES['start_button'][lang])
        if success:
            QMessageBox.information(self, LANGUAGES['conversion_complete'][lang], message)
        else:
            QMessageBox.critical(self, LANGUAGES['conversion_error'][lang], message)

    def closeEvent(self, event):
        self.save_settings()
        if self.converter_thread and self.converter_thread.is_running:
            self.converter_thread.stop()
            self.converter_thread.wait()
        event.accept()