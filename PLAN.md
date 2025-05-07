## Internal Improvements

1. **Release Automation for PyPI**

   - **Effort:** Low
   - **Impact:** High
   - Add a GitHub Action (or UV CI) that on each tagged commit runs `build`, `twine check`, and `twine upload`. Improves release cadence and reduces manual mistakes.

2. **Better Logging Infrastructure**

   - **Effort:** Low
   - **Impact:** Moderate
   - Swap ad-hoc `print` for Python’s `logging` with adjustable levels (INFO/WARN/ERROR) and simple rotation. Optional flag to increase verbosity.

3. **Edge-Case & Property-Based Tests**

   - **Effort:** Low → Moderate
   - **Impact:** Moderate
   - Bundle a few Hypothesis tests around `nearest_quarter` and random minute inputs to catch off-by-ones beyond fixed boundaries.

4. **Type Annotations & Static Checking**

   - **Effort:** Moderate
   - **Impact:** Moderate
   - Add return‐type hints everywhere and enable mypy in CI. Catches signature mismatches early.

5. **Dependency Injection for Subprocess/FFmpeg Calls**

   - **Effort:** Moderate
   - **Impact:** Moderate
   - Abstract out calls to `subprocess.run` and `shutil.which` behind an interface injectable in tests—simplifies monkeypatching and future backends.

6. **Configuration Schema & Validation**

   - **Effort:** Moderate
   - **Impact:** Moderate
   - Formalize `~/.config/bingbong/config.toml` (or `.yaml`) with a library like `pydantic`. Validates user edits and surfaces clear errors.

7. **CI Quality Gates & Mutation Testing**
   - **Effort:** High
   - **Impact:** Moderate
   - Enforce minimum coverage threshold and optionally integrate a mutation testing tool to surface hidden edge cases.

---

## External Features & UX

1. **Graceful FFmpeg-Missing Guidance**

   - **Effort:** Low
   - **Impact:** High
   - Catch FFmpeg failures in `install`/`build` and print actionable hints (e.g. `brew install ffmpeg`) instead of raw tracebacks.

2. **Suppress Chime on Screen-Lock**

   - **Effort:** Moderate
   - **Impact:** High
   - On macOS, detect screen-locked state (CGSession or similar) and skip all alerts while locked.

3. **Windows Service Support**

   - **Effort:** High
   - **Impact:** High
   - Provide a Windows Scheduled Task installer or a tiny tray app wrapper so BingBong can run on Windows without code‐duplication.

4. **Pluggable Sound Packs**

   - **Effort:** Moderate
   - **Impact:** High
   - Let users drop in `hour_N.wav`/`quarter_N.wav` (or named packs) into a `sounds/` folder; auto-detect and fallback to built-in if absent.

5. **Configurable Intervals & Quiet-Hours**

   - **Effort:** Moderate
   - **Impact:** High
   - In the user config file, allow arbitrary cron-style schedules or disable individual quarters; add a DND-respect flag.

6. **Interactive `bingbong configure` Wizard**

   - **Effort:** Moderate
   - **Impact:** Moderate
   - A CLI subcommand that walks users through setting sound packs, schedules, and DND windows, then writes a validated config.

7. **Enhanced `doctor` & `logs` UX**

   - **Effort:** Low
   - **Impact:** Moderate
   - Expand `doctor` with clearer suggestions (e.g. “FFmpeg found at /usr/bin/ffmpeg”), colorize pass/fail. Let `logs --follow` tail in real time.

8. **Expanded README & Troubleshooting Guide**
   - **Effort:** Low
   - **Impact:** Moderate
   - Add sections on Windows setup, common LaunchAgents permissions, missing-FFmpeg fixes, and examples of custom sound packs.
