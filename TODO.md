## Architecture & Reliability
- [ ] Add Darwin/macOS guard early in CLI with friendly message for non-Darwin platforms
- [ ] Fail fast when audio files are missing or corrupt; log meaningful error once and exit gracefully
- [ ] Validate config shape in `Config.load()` and handle missing keys with clear error
- [ ] Add `version` field to config for future schema changes
- [ ] Implement `resume` CLI command to remove silence state
- [ ] Add `silence --until "HH:MM"` convenience option
- [ ] Use `slots=True` for `Config` dataclass for memory and attribute safety

## Service & Scheduling
- [ ] Guard against drift in `tick()` by checking elapsed time between chime and pops
- [ ] Implement optional “quiet hours” window (e.g., 22:00–07:00) to suppress chimes

## Platform / Subprocess
- [ ] Check at install that AFPLAY (or `BINGBONG_PLAYER` override) exists and is executable
- [ ] If `afplay` exits non-zero, log the exit code instead of failing silently

## Packaging & Resources
- [ ] Ensure WAV assets are included in wheels/sdists; add test to install wheel in temp venv and assert existence
- [ ] Add README note about overriding sounds with `--chime`/`--pop` and `BINGBONG_PLAYER`

## CLI UX
- [ ] Improve `status` output with reasons for missing plist and display resolved player path
- [ ] In `install`, echo chosen player and suggest `launchctl print gui/$UID/<label>` for troubleshooting
- [ ] Add `doctor` subcommand to run platform/player/config/plist checks

## Tests
- [ ] Add unit tests for corrupted `silence_until.json` handling
- [ ] Add boundary tests for `silence_active(now=…)`
- [ ] Add tests to verify `service.build_schedule()` generates correct 96 entries
- [ ] Mock `subprocess.run` in audio tests and assert correct call counts
- [ ] Add platform guard test for `install` on non-Darwin platforms
- [ ] Add property tests for `compute_pop_count` at hour/quarter edges

## Code Quality & Consistency
- [ ] Resolve static typing tool mismatch between `ty` and `basedpyright`
- [ ] Add `__all__` to modules to control exports
- [ ] Use `slots=True` for `Config`
- [ ] Convert Click option paths to `Path` consistently

## Docs & Housekeeping
- [ ] Expand README with install instructions, examples, troubleshooting
