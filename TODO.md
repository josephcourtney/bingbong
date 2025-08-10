## Architecture & Reliability
- [x] Add Darwin/macOS guard early in CLI with friendly message for non-Darwin platforms
- [x] Fail fast when audio files are missing or corrupt; log meaningful error once and exit gracefully
- [x] Validate config shape in `Config.load()` and handle missing keys with clear error
- [x] Add `version` field to config for future schema changes
- [x] Implement `resume` CLI command to remove silence state
- [x] Add `silence --until "HH:MM"` convenience option
- [x] Use `slots=True` for `Config` dataclass for memory and attribute safety

## Service & Scheduling
- [x] Guard against drift in `tick()` by checking elapsed time between chime and pops
- [x] Implement optional “quiet hours” window (e.g., 22:00–07:00) to suppress chimes

## Platform / Subprocess
- [x] Check at install that AFPLAY (or `BINGBONG_PLAYER` override) exists and is executable
- [x] If `afplay` exits non-zero, log the exit code instead of failing silently

## Packaging & Resources
- [x] Ensure WAV assets are included in wheels/sdists; add test to install wheel in temp venv and assert existence
- [x] Add README note about overriding sounds with `--chime`/`--pop` and `BINGBONG_PLAYER`

## CLI UX
- [x] Improve `status` output with reasons for missing plist and display resolved player path
- [x] In `install`, echo chosen player and suggest `launchctl print gui/$UID/<label>` for troubleshooting
- [x] Add `doctor` subcommand to run platform/player/config/plist checks

## Tests
- [x] Add unit tests for corrupted `silence_until.json` handling
- [x] Add boundary tests for `silence_active(now=… )`
- [x] Add tests to verify `service.build_schedule()` generates correct 96 entries
- [x] Mock `subprocess.run` in audio tests and assert correct call counts
- [x] Add platform guard test for `install` on non-Darwin platforms
- [x] Add property tests for `compute_pop_count` at hour/quarter edges

## Code Quality & Consistency
- [x] Resolve static typing tool mismatch between `ty` and `basedpyright`
- [x] Add `__all__` to modules to control exports
- [x] Use `slots=True` for `Config`
- [x] Convert Click option paths to `Path` consistently

## Docs & Housekeeping
- [x] Expand README with install instructions, examples, troubleshooting
