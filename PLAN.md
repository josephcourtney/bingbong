This document outlines a step-by-step approach for implementing the items listed in `TODO.md`.
Each major feature will be delivered using a test-driven development (TDD) workflow:
1. Write failing tests that capture the desired behaviour.
2. Implement the minimal code required for the tests to pass.
3. Refactor for clarity and maintainability.
4. Repeat until all tasks are complete.

## 1. `--dry-run` Flag
- **Tests**: Add CLI tests to verify that each subcommand accepts `--dry-run`, performs no side effects and prints the actions that would occur.
- **Implementation**:
  - Introduce a global option on the Click group that stores a flag in the context object.
  - Update subcommands to branch on this flag; when enabled, skip file writes or system calls and collect messages about intended actions.
  - After command execution, output the collected actions.

## 2. `configure` Subcommand
- **Tests**:
  - Use `CliRunner` to simulate user interaction with prompts.
  - Verify that valid input produces a config file in either the existing path or the default location.
  - Confirm that invalid input (bad cron, malformed time range) causes the command to exit with an error.
- **Implementation**:
  - Create a configuration data class for schedule, suppression windows, timezone and custom sounds.
  - Implement interactive prompts using Click’s `prompt` and `confirm` helpers.
  - Display a summary table of changes with rich formatting and ask for confirmation before writing.
  - Persist configuration to the current or default config file.

## 3. Enhanced `status`
- **Tests**:
  - Mock time and configuration to check that the next scheduled chime, active suppression source and config path are reported.
- **Implementation**:
  - Load the configuration file and compute the next chime based on the schedule.
  - Detect manual pause vs. Do‑Not‑Disturb and report which is active.
  - Show the resolved configuration path.

## 4. Consistent Messaging
- **Tests**: Ensure every CLI output begins with `OK:`, `WARN:` or `ERROR:` depending on the situation.
- **Implementation**:
  - Add helper functions for formatted messages and error handling at startup for missing dependencies.
  - Capture and display rebuild results explicitly.

## 5. Unified `silence` Command
- **Tests**:
  - Verify `silence --minutes` and `silence --until` create or remove the pause file appropriately and toggle state if already silenced.
- **Implementation**:
  - Merge `pause` and `unpause` into a single command with auto‑toggle logic.
  - Support both time‑based options.

## 6. Log Management
- **Tests**:
  - Cover `logs --follow` and `logs --lines` behaviour.
  - Ensure logs rotate once exceeding `LOG_ROTATE_SIZE` and rotated files appear in `status` and `doctor` output.
- **Implementation**:
  - Use `tail -n` and file watching for `--follow`.
  - Implement rotation when the log file exceeds the threshold.

## 7. `rich` Output and `--no-color`
- **Tests**:
  - Validate coloured output for success, warning and error cases.
  - Confirm `--no-color` disables styling.
- **Implementation**:
  - Integrate the `rich` library for all console rendering and align table widths.
  - Provide a global `--no-color` option that sets the appropriate environment variable for rich.

## 8. Documentation and Examples
- **Tests**: Parse README code blocks with `croniter` (existing tests already cover this) and ensure examples stay valid.
- **Implementation**:
  - Expand README with a quickstart section, configuration templates and explanation of XDG paths vs. macOS defaults.

## 9. Shell Completions
- **Tests**: Use `CliRunner` to invoke the completion commands for bash, zsh, fish and PowerShell and verify output is produced.
- **Implementation**: Leverage Click’s shell completion feature to generate scripts and document installation steps.

## 10. Version Reporting
- **Tests**: Assert that `bingbong --version` or `bingbong version` prints the package version string.
- **Implementation**: Add a `--version` option using Click’s `version_option` helper or a dedicated subcommand.

## 11. Configurable Logging
- **Tests**: Provide a temporary config that sets custom log paths and verbosity; verify log files are created at the specified locations.
- **Implementation**: Extend the configuration schema to include log path and log level, and update logging setup accordingly.

## 12. Expanded Test Suite
- **Tests**: Add coverage for all new commands, options and edge cases introduced above. Use fixtures to isolate filesystem and environment interactions.
- **Implementation**: Continue using TDD for each new behaviour to maintain high coverage.

## 13. Optional Telemetry
- **Tests**: Ensure telemetry is disabled by default and only active when the user opts in via config. Mock the network sender and assert that errors do not prevent core functionality.
- **Implementation**: Implement a lightweight telemetry module that records errors and usage statistics when enabled.

## 14. README Updates
- **Tests**: Existing documentation tests already parse cron snippets. Extend them to verify that the documented configuration schema matches the implementation.
- **Implementation**: Document audio backend requirements, describe each config field and provide example configs.
