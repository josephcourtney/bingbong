# bingbong

**bingbong** is a macOS background utility that chimes like a clock—playing a distinct sound at the hour and quarter-hour marks.

## Installation

```bash
uv tool install bingbong
```

## Usage

Install the launchd service:

```bash
bingbong install
```

Override sounds or player:

```bash
bingbong install --chime /path/to/chime.wav --pop /path/to/pop.wav
# or
BINGBONG_PLAYER=/path/to/player bingbong install
```

Temporarily silence chimes:

```bash
bingbong silence --minutes 30
bingbong silence --until 22:00
bingbong resume
```

Check status or run diagnostics:

```bash
bingbong status
bingbong doctor
```

## Troubleshooting

If install fails, verify the audio player path and review launchd logs:

```bash
launchctl print gui/$UID/com.bingbong.chimes
```
