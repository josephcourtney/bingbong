# bingbong

**bingbong** is a macOS background utility that chimes like a clock—playing a distinct sound at the hour and quarter-hour marks.

## Features

- Plays customizable audio notifications:
  - On the hour: one chime plus a sequence of "pop" sounds indicating the hour (e.g., 3 PM = chime + 2 pops).
  - On the quarter-hour: 1–3 pops for 15, 30, and 45 minutes past the hour.
- Ships prebuilt audio files and copies them into place via `bingbong build` (no ffmpeg required).
- Runs automatically via `launchctl` with logs and diagnostics.
- Fully tested with `pytest` and `freezegun`.

## Installation

Ensure Python ≥ 3.13 is installed.

```bash
uv tool install git+https://github.com/josephcourtney/bingbong.git
bingbong build
bingbong install
bingbong doctor
```

## CLI Usage

```bash
bingbong build      # Generate audio files
bingbong install    # Set up launchctl service
bingbong uninstall  # Remove launchctl service
bingbong chime      # Manually play current time chime
bingbong clean      # Remove generated audio
bingbong logs       # Show service logs
bingbong doctor     # Run system diagnostics
```

### Advanced options

The `install` command accepts several flags for tuning launchd behavior:

- `--exit-timeout <seconds>`
- `--throttle-interval <seconds>`
- `--successful-exit/--no-successful-exit`
- `--crashed/--no-crashed`
- `--backoff <seconds>` to restart after crashes with a delay

The configuration file `config.toml` contains:

```toml
suppress_schedule = ["08:00-09:00", "22:00-23:00"]
respect_dnd = true
timezone = "America/New_York"
custom_sounds = ["~/Music/chime.wav", "~/Music/pop.wav"]
```

- **Fixed schedule:** Bingbong chimes on the quarter-hour (00, 15, 30, 45) — no cron expression is needed.
- `suppress_schedule`: List of time ranges in `HH:MM-HH:MM` format when chimes should be suppressed.
- `respect_dnd`: If `true`, bingbong will not chime during macOS Do Not Disturb (Focus) mode.
- `timezone`: Optional. Sets the timezone for suppression windows.
- `custom_sounds`: Optional list of custom audio file paths to replace default sounds.


The launchd service watches this file and reloads itself when it changes.

Chime selection can be customised by providing a strategy object to `notify.notify_time()`. The default `QuarterHourPolicy` plays a chime on the hour and pop clusters on quarter-hours, but other policies can be injected for different schedules.

To temporarily pause chimes:

```bash
bingbong silence --minutes 10  # pause for ten minutes
bingbong silence               # toggle to resume
```

All chime events are logged via the internal console/logger and include ISO timestamps and the file played.
