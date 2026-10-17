# Changelog

## [1.0.0] — First stable release

### Added
- Studio Pro desktop interface for audio and video conversion.
- Light, Dark, and AMOLED themes.
- Russian and English interface localization.
- Audio and video conversion workflows powered by FFmpeg/FFprobe.
- Conversion progress, FFmpeg output logs, and cancellation controls.
- An About dialog with project links and attribution to the AmelliaBot interface inspiration.
- Clearer explanations for common FFmpeg and conversion errors.
- Windows one-file executable build script using PyInstaller.
- Automated tests for conversion error explanations.

### Improved
- Refined interface layout, spacing, controls, and visual consistency.
- Improved worker and conversion utility organization.
- Reduced packaged executable size by avoiding unnecessary Qt resource collection.
- Added build cleanup for temporary build files and caches.
- Expanded bilingual README with setup, usage, prerequisites, and build instructions.

### Fixed
- Various interface and conversion workflow bugs.
- Improved handling and explanation of common conversion failures.

### Requirements and notes
- FFmpeg and FFprobe must be installed separately and available on `PATH` for conversion.
- The Windows executable should be validated on Windows before distribution; the GUI build is not verified by this release archive's Linux-side checks.
