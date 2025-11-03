## Battery Monitor (Windows)

Monitors your laptop battery every 30 seconds and beeps when it reaches a threshold (default 95%). You can change the threshold live while it runs. It also reports how long it took to reach the threshold from when monitoring started or since you last changed the threshold.

### Features
- Beep alert when battery reaches the threshold
- Poll every 30 seconds (configurable)
- Live update threshold via console command: `set 90`
- Shows elapsed time to reach the threshold

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


