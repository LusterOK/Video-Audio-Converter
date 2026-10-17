import os
import sys
import re
import time
from PySide6.QtWidgets import (
    QMainWindow, QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget, 
    QFileDialog, QSlider, QHBoxLayout, QLineEdit, QCheckBox, QStatusBar, 
    QMessageBox, QProgressBar, QTextEdit, QFrame, QRadioButton, QGroupBox, QButtonGroup,
    QScrollArea, QSplitter, QGraphicsOpacityEffect, QDialog, QDialogButtonBox
)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QSettings, QDateTime, QPropertyAnimation, QEasingCurve, QTimer, Signal

from config import LANGUAGES, VIDEO_FORMATS, AUDIO_FORMATS, CODECS, AUDIO_CODECS, CODEC_INFO
from core.utils import detect_media_type, get_audio_tracks_count
from core.audio_worker import AudioConverterThread
from core.video_worker import VideoConverterThread
from core.error_explanations import explain_ffmpeg_error

def resource_path(relative_path):
    """Resolve bundled assets both from source and from a PyInstaller one-file build."""
    bundle_root = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(bundle_root, relative_path)


class ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("VideoConverter", "Settings")
        icon_path = resource_path("icon.ico")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.current_language = self.settings.value("language", "ru")
        self.last_input_path = self.settings.value("last_input_path", "")
        self.last_output_path = self.settings.value("last_output_path", "")
        self.last_quality = int(self.settings.value("last_quality", 23))
        self.last_lossless = self._setting_to_bool(self.settings.value("last_lossless", False), False)
        self.last_keep_all_tracks = self._setting_to_bool(self.settings.value("last_keep_all_tracks", True), True)
        self.last_mode = self.settings.value("mode", "simple")
        self.last_conversion_mode = self.settings.value("conversion_mode", "video")
        self.current_theme = self.settings.value("theme", "dark")
        
        self.converter_thread = None
        self.conversion_started_at = None
        self.latest_ffmpeg_speed = ""
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(1000)
        self.progress_timer.timeout.connect(self.update_progress_details)
        self.input_media_type = "unknown"
        self.audio_tracks_count = 0
        self.current_mode = self.last_mode
        self.conversion_mode = self.last_conversion_mode
        
        self.resize(1180, 820)
        # The two-column workspace needs enough width for both panels and their
        # controls. Avoid allowing the splitter to squeeze either side until
        # labels, codecs, or buttons appear clipped.
        self.setMinimumSize(1000, 650)
        self.create_ui_elements()
        self.connect_signals()
        self.load_saved_settings()
        self.update_ui_language(self.current_language)
        self.update_mode_ui()
        self.update_conversion_mode_ui()
        self.apply_theme(self.current_theme)
        self.update_output_summary()

    @staticmethod
    def _setting_to_bool(value, default=False):
        """Normalize QSettings values regardless of whether Qt returns bool, int, or text."""
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        if value is None:
            return default
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off", ""}:
            return False
        return default

    @staticmethod
    def _theme_stylesheet(theme):
        """Return a complete application palette for Light, Dark and true AMOLED themes."""
        palettes = {
            "light": {"bg":"#f8f4f8", "surface":"#ffffff", "surface2":"#f2eaf3", "input":"#fffaff", "text":"#302638", "muted":"#766779", "border":"#ead9e9", "accent":"#d92d91", "accent_hover":"#c21f7d", "accent_soft":"#fbe1f0", "selection":"#f3b8da", "log":"#fffaff"},
            "dark": {"bg":"#17151b", "surface":"#211d27", "surface2":"#2b2432", "input":"#19161e", "text":"#f5edf7", "muted":"#b5a6bb", "border":"#403747", "accent":"#a66af5", "accent_hover":"#b883ff", "accent_soft":"#382849", "selection":"#7650a8", "log":"#17141b"},
            "amoled": {"bg":"#000000", "surface":"#080808", "surface2":"#111111", "input":"#050505", "text":"#f5f5f7", "muted":"#a2a2aa", "border":"#292929", "accent":"#bb78ff", "accent_hover":"#ca99ff", "accent_soft":"#21132f", "selection":"#7040a0", "log":"#000000"},
        }
        c = palettes.get(theme, palettes["dark"])
        return f"""
        QMainWindow, QWidget {{ background: {c['bg']}; color: {c['text']}; font-size: 10pt; }}
        QToolTip {{ background: {c['surface2']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 6px 8px; border-radius: 6px; }}
        QLabel {{ background: transparent; color: {c['muted']}; }}
        QGroupBox {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 15px; margin-top: 0px; padding: 34px 14px 13px; font-weight: 650; color: {c['text']}; }}
        QGroupBox::title {{ subcontrol-origin: padding; subcontrol-position: top left; top: 9px; left: 14px; padding: 0 5px; background: {c['surface']}; color: {c['accent']}; }}
        QPushButton {{ background: {c['surface2']}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 10px; padding: 10px 15px; font-weight: 650; }}
        QPushButton:hover {{ background: {c['accent_soft']}; border-color: {c['accent']}; }}
        QPushButton:focus {{ border: 1px solid {c['accent']}; }}
        QPushButton:pressed {{ background: {c['selection']}; }}
        QPushButton:disabled {{ color: {c['muted']}; background: {c['surface']}; border-color: {c['border']}; }}
        QPushButton#primaryButton {{ background: {c['accent']}; border-color: {c['accent']}; color: white; }}
        QPushButton#primaryButton:hover {{ background: {c['accent_hover']}; }}
        QComboBox, QLineEdit, QTextEdit {{ background: {c['input']}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 9px; padding: 9px; selection-background-color: {c['selection']}; }}
        QComboBox QAbstractItemView {{ outline: 0; border: 1px solid {c['border']}; }}
        QSlider {{ background: transparent; }}
        QComboBox:hover, QLineEdit:hover, QTextEdit:hover {{ border-color: {c['accent']}; }}
        QComboBox::drop-down {{ border: 0; width: 24px; }}
        QComboBox QAbstractItemView {{ background: {c['surface']}; color: {c['text']}; selection-background-color: {c['accent_soft']}; }}
        QCheckBox, QRadioButton {{ background: transparent; spacing: 8px; color: {c['text']}; padding: 4px; border: none; }}
        QCheckBox:hover, QRadioButton:hover {{ background: {c['accent_soft']}; border-radius: 6px; }}
        QCheckBox::indicator, QRadioButton::indicator {{ width: 16px; height: 16px; }}
        QCheckBox::indicator {{ border: 1px solid {c['border']}; border-radius: 5px; background: {c['input']}; }}
        QCheckBox::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']}; }}
        QRadioButton::indicator {{ border: 1px solid {c['border']}; border-radius: 8px; background: {c['input']}; }}
        QRadioButton::indicator:checked {{ background: {c['accent_hover']}; border: 4px solid {c['accent']}; }}
        QSlider::groove:horizontal {{ height: 5px; background: {c['border']}; border-radius: 3px; }}
        QSlider::sub-page:horizontal {{ background: {c['accent']}; border-radius: 3px; }}
        QSlider::handle:horizontal {{ background: {c['accent_hover']}; width: 15px; margin: -5px 0; border-radius: 8px; }}
        QSlider:disabled {{ opacity: 0.55; }}
        QSlider::groove:horizontal:disabled {{ background: {c['surface2']}; border: 1px solid {c['border']}; }}
        QSlider::sub-page:horizontal:disabled {{ background: {c['border']}; }}
        QSlider::handle:horizontal:disabled {{ background: {c['muted']}; border: 1px solid {c['border']}; }}
        QProgressBar {{ background: {c['surface2']}; border: 1px solid {c['border']}; border-radius: 8px; text-align: center; color: {c['text']}; min-height: 17px; padding: 1px; }}
        QProgressBar::chunk {{ background: {c['accent']}; border-radius: 6px; }}
        QTextEdit#logPanel {{ font-family: Consolas, 'Cascadia Code', monospace; font-size: 9pt; background: {c['log']}; }}
        QLabel#outputSummary {{ color: {c['muted']}; background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 5px 8px; font-size: 8pt; }}
        QStatusBar {{ background: {c['surface']}; color: {c['muted']}; border-top: 1px solid {c['border']}; }}
        QScrollArea {{ border: none; background: transparent; }}
        QScrollBar:vertical {{ background: {c['surface']}; width: 10px; margin: 3px; border-radius: 5px; }}
        QScrollBar::handle:vertical {{ background: {c['border']}; min-height: 28px; border-radius: 5px; }}
        QScrollBar::handle:vertical:hover {{ background: {c['accent']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QSplitter::handle {{ background: transparent; border: none; width: 0px; }}
        """

    def apply_theme(self, theme):
        """Apply and persist the selected theme across all application widgets."""
        if theme not in ("light", "dark", "amoled"):
            theme = "dark"
        self.current_theme = theme
        self.setStyleSheet(self._theme_stylesheet(theme))
        palettes = {
            "light": ("#f2eaf3", "#ead9e9", "#c21f7d", "#d92d91"),
            "dark": ("#2b2432", "#403747", "#b883ff", "#a66af5"),
            "amoled": ("#111111", "#292929", "#ca99ff", "#bb78ff"),
        }
        surface, border, text, accent = palettes[theme]
        if hasattr(self, "mode_card"):
            self.mode_card.setStyleSheet(f"QFrame#modeCard {{ background:{surface}; border:1px solid {border}; border-radius:13px; }}")
        if hasattr(self, "selected_file_label"):
            self.selected_file_label.setStyleSheet(f"background:{surface}; border:1px solid {border}; border-radius:8px; padding:10px; color:{text};")
            self.output_path_label.setStyleSheet(f"background:{surface}; border:1px solid {border}; border-radius:8px; padding:10px; color:{text};")
            self.audio_tracks_label.setStyleSheet(f"color:{accent}; font-weight:600;")
            self.app_title.setStyleSheet(f"font-size:18pt; font-weight:850; color:{accent}; letter-spacing:1.2px; background:transparent;")
            self.app_subtitle.setStyleSheet(f"color:{text}; font-size:9pt; background:transparent;")
            self.brand_mark.setStyleSheet(f"background:{surface}; border:1px solid {border}; border-radius:16px;")
        self.settings.setValue("theme", theme)
        self.settings.sync()


    def show_about_dialog(self):
        """Show application details, using the currently selected app theme."""
        is_ru = self.current_language == "ru"
        palettes = {
            "light": {"bg": "#f8f4f8", "surface": "#ffffff", "text": "#302638", "muted": "#766779", "border": "#ead9e9", "accent": "#d92d91", "hover": "#fbe1f0"},
            "dark": {"bg": "#17151b", "surface": "#211d27", "text": "#f5edf7", "muted": "#b5a6bb", "border": "#403747", "accent": "#a66af5", "hover": "#382849"},
            "amoled": {"bg": "#000000", "surface": "#080808", "text": "#f5f5f7", "muted": "#a2a2aa", "border": "#292929", "accent": "#bb78ff", "hover": "#21132f"},
        }
        c = palettes.get(self.current_theme, palettes["dark"])
        dialog = QDialog(self)
        dialog.setWindowTitle("О программе" if is_ru else "About")
        dialog.setModal(True)
        dialog.setMinimumWidth(430)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(10)

        title = QLabel("VIDEO / AUDIO · STUDIO")
        title.setStyleSheet(f"font-size: 17pt; font-weight: 800; color: {c['accent']}; background: transparent;")
        subtitle = QLabel("Профессиональный конвертер аудио и видео" if is_ru else "A professional audio and video converter")
        subtitle.setWordWrap(True)
        description = QLabel(
            ("Конвертация аудио и видео на базе FFmpeg. Поддержка разных форматов, "
             "настроек качества и режимов без потери качества.") if is_ru else
            ("Audio and video conversion powered by FFmpeg, with format options, "
             "quality controls, and lossless mode.")
        )
        description.setWordWrap(True)
        description.setStyleSheet(f"color: {c['muted']}; background: transparent;")

        inspiration = QLabel(
            "Вдохновлено интерфейсом AmelliaBot" if is_ru else
            "UI inspired by AmelliaBot"
        )
        inspiration.setWordWrap(True)
        inspiration.setStyleSheet(f"color: {c['accent']}; font-size: 9pt; background: transparent;")

        links = QLabel(
            '<b>GitHub:</b> <a href="https://github.com/LusterOK/Video-Audio-Converter">LusterOK/Video-Audio-Converter</a><br>'
            '<b>Developer:</b> LusterOK<br>'
            '<b>Telegram:</b> <a href="https://t.me/mmmmmm7237">@mmmmmm7237</a>'
        )
        links.setOpenExternalLinks(True)
        links.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        links.setStyleSheet(
            f"background: transparent; color: {c['text']}; "
            f"QLabel {{ line-height: 1.5; }} QLabel a {{ color: {c['accent']}; }}"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(description)
        layout.addSpacing(2)
        layout.addWidget(inspiration)
        layout.addSpacing(4)
        layout.addWidget(links)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.setStyleSheet(
            f"QDialog {{ background: {c['bg']}; color: {c['text']}; }} "
            f"QLabel {{ color: {c['text']}; }} "
            f"QPushButton {{ background: {c['surface']}; color: {c['text']}; "
            f"border: 1px solid {c['border']}; border-radius: 8px; padding: 7px 18px; }} "
            f"QPushButton:hover {{ background: {c['hover']}; border-color: {c['accent']}; }}"
        )
        dialog.exec()

    def on_theme_changed(self, index):
        self.apply_theme(("light", "dark", "amoled")[index])

    def create_ui_elements(self):
        # Header
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(22, 18, 22, 14)
        self.main_layout.setSpacing(12)
        header = QHBoxLayout()
        header.setSpacing(14)
        self.brand_mark = ClickableLabel()
        self.brand_mark.setObjectName("brandMark")
        self.brand_mark.setCursor(Qt.CursorShape.PointingHandCursor)
        self.brand_mark.setToolTip("О программе / About")
        self.brand_mark.clicked.connect(self.show_about_dialog)
        self.brand_mark.setFixedSize(54, 54)
        mark_path = resource_path("brand-mark.png")
        if os.path.isfile(mark_path):
            self.brand_mark.setPixmap(QPixmap(mark_path).scaled(42, 42, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.brand_mark)
        brand = QVBoxLayout()
        brand.setSpacing(3)
        self.app_title = QLabel("VIDEO / AUDIO  ·  STUDIO")
        self.app_title.setStyleSheet("font-size: 18pt; font-weight: 850; color: #b883ff; letter-spacing: 1.2px; background: transparent;")
        self.app_subtitle = QLabel("Media conversion workspace")
        self.app_subtitle.setStyleSheet("color: #8e8f9f; font-size: 9pt; background: transparent;")
        brand.addWidget(self.app_title)
        brand.addWidget(self.app_subtitle)
        header.addLayout(brand)
        header.addStretch()
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Русский", "English"])
        self.language_combo.setFixedWidth(135)
        header.addWidget(self.language_combo)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Светлая тема", "Тёмная тема", "AMOLED"])
        self.theme_combo.setFixedWidth(150)
        header.addWidget(self.theme_combo)
        self.main_layout.addLayout(header)

        self.control_panel = QWidget()
        control_layout = QVBoxLayout(self.control_panel)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(12)

        mode_card = QFrame()
        self.mode_card = mode_card
        mode_card.setObjectName("modeCard")
        mode_layout = QHBoxLayout(mode_card)
        mode_layout.setContentsMargins(14, 8, 14, 8)
        self.mode_switcher_label = QLabel()
        mode_layout.addWidget(self.mode_switcher_label)
        self.video_mode_radio = QRadioButton()
        self.video_mode_radio.setChecked(True)
        self.audio_mode_radio = QRadioButton()
        mode_layout.addWidget(self.video_mode_radio)
        mode_layout.addWidget(self.audio_mode_radio)
        mode_layout.addSpacing(20)
        self.mode_label = QLabel()
        mode_layout.addWidget(self.mode_label)
        self.simple_mode_radio = QRadioButton()
        self.simple_mode_radio.setChecked(True)
        self.advanced_mode_radio = QRadioButton()
        mode_layout.addWidget(self.simple_mode_radio)
        mode_layout.addWidget(self.advanced_mode_radio)
        mode_layout.addStretch()
        control_layout.addWidget(mode_card)

        workspace = QSplitter(Qt.Orientation.Horizontal)
        workspace.setChildrenCollapsible(False)
        # No visible splitter gutter or divider: keep both panels adjacent.
        workspace.setHandleWidth(0)
        workspace.setMinimumHeight(250)
        workspace.setStretchFactor(0, 1)
        workspace.setStretchFactor(1, 1)

        # Left side: source, destination and output format.
        media_panel = QGroupBox("MEDIA / OUTPUT")
        media_layout = QVBoxLayout(media_panel)
        media_layout.setSpacing(7)
        self.input_file_label = QLabel()
        self.select_file_button = QPushButton()
        input_row = QHBoxLayout()
        input_row.addWidget(self.input_file_label)
        input_row.addStretch()
        input_row.addWidget(self.select_file_button)
        media_layout.addLayout(input_row)
        self.selected_file_label = QLabel()
        self.selected_file_label.setWordWrap(True)
        self.selected_file_label.setMinimumHeight(42)
        self.selected_file_label.setStyleSheet("background:#191a21; border:1px solid #353643; border-radius:6px; padding:10px; color:#b9a3ff;")
        media_layout.addWidget(self.selected_file_label)
        info_row = QHBoxLayout()
        self.media_type_label = QLabel()
        self.audio_tracks_label = QLabel()
        self.audio_tracks_label.setStyleSheet("color:#d5b56d; font-weight:600;")
        info_row.addWidget(self.media_type_label)
        info_row.addStretch()
        info_row.addWidget(self.audio_tracks_label)
        media_layout.addLayout(info_row)
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: palette(mid);")
        media_layout.addWidget(divider)
        self.output_file_label = QLabel()
        self.save_as_button = QPushButton()
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_file_label)
        output_row.addStretch()
        output_row.addWidget(self.save_as_button)
        media_layout.addLayout(output_row)
        self.output_path_label = QLabel()
        self.output_path_label.setWordWrap(True)
        self.output_path_label.setMinimumHeight(42)
        self.output_path_label.setStyleSheet("background:#191a21; border:1px solid #353643; border-radius:6px; padding:10px; color:#b9a3ff;")
        media_layout.addWidget(self.output_path_label)
        format_row = QHBoxLayout()
        self.format_label = QLabel()
        self.format_combo = QComboBox()
        self.format_combo.addItems(VIDEO_FORMATS)
        self.format_line_edit = QLineEdit()
        self.format_line_edit.setPlaceholderText("Формат вручную (например, mkv)")
        self.format_line_edit.setVisible(False)
        format_row.addWidget(self.format_label)
        format_row.addWidget(self.format_combo, 1)
        format_row.addWidget(self.format_line_edit, 1)
        media_layout.addLayout(format_row)

        # Compact summary: avoid a second framed group box so the information
        # remains visible even when the window is not tall.
        self.output_summary_label = QLabel()
        self.output_summary_label.setWordWrap(True)
        self.output_summary_label.setObjectName("outputSummary")
        self.output_summary_label.setMaximumHeight(48)
        self.output_summary_label.setMinimumHeight(34)
        media_layout.addWidget(self.output_summary_label)
        media_layout.addStretch(1)
        workspace.addWidget(media_panel)

        # Right side: encoder controls, with a scroll area for smaller screens.
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        settings_content = QWidget()
        settings_layout = QVBoxLayout(settings_content)
        settings_layout.setContentsMargins(8, 2, 8, 2)
        settings_layout.setSpacing(8)

        self.video_settings_group = QGroupBox()
        video_settings_layout = QVBoxLayout(self.video_settings_group)
        video_settings_layout.setSpacing(9)
        quality_layout = QHBoxLayout()
        self.quality_label = QLabel()
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(0, 51)
        self.quality_slider.setValue(23)
        self.quality_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.current_quality_label = QLabel(str(self.quality_slider.value()))
        self.current_quality_label.setMinimumWidth(28)
        self.quality_slider.setToolTip('Качество кодирования' if self.current_language == 'ru' else 'Encoding quality')
        self.current_quality_label.setToolTip(self.quality_slider.toolTip())
        quality_layout.addWidget(self.quality_label)
        quality_layout.addWidget(self.quality_slider, 1)
        quality_layout.addWidget(self.current_quality_label)
        video_settings_layout.addLayout(quality_layout)
        self.lossless_checkbox = QCheckBox()
        video_settings_layout.addWidget(self.lossless_checkbox)
        self.keep_all_tracks_checkbox = QCheckBox()
        video_settings_layout.addWidget(self.keep_all_tracks_checkbox)
        self.copy_metadata_checkbox = QCheckBox()
        self.copy_metadata_checkbox.setChecked(True)
        video_settings_layout.addWidget(self.copy_metadata_checkbox)
        codec_layout = QHBoxLayout()
        self.video_codec_label = QLabel()
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(CODECS)
        self.codec_line_edit = QLineEdit("libx264")
        codec_layout.addWidget(self.video_codec_label)
        codec_layout.addWidget(self.codec_combo, 1)
        codec_layout.addWidget(self.codec_line_edit, 1)
        video_settings_layout.addLayout(codec_layout)
        audio_codec_layout = QHBoxLayout()
        self.audio_codec_label = QLabel()
        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.addItems(AUDIO_CODECS)
        self.audio_codec_line_edit = QLineEdit("aac")
        audio_codec_layout.addWidget(self.audio_codec_label)
        audio_codec_layout.addWidget(self.audio_codec_combo, 1)
        audio_codec_layout.addWidget(self.audio_codec_line_edit, 1)
        video_settings_layout.addLayout(audio_codec_layout)
        settings_layout.addWidget(self.video_settings_group)

        self.audio_settings_group = QGroupBox()
        audio_settings_layout = QVBoxLayout(self.audio_settings_group)
        audio_settings_layout.setSpacing(9)
        audio_only_codec_layout = QHBoxLayout()
        self.audio_only_codec_label = QLabel()
        self.audio_only_codec_combo = QComboBox()
        self.audio_only_codec_combo.addItems(AUDIO_CODECS)
        self.audio_only_codec_line_edit = QLineEdit("aac")
        audio_only_codec_layout.addWidget(self.audio_only_codec_label)
        audio_only_codec_layout.addWidget(self.audio_only_codec_combo, 1)
        audio_only_codec_layout.addWidget(self.audio_only_codec_line_edit, 1)
        audio_settings_layout.addLayout(audio_only_codec_layout)
        bitrate_layout = QHBoxLayout()
        self.audio_bitrate_label = QLabel()
        self.audio_bitrate_edit = QLineEdit("192k")
        bitrate_layout.addWidget(self.audio_bitrate_label)
        bitrate_layout.addWidget(self.audio_bitrate_edit, 1)
        audio_settings_layout.addLayout(bitrate_layout)
        self.audio_lossless_checkbox = QCheckBox()
        audio_settings_layout.addWidget(self.audio_lossless_checkbox)
        self.audio_copy_metadata_checkbox = QCheckBox()
        self.audio_copy_metadata_checkbox.setChecked(True)
        audio_settings_layout.addWidget(self.audio_copy_metadata_checkbox)
        settings_layout.addWidget(self.audio_settings_group)

        self.ffmpeg_args_label = QLabel()
        settings_layout.addWidget(self.ffmpeg_args_label)
        self.ffmpeg_args_edit = QTextEdit()
        self.ffmpeg_args_edit.setMaximumHeight(76)
        self.ffmpeg_args_edit.setPlaceholderText("-preset slow …")
        settings_layout.addWidget(self.ffmpeg_args_edit)
        settings_layout.addStretch(1)
        settings_scroll.setWidget(settings_content)
        workspace.addWidget(settings_scroll)
        workspace.setSizes([460, 560])
        control_layout.addWidget(workspace, 1)

        # Persistent footer: progress, primary action and log.
        progress_row = QHBoxLayout()
        self.progress_label = QLabel()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_row.addWidget(self.progress_label)
        progress_row.addWidget(self.progress_bar, 1)
        self.progress_details_label = QLabel()
        self.progress_details_label.setMinimumWidth(170)
        self.progress_details_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        progress_row.addWidget(self.progress_details_label)
        control_layout.addLayout(progress_row)
        buttons_layout = QHBoxLayout()
        self.start_button = QPushButton()
        self.start_button.setObjectName("primaryButton")
        self.clear_log_button = QPushButton()
        self.save_log_button = QPushButton()
        buttons_layout.addWidget(self.start_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.clear_log_button)
        buttons_layout.addWidget(self.save_log_button)
        control_layout.addLayout(buttons_layout)
        self.main_layout.addWidget(self.control_panel, 1)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("logPanel")
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("")
        self.log_text.setMinimumHeight(90)
        self.log_text.setMaximumHeight(155)
        self.main_layout.addWidget(self.log_text)
        self.setCentralWidget(self.main_widget)
        self.status_bar = QStatusBar()
        # The native QSizeGrip creates an unstyled diagonal corner in the
        # bottom-right of the window. Keep the window resizable without it.
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)

    def connect_signals(self):
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        self.select_file_button.clicked.connect(self.open_file_dialog)
        self.save_as_button.clicked.connect(self.open_save_as_dialog)
        self.start_button.clicked.connect(self.start_conversion)
        self.clear_log_button.clicked.connect(self.clear_log)
        self.save_log_button.clicked.connect(self.save_log_to_file)
        self.quality_slider.valueChanged.connect(self.update_quality_display)
        self.format_combo.currentTextChanged.connect(self.update_output_summary)
        self.format_line_edit.textChanged.connect(self.update_output_summary)
        self.format_line_edit.editingFinished.connect(self.on_format_changed)
        self.codec_line_edit.textChanged.connect(self.update_output_summary)
        self.audio_codec_line_edit.textChanged.connect(self.update_output_summary)
        self.lossless_checkbox.toggled.connect(self.update_output_summary)
        self.audio_lossless_checkbox.toggled.connect(self.update_output_summary)
        self.audio_lossless_checkbox.toggled.connect(self.on_audio_lossless_changed)
        self.lossless_checkbox.toggled.connect(self.on_lossless_changed)
        self.format_combo.currentIndexChanged.connect(self.on_format_changed)
        self.codec_combo.currentIndexChanged.connect(self.on_codec_changed)
        self.codec_line_edit.textChanged.connect(self.on_codec_changed)
        
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
        if hasattr(self, "app_subtitle"):
            self.app_subtitle.setText("Профессиональная рабочая область" if lang == "ru" else "Professional media workspace")
        if hasattr(self, "theme_combo"):
            selected_theme = self.theme_combo.currentIndex()
            self.theme_combo.blockSignals(True)
            self.theme_combo.clear()
            self.theme_combo.addItems(["Светлая тема", "Тёмная тема", "AMOLED"] if lang == "ru" else ["Light", "Dark", "AMOLED"])
            self.theme_combo.setCurrentIndex(selected_theme)
            self.theme_combo.blockSignals(False)
        self.input_file_label.setText(LANGUAGES['input_file_label'][lang])
        self.keep_all_tracks_checkbox.setText(LANGUAGES['keep_all_tracks'][lang])
        self.copy_metadata_checkbox.setText(LANGUAGES['copy_metadata'][lang])
        self.audio_copy_metadata_checkbox.setText(LANGUAGES['copy_metadata'][lang])
        self.ffmpeg_args_label.setText(LANGUAGES['ffmpeg_args_label'][lang])
        self.progress_label.setText(LANGUAGES['progress_label'][lang])
        self.log_text.setPlaceholderText(LANGUAGES['log_placeholder'][lang])
        if self.conversion_started_at is None:
            self.progress_details_label.setText(LANGUAGES['ready_status'][lang])
        self.output_file_label.setText(LANGUAGES['output_file_label'][lang])
        self.select_file_button.setText(LANGUAGES['select_file_button'][lang])
        self.save_as_button.setText(LANGUAGES['save_as_button'][lang])
        self.start_button.setText(LANGUAGES['start_button'][lang])
        self.clear_log_button.setText(LANGUAGES['clear_log'][lang])
        self.save_log_button.setText(LANGUAGES['save_log'][lang])
        self.format_label.setText(LANGUAGES['format_label'][lang])
        self.format_line_edit.setPlaceholderText(LANGUAGES['format_manual_placeholder'][lang])
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
        self.update_output_summary()
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
        active_group = self.video_settings_group if is_video else self.audio_settings_group
        inactive_group = self.audio_settings_group if is_video else self.video_settings_group
        inactive_group.hide()
        active_group.show()
        # A short opacity transition softens mode changes without delaying conversion.
        if not hasattr(self, "_mode_opacity_effects"):
            self._mode_opacity_effects = {}
            for group in (self.video_settings_group, self.audio_settings_group):
                effect = QGraphicsOpacityEffect(group)
                effect.setOpacity(1.0)
                group.setGraphicsEffect(effect)
                self._mode_opacity_effects[group] = effect
        effect = self._mode_opacity_effects[active_group]
        effect.setOpacity(0.72)
        self._mode_animation = QPropertyAnimation(effect, b"opacity", self)
        self._mode_animation.setDuration(160)
        self._mode_animation.setStartValue(0.72)
        self._mode_animation.setEndValue(1.0)
        self._mode_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._mode_animation.start()
        
        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        self.format_combo.addItems(VIDEO_FORMATS if is_video else AUDIO_FORMATS)
        self.format_combo.blockSignals(False)
        self.on_format_changed()
        self.on_lossless_changed(self.lossless_checkbox.isChecked())
        self.on_audio_lossless_changed(self.audio_lossless_checkbox.isChecked())
        self.update_output_summary()

    def on_format_changed(self, *_):
        format_name = self.get_current_format().strip().lower().lstrip(".")
        # Lossless audio is only valid in genuinely lossless containers.
        # If the user selects a lossy format while lossless is enabled, switch
        # back to FLAC instead of letting the worker fail after starting.
        if self.conversion_mode == "audio" and self.audio_lossless_checkbox.isChecked() and format_name not in {"flac", "wav"}:
            format_name = "flac"
            if self.current_mode == "advanced":
                self.format_line_edit.blockSignals(True)
                self.format_line_edit.setText(format_name)
                self.format_line_edit.blockSignals(False)
            else:
                self.format_combo.blockSignals(True)
                self.format_combo.setCurrentText(format_name)
                self.format_combo.blockSignals(False)
            self.set_audio_codec_for_lossless(format_name)
        current_path = self.output_path_label.text()
        if current_path and current_path not in ["Нет пути сохранения", "No output path"]:
            base = os.path.splitext(current_path)[0]
            self.output_path_label.setText(f"{base}.{format_name}")
        self.update_output_summary()
        self.save_settings()

    def set_audio_codec_for_lossless(self, format_name):
        """Keep the audio codec aligned with the selected lossless container."""
        codec = "flac" if format_name == "flac" else "wav"
        if self.current_mode == "advanced":
            self.audio_only_codec_line_edit.setText(codec)
        else:
            self.audio_only_codec_combo.setCurrentText(codec)

    def on_audio_lossless_changed(self, checked):
        """Disable lossy bitrate controls and enforce a lossless output format."""
        self.audio_bitrate_edit.setEnabled(not checked)
        lang = self.get_current_language()
        self.audio_bitrate_edit.setToolTip(
            ("Битрейт не используется в режиме без потерь" if lang == "ru" else
             "Bitrate is ignored in lossless mode") if checked else
            ("Битрейт для кодеков с потерями" if lang == "ru" else
             "Bitrate for lossy codecs")
        )
        if checked:
            format_name = self.get_current_format().strip().lower().lstrip(".")
            if format_name not in {"flac", "wav"}:
                format_name = "flac"
                if self.current_mode == "advanced":
                    self.format_line_edit.blockSignals(True)
                    self.format_line_edit.setText(format_name)
                    self.format_line_edit.blockSignals(False)
                else:
                    self.format_combo.blockSignals(True)
                    self.format_combo.setCurrentText(format_name)
                    self.format_combo.blockSignals(False)
                current_path = self.output_path_label.text()
                if current_path and current_path not in ["Нет пути сохранения", "No output path"]:
                    base = os.path.splitext(current_path)[0]
                    self.output_path_label.setText(f"{base}.flac")
            self.set_audio_codec_for_lossless(format_name)
        self.update_output_summary()
        self.save_settings()

    def get_current_format(self):
        if self.current_mode == "advanced" and (manual := self.format_line_edit.text().strip()):
            return manual
        return self.format_combo.currentText()

    def on_codec_changed(self):
        codec = self.get_video_codec()
        if codec in CODEC_INFO:
            info = CODEC_INFO[codec]
            # CRF 0 means lossless for x264/x265/VP9, so keep it reserved
            # for the explicit lossless checkbox rather than ordinary quality mode.
            min_quality = max(1, info['min']) if info.get('param') == 'crf' else info['min']
            self.quality_slider.setRange(min_quality, info['max'])
        else:
            self.quality_slider.setRange(1, 51)
        self.on_lossless_changed(self.lossless_checkbox.isChecked())
        self.update_quality_display()

    def on_lossless_changed(self, checked):
        # Lossless encoder settings override quality/CRF, so make the slider visibly unavailable.
        self.quality_slider.setEnabled(not checked)
        self.current_quality_label.setEnabled(not checked)
        self.quality_slider.setToolTip(
            ('В режиме без потери качества этот параметр не используется' if self.current_language == 'ru'
             else 'Quality is ignored in lossless mode') if checked else
            ('Качество кодирования' if self.current_language == 'ru' else 'Encoding quality')
        )
        self.current_quality_label.setText('—' if checked else str(self.quality_slider.value()))
        self.current_quality_label.setToolTip(self.quality_slider.toolTip())
        if not checked and self.quality_slider.value() == 0:
            self.quality_slider.setValue(max(1, self.quality_slider.minimum()))

    def load_saved_settings(self):
        self.language_combo.setCurrentIndex(0 if self.current_language == "ru" else 1)
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentIndex({"light": 0, "dark": 1, "amoled": 2}.get(self.current_theme, 1))
        self.theme_combo.blockSignals(False)
        self.video_mode_radio.setChecked(self.last_conversion_mode == "video")
        self.audio_mode_radio.setChecked(self.last_conversion_mode == "audio")
        self.conversion_mode = "audio" if self.audio_mode_radio.isChecked() else "video"
        self.update_conversion_mode_ui()
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
        self.on_codec_changed()
        self.keep_all_tracks_checkbox.setChecked(self.last_keep_all_tracks)

    def save_settings(self):
        self.settings.setValue("language", "ru" if self.language_combo.currentIndex() == 0 else "en")
        self.settings.setValue("theme", self.current_theme)
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
            elif self.input_media_type == "video":
                self.video_mode_radio.setChecked(True)
                self.on_conversion_mode_changed()
            self.save_settings()

    def open_save_as_dialog(self):
        lang = self.get_current_language()
        file_path, _ = QFileDialog.getSaveFileName(self, LANGUAGES['save_dialog_title'][lang], "", "All Files (*)")
        if file_path:
            self.output_path_label.setText(file_path)
            self.update_output_summary()
            self.save_settings()

    def clear_log(self):
        self.log_text.clear()

    def update_quality_display(self, value=None):
        val = value if value is not None else self.quality_slider.value()
        self.current_quality_label.setText(str(val))
        self.update_output_summary()
        self.save_settings()

    def update_output_summary(self, *_):
        """Refresh a compact, read-only summary that fits short window heights."""
        lang = self.get_current_language()
        fmt = self.get_current_format().strip().lower().lstrip(".") or ("не задан" if lang == "ru" else "not set")
        path = self.output_path_label.text().strip()
        filename = os.path.basename(path) if path else ("не выбран" if lang == "ru" else "not selected")
        if self.conversion_mode == "audio":
            codec = self.get_audio_only_codec() or ("по умолчанию" if lang == "ru" else "default")
            lossless = self.audio_lossless_checkbox.isChecked()
            line1 = (f"Выход: {filename}  ·  {fmt.upper()}" if lang == "ru" else
                     f"Output: {filename}  ·  {fmt.upper()}")
            line2 = (f"Кодек: {codec}  ·  {'Без потерь' if lossless else 'Обычное качество'}" if lang == "ru" else
                     f"Codec: {codec}  ·  {'Lossless' if lossless else 'Standard quality'}")
        else:
            codec = self.get_video_codec() or ("по умолчанию" if lang == "ru" else "default")
            audio_codec = self.get_audio_codec() or ("по умолчанию" if lang == "ru" else "default")
            lossless = self.lossless_checkbox.isChecked()
            line1 = (f"Выход: {filename}  ·  {fmt.upper()}" if lang == "ru" else
                     f"Output: {filename}  ·  {fmt.upper()}")
            line2 = (f"Видео: {codec}  ·  Аудио: {audio_codec}  ·  {'Без потерь' if lossless else 'Обычное качество'}" if lang == "ru" else
                     f"Video: {codec}  ·  Audio: {audio_codec}  ·  {'Lossless' if lossless else 'Standard quality'}")
        self.output_summary_label.setText(line1 + "\n" + line2)

    @staticmethod
    def _format_clock(seconds):
        if seconds is None or seconds < 0:
            return "--:--"
        seconds = int(seconds)
        return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"

    def update_progress_details(self):
        lang = self.get_current_language()
        if self.conversion_started_at is None:
            return
        elapsed = max(0, time.monotonic() - self.conversion_started_at)
        progress = self.progress_bar.value()
        eta = (elapsed * (100 - progress) / progress) if progress > 0 else None
        if lang == "ru":
            parts = [f"Прошло {self._format_clock(elapsed)}"]
            if eta is not None and progress < 100:
                parts.append(f"осталось ~{self._format_clock(eta)}")
        else:
            parts = [f"Elapsed {self._format_clock(elapsed)}"]
            if eta is not None and progress < 100:
                parts.append(f"ETA ~{self._format_clock(eta)}")
        if self.latest_ffmpeg_speed:
            parts.append(f"{'скорость' if lang == 'ru' else 'speed'} {self.latest_ffmpeg_speed}")
        self.progress_details_label.setText(" · ".join(parts))

    def handle_conversion_log(self, message):
        self.log_text.append(message)
        match = re.search(r"\\bspeed=\\s*([0-9.]+x)", str(message))
        if match:
            self.latest_ffmpeg_speed = match.group(1)
            self.update_progress_details()

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
        output_file = self.output_path_label.text().strip()

        if not os.path.exists(input_file):
            QMessageBox.critical(self, LANGUAGES['conversion_error'][self.get_current_language()], LANGUAGES['input_missing_error'][self.get_current_language()])
            return
        if not output_file or output_file in {"Нет пути сохранения", "No output path"}:
            QMessageBox.critical(self, LANGUAGES['conversion_error'][self.get_current_language()], LANGUAGES['output_missing_error'][self.get_current_language()])
            return

        format_ = self.get_current_format().strip().lower().lstrip('.')
        if not format_:
            QMessageBox.critical(self, LANGUAGES['conversion_error'][self.get_current_language()], LANGUAGES['format_missing_error'][self.get_current_language()])
            return
        output_root, output_ext = os.path.splitext(output_file)
        expected_ext = f".{format_}"
        if output_ext.lower() != expected_ext:
            output_file = f"{output_root if output_ext else output_file}{expected_ext}"
            self.output_path_label.setText(output_file)
            self.update_output_summary()
            self.save_settings()
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
                self.keep_all_tracks_checkbox.isChecked(), self.audio_tracks_count, ffmpeg_args,
                self.copy_metadata_checkbox.isChecked()
            )

        self.progress_bar.setValue(0)
        self.conversion_started_at = time.monotonic()
        self.latest_ffmpeg_speed = ""
        self.progress_details_label.setText("Запуск…" if self.get_current_language() == "ru" else "Starting…")
        self.progress_timer.start()
        self.converter_thread.progress_update.connect(self.progress_bar.setValue)
        self.converter_thread.progress_update.connect(lambda _value: self.update_progress_details())
        self.converter_thread.log_update.connect(self.handle_conversion_log)
        self.converter_thread.conversion_finished.connect(self.on_conversion_finished)
        # Mark the worker active before start() returns so an immediate stop/close is not missed.
        self.converter_thread.is_running = True
        self.converter_thread.start()
        self.start_button.setText(LANGUAGES['stop_button'][self.get_current_language()])

    def on_conversion_finished(self, success, message):
        lang = self.get_current_language()
        self.progress_timer.stop()
        self.update_progress_details()
        self.start_button.setText(LANGUAGES['start_button'][lang])
        if success:
            QMessageBox.information(self, LANGUAGES['conversion_complete'][lang], message)
        else:
            # Keep the raw diagnostics in the log and expose them as expandable
            # details, while presenting a plain-language reason in the main text.
            log_text = self.log_text.toPlainText()
            explanation = explain_ffmpeg_error(log_text, message, lang)
            details = "\n".join(log_text.splitlines()[-18:]).strip()
            code_match = re.search(r"(?:код(?:ом)?|code)[: ]+(-?\d+)", str(message), re.IGNORECASE)
            code_line = (f"\n\nКод FFmpeg: {code_match.group(1)}" if lang == "ru" else
                         f"\n\nFFmpeg code: {code_match.group(1)}") if code_match else ""
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Critical)
            box.setWindowTitle(LANGUAGES['conversion_error'][lang])
            box.setText(explanation + code_line)
            if details:
                box.setDetailedText(details)
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
            # Qt creates the details button when detailed text is set; localize it
            # without changing the standard OK button.
            for button in box.buttons():
                if button.text().replace("&", "").strip().lower() in ("show details...", "show details", "hide details...", "hide details"):
                    localized_details = "Подробнее…" if lang == "ru" else "Show Details…"
                    button.setText(localized_details)
                    # QMessageBox changes this label itself when expanded; restore
                    # the localized label after Qt processes each toggle.
                    button.clicked.connect(
                        lambda _checked=False, b=button, label=localized_details:
                            QTimer.singleShot(0, lambda: b.setText(label))
                    )
            box.exec()

    def closeEvent(self, event):
        self.save_settings()
        if self.converter_thread and self.converter_thread.is_running:
            self.converter_thread.stop()
            self.converter_thread.wait()
        event.accept()