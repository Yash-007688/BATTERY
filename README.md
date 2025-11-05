## Battery Monitor (Windows)

Monitors your laptop battery every 30 seconds and beeps when it reaches a threshold (default 95%). You can change the threshold live while it runs. It also reports how long it took to reach the threshold from when monitoring started or since you last changed the threshold.

### Features
- Beep alert when battery reaches the threshold
- Poll every 30 seconds (configurable)
- Live update threshold via console command: `set 90`
- Shows elapsed time to reach the threshold
- Logs 1-minute battery percentage difference (Δ1m) during monitoring
- Displays min/max Δ1m values when showing total time to reach threshold

### Requirements
- Windows (beep uses `winsound`)
- Python 3.9+

Install dependencies:

```bash
pip install -r requirements.txt
```

### Run

```bash
python app.py
```

Optional CLI overrides:

```bash
python app.py 90 20
#     threshold%   poll interval in seconds

# With flags (percent sign supported):
python app.py -f 95% -n 85%
# -n (new) overrides -f (from) if both provided
```

### While Running
- Type `set <percent>` to change threshold (e.g., `set 90`).
- Type `quit` to exit.
 - When threshold is reached while plugged in, it will beep 5 times and show options:
   - Type `snooze` to mute alerts for 1 minute.
   - Type `dismiss` to silence until battery drops below threshold and rises again (requires unplugging charger first).

#### New output examples

Regular status lines (every poll):

```text
[14:07:12] Battery: 62% | Plugged | Threshold: 80%
```

Every full minute, a 1-minute difference is printed:

```text
[14:08:12] Δ1m: +1.0%
```

When the threshold is reached, total time and min/max Δ1m are shown:

```text
[14:15:12] Battery: 80% | Plugged | Threshold: 80% | Time to reach: 8m 0s | Δ1m min: +0.8% max: +1.3%
```

### Configuration File
`battery_config.json`

```json
{
  "threshold_percent": 95,
  "poll_interval_seconds": 30
}
```

Edits to this file persist between runs. Live changes while the app is running should be done with the `set` command.

### Notes
- If the battery is already above the threshold when you change it, the app alerts immediately and records that as the reach time.
- If battery info is not available on your system, the app will print a warning.
- Δ1m values use battery percentage. Windows `psutil` does not expose battery voltage; voltage differences are not available.


