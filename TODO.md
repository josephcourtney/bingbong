- Improve timezone & sound-path validation in `configure()`
- Implement shell-completion commands
- Unify output and logging so that formatting, dealing with verbosity, etc can be dealt with in one place
- Update README
- Add docstrings for `ChimeScheduler` public API

- **General clean-ups**
  - Convert repetitive dry-run checks into a reusable `@dryable` decorator.
  - Harden suppression-window parsing to handle overnight ranges (e.g. `22:00-02:00`).
  - Remove `_render_minimal_start_calendar_interval_plist` (dead code).
  - Introduce domain-specific `BingBongError` exceptions and replace bare `RuntimeError` / `ValueError`.
  - Replace library-level `print()` calls with structured logging or a result object consumed by the CLI.
  - Use `pathlib.Path` consistently (e.g. `ffmpeg.concat` inputs).
  - Add explicit return-type annotations for Click commands.

- **Audio / FFmpeg**
  - Wrap FFmpeg interaction in an injectable `FFmpeg` class to improve testability and decouple subprocess logic.

- **Tests**
  - Add a round-trip test: render the launchd plist, then verify with `plistlib.loads()` that it is valid XML.
  - Expand CI matrix (tox/nox) to run tests on both macOS and Linux; skip launchd-specific tests where unsupported.

- **State management**
  - Consolidate `.pause_until` and `.last_run` into a single JSON store to avoid multiple sentinel files.

- **CI / Tooling**
  - Gate Ruff and Pyright in GitHub Actions.
