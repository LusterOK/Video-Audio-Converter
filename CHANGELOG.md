# Changelog

All notable changes for Video-Audio-Converter are documented here.

## [1.0.0] — Initial release

### Added
- Redesigned the application interface as Studio Pro, with a cleaner layout and improved controls.
- Added Light, Dark, and AMOLED appearance themes.
- Added Russian and English interface localization.
- Added audio and video conversion workflows powered by FFmpeg.
- Added conversion progress reporting and cancellation controls.
- Added clearer explanations for common FFmpeg and conversion errors.
- Added an About dialog with project links and UI inspiration credit.
- Added a Windows PyInstaller build script and application metadata.

### Improved
- Refined conversion worker behavior and shared process utilities.
- Improved handling of conversion options, including lossless-oriented settings where supported by the selected format and codec.
- Reduced the packaged Windows executable size by excluding unnecessary PySide6 modules.
- Added build cleanup for temporary artifacts and caches.

### Fixed
- Fixed multiple UI, theme-control, layout, and conversion-related issues found during testing.
- Improved error handling for missing tools and failed conversion processes.

### Requirements and notes
- FFmpeg and FFprobe must be installed and available on PATH for conversion.
- The Windows executable was manually checked by the project maintainer. Automated checks cover Python syntax and error-explanation tests; a full Windows GUI/build test is environment-dependent.
