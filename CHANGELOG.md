## [0.2.3] - 2025-08-10

### Added
- add resume CLI command
- add `silence --until` option
- add `doctor` subcommand for diagnostics
- add optional quiet hours via `BINGBONG_QUIET_HOURS`
- add Darwin platform guard and audio player checks
- add versioned, slotted `Config`
- add `__all__` exports across modules

### Fixed
- fail fast when audio files are missing or player exits non-zero
- validate config shape and handle corrupted silence state
- guard against drift between chime and pops
- ensure wav assets are packaged in wheels

### Changed
- convert CLI path options to `Path`
- improve status and install messages
