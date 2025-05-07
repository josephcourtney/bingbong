- [ ] **Unified cron-driven engine**  
  - In `config.toml` support:  
    - `chime_schedule = "<cron-expr>"` (when to play)  
    - `suppress_schedule = ["<cron-expr>", …]` (when to silence)  
  - At install time, render both into `<StartCalendarInterval>` entries  

- [ ] **Interactive configuration wizard**  
  - Scan or initialize `~/.config/bingbong/config.toml`  
  - Prompt for:  
    - Chime schedule (cron)  
    - Suppression windows (daily quiet hours or cron)  
    - Respect system DND?  
    - Time-zone override (optional)  
    - Custom sounds (paths or bundled options)  
  - Validate inputs and emit a complete config file  

- [ ] **Enhanced status output**  
  - Show next scheduled chime and any upcoming suppression window  
  - If a temporary pause is active, display remaining time  

- [ ] **Volume control & ducking**  
  - Integrate with CoreAudio to lower other audio streams while chime plays  

- [ ] **Better logging & diagnostics**  
  - Write to `~/Library/Logs/bingbong.log` or use Unified Logging (`os_log`)  
  - Rotate logs and integrate with Console.app  

- [ ] **Sleep/wake handling**  
  - Record last-run timestamp in state file  
  - On wake, optionally play any missed chimes  

- [ ] **Documentation & examples**  
  - Expand README with:  
    - Cron-syntax examples for chimes and suppression  
    - Quiet-hours recipes  
    - Automator/Shortcuts integration  
    - Troubleshooting tips  
