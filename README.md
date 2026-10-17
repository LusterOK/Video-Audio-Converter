<p align="center">
  <img src="brand-mark.png" alt="Video / Audio · Studio Pro logo" width="112" />
</p>

<h1 align="center">VIDEO / AUDIO · STUDIO PRO</h1>

<p align="center">
  <strong>A professional audio and video converter</strong>
</p>

<p align="center">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" />
  <img alt="UI PySide6" src="https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white" />
  <img alt="Core FFmpeg" src="https://img.shields.io/badge/Core-FFmpeg-007808" />
  <img alt="License CC0" src="https://img.shields.io/badge/License-CC0-32A852" />
</p>

<p align="center">
  <a href="https://github.com/LusterOK/Video-Audio-Converter">GitHub Repository</a>
  · <a href="https://t.me/mmmmmm7237">Telegram</a>
</p>

A desktop audio and video converter built with Python, PySide6, and FFmpeg. It features a Studio Pro interface with Light, Dark, and AMOLED themes, Russian and English localization, simple and advanced modes, conversion progress, logs, and cancellation.

[Русский](#русский) · [English](#english)

---

## Русский

### Возможности

- **Аудио:** MP3, WAV, FLAC, AAC и OGG.
- **Видео:** MP4, AVI, MKV, MOV и WEBM.
- Простой и продвинутый режимы; дополнительные аргументы FFmpeg с проверкой конфликтов.
- Настройки кодеков и качества, включая режимы без потерь для поддерживаемых комбинаций формата и кодека.
- Отображение прогресса и вывода FFmpeg, отмена текущей операции.
- Копирование метаданных, если это поддерживают источник и целевой формат.
- Темы **Light**, **Dark** и **AMOLED**; интерфейс на русском и английском.
- Окно «О программе» со ссылками разработчика.

### Требования

- Windows 10/11 для готовой Windows-сборки.
- Python 3.10 или новее — для запуска из исходников и сборки EXE.
- FFmpeg и FFprobe, доступные через `PATH`. Они **не входят** в EXE и устанавливаются отдельно.

Проверьте доступность FFmpeg в терминале:

```powershell
ffmpeg -version
ffprobe -version
```

Если FFmpeg не установлен, на поддерживаемых версиях Windows можно попробовать установить его через `winget`:

```powershell
winget install --id Gyan.FFmpeg --exact
```

После установки откройте новое окно терминала. Если команда `winget` недоступна, установите FFmpeg из доверенного дистрибутива и добавьте его папку `bin` в `PATH`.

### Запуск из исходников

Откройте PowerShell в папке проекта и выполните:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

Если PowerShell запрещает активацию окружения, можно запускать команды через `\.venv\Scripts\python.exe` без активации.

### Сборка EXE для Windows

1. Установите Python 3.10+ с Python Launcher (`py`).
2. Распакуйте проект в отдельную папку.
3. Запустите `build_windows.bat`.
4. Дождитесь сообщения об успешной сборке.
5. Готовый файл появится в `dist\Converter.exe`.

Скрипт создаёт `.venv`, устанавливает зависимости и PyInstaller, собирает приложение по конфигурации `VideoAudioConverter.spec`, а затем очищает временную папку `build`, Python-кеш и кеш pip. В конце он предложит удалить `.venv`, которая может занимать сотни мегабайт. Если выбрать удаление, EXE останется на месте, но следующая сборка заново создаст окружение и установит зависимости.

Для ручной сборки после установки зависимостей можно запустить:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean VideoAudioConverter.spec
```

**Важно:** FFmpeg не упаковывается внутрь приложения. На целевом компьютере он должен быть установлен отдельно и доступен через `PATH`.

### Перед релизом

Проверьте готовый `dist\Converter.exe` на Windows, в том числе на компьютере без Python:

- запуск приложения и наличие иконки/логотипа;
- переключение русского и английского языков;
- темы Light, Dark и AMOLED, включая окно «О программе»;
- конвертацию MP3, WAV и FLAC, а также видео;
- прогресс, отмену, сохранение метаданных и сообщения об ошибках;
- понятное сообщение, если FFmpeg или FFprobe не найдены.

Не считайте EXE проверенным на Windows, пока фактическая сборка и эти ручные проверки не выполнены.

### Ограничения

- Для конвертации нужен отдельно установленный FFmpeg/FFprobe.
- Доступные кодеки и контейнеры зависят от сборки FFmpeg. Режим без потерь поддерживается только для предусмотренных программой сочетаний.
- Целевые платформы сборки — Windows 10 и Windows 11. Поддержка Windows 7 не заявляется.

### Автор и ссылки

- GitHub: [LusterOK/Video-Audio-Converter](https://github.com/LusterOK/Video-Audio-Converter)
- Telegram: [@mmmmmm7237](https://t.me/mmmmmm7237)
- UI inspired by AmelliaBot.

### Лицензия

CC0 — подробности в файле [`LICENSE`](LICENSE).

---

## English

### Features

- **Audio:** MP3, WAV, FLAC, AAC, and OGG.
- **Video:** MP4, AVI, MKV, MOV, and WEBM.
- Simple and advanced modes, with validation for conflicting extra FFmpeg arguments.
- Codec and quality settings, including lossless options for supported format/codec combinations.
- Conversion progress, FFmpeg output log, and cancellation.
- Metadata copying when supported by the source and target format.
- **Light**, **Dark**, and **AMOLED** themes; Russian and English UI.
- An About dialog with developer links.

### Requirements

- Windows 10/11 for the Windows executable.
- Python 3.10 or newer to run from source or build the executable.
- FFmpeg and FFprobe available on `PATH`. They are **not bundled** with the EXE and must be installed separately.

Verify the FFmpeg installation in a terminal:

```powershell
ffmpeg -version
ffprobe -version
```

On supported Windows installations, you can try installing FFmpeg with `winget`:

```powershell
winget install --id Gyan.FFmpeg --exact
```

Open a new terminal after installation. If `winget` is unavailable, install FFmpeg from a trusted distribution and add its `bin` directory to `PATH`.

### Run from source

Open PowerShell in the project directory and run:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

If PowerShell blocks environment activation, you can invoke `\.venv\Scripts\python.exe` directly instead.

### Build the Windows executable

1. Install Python 3.10+ with the Python Launcher (`py`).
2. Extract the project to a separate folder.
3. Run `build_windows.bat`.
4. Wait for the success message.
5. Find the executable at `dist\Converter.exe`.

The script creates `.venv`, installs the project dependencies and PyInstaller, builds the application using `VideoAudioConverter.spec`, then removes the temporary `build` directory, Python bytecode caches, and pip's download cache. At the end, it asks whether to delete `.venv`, which can occupy several hundred megabytes. The EXE is preserved if you choose to delete it, but the next build will recreate the environment and reinstall dependencies.

For a manual build after installing dependencies, run:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean VideoAudioConverter.spec
```

**Important:** FFmpeg is not bundled. It must be installed separately and available on `PATH` on the target computer.

### Pre-release checklist

Test `dist\Converter.exe` on Windows, including on a machine without Python:

- application startup, icon, and logo;
- Russian and English localization;
- Light, Dark, and AMOLED themes, including the About dialog;
- MP3, WAV, and FLAC conversion, plus video conversion;
- progress, cancellation, metadata handling, and error messages;
- a clear error if FFmpeg or FFprobe cannot be found.

Do not describe the EXE as Windows-tested until the actual build and manual checks have been completed.

### Limitations

- A separate FFmpeg/FFprobe installation is required.
- Available codecs and containers depend on the FFmpeg build. Lossless mode is available only for combinations supported by the application.
- Windows 10 and Windows 11 are the target build platforms. Windows 7 support is not claimed.

### Author and links

- GitHub: [LusterOK/Video-Audio-Converter](https://github.com/LusterOK/Video-Audio-Converter)
- Telegram: [@mmmmmm7237](https://t.me/mmmmmm7237)
- UI inspired by AmelliaBot.

### License

CC0 — see [`LICENSE`](LICENSE).
