## 1 • Refactor & Architecture

- **Extract core domain objects**
  - `ChimeScheduler` dataclass to own cron parsing and suppression logic.  
  - Move validation of `suppress_schedule` cron into this class.
  - Unit-test `minutes_for_chime()` & `minutes_for_suppression()`.

- **Introduce rendering strategies**
  - `PlistRenderer` protocol with `MinimalRenderer` (👍 now) and `FullRenderer` (🔮 future).  
  - `launchctl.install()` picks the renderer instead of string-concat.

- **Modular command layout**
  - Create `bingbong/commands/` package; one file per Click command: `build.py`, `doctor.py`, `logs.py`, `silence.py`, `status.py`, etc.  
  - `cli.py` becomes a thin dispatcher that imports these commands.  
  - Add `__all__` glue for auto-discovery.

- **Consolidated console helpers**
  - New module `bingbong.console` with `ok()`, `warn()`, `err()` wrappers using *rich*.  
  - Replace ad-hoc `print` / `logger.info` inside CLI.

- **Remove duplicate rebuild block**
  - Delete second “Rebuild if missing” guard in `notify.notify_time()`.

- **Replace hard-coded path in plist**
  - Render `${sys.executable}` or `shutil.which("bingbong")` into template.

- **Type safety & modern Python**
  - Add/repair annotations across `audio.py`, `ffmpeg.py`, `notify.py`.  
  - Fix `concat()` to accept `Path` not `str`.  
  - Promote `find_ffmpeg()` with `@cache` instead of global `FFMPEG`.  
  - Enable Pyright “strict” after cleanup.

---

## 2 • Features & UX

- Extend **`--dry-run`** to all commands *(unchanged)*.
- **Log enhancements** *(unchanged)*  
  - `--follow`, `--lines N`, log rotation tests.
- Rich-styled **console messaging** *(re-implement with new helpers)*.
- **Timezone & sound-path validation** *(unchanged)*.
- Shell-completion commands *(unchanged)*.
- Configurable logging/verbosity *(unchanged)*.
- Optional telemetry *(unchanged)*.

---

## 3 • Testing

- Add unit tests for `ChimeScheduler` & `PlistRenderer`
- Add tests for new console wrappers to ensure colour disable works
- Expand coverage for modularised commands (update existing tests).

---

## 4 • Cleanup

- Replace remaining `print()` / bare `logger.*` in CLI paths
- Delete legacy helpers after migration:
  - `_print_log` in old `cli.py` → move to `commands/logs.py`.
- Review for unnecessary subprocess shell calls; wrap with error handling (ongoing).

---

## 5 • Documentation

- Update README with new command paths and architecture diagram.
- Add CONTRIBUTING.md describing module layout and style conventions.
- Document public API of `ChimeScheduler` in docstrings and MkDocs site.

---
