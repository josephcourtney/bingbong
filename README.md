# bingbong

**bingbong** is a macOS background utility that chimes like a clock—playing a distinct sound at the hour and quarter-hour marks.

## Features

- Plays customizable audio notifications:
  - On the hour: one chime plus a sequence of "pop" sounds indicating the hour (e.g., 3 PM = chime + 2 pops).
  - On the quarter-hour: 1–3 pops for 15, 30, and 45 minutes past the hour.
- Builds audio files from bundled resources using `ffmpeg`.
- Runs automatically via `launchctl` with logs and diagnostics.
- Fully tested with `pytest` and `freezegun`.

## Installation

Ensure Python ≥ 3.13 and `ffmpeg` are installed.

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
