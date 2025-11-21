## Battery Monitor (Windows)

Monitors your laptop and phone batteries every 30 seconds and beeps when they reach a threshold (default 95%). You can change the threshold live while it runs. It also reports how long it took to reach the threshold from when monitoring started or since you last changed the threshold.

### Features
- **Dual Device Support**: Monitors both laptop and phone batteries (phone via ADB)
- **Detailed Battery Info**: Shows voltage, temperature, health status, and battery technology
- **Beep alert** when battery reaches the threshold
- **Windows Notification** when battery reaches the threshold
- **Web Interface**: Real-time battery status display with percentage, difference, and time to 80%
- Poll every 30 seconds (configurable)
- Live update threshold via console command: `set 90`
- Shows elapsed time to reach the threshold
- Logs 1-minute battery percentage difference (Δ1m) during monitoring
- Displays min/max Δ1m values when showing total time to reach threshold
- **Phone Monitoring**: Automatically detects and monitors connected Android phones via ADB when charging
- **Battery Health**: Calculates and displays battery health based on capacity degradation

### Requirements
- Windows (beep uses `winsound`)
- Python 3.9+
- **For phone monitoring**: Android Debug Bridge (ADB) - Install [Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools)

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

# With web interface:
python app.py --web
```

### While Running
- Type `set <percent>` to change threshold (e.g., `set 90`).
- Type `quit` to exit.
 - When threshold is reached while plugged in, it will beep 5 times and show options:
   - Type `snooze` to mute alerts for 1 minute.
   - Type `dismiss` to silence until battery drops below threshold and rises again (requires unplugging charger first).

#### Output Examples

**Laptop Battery Monitoring:**

Regular status lines (every poll) with detailed info:

```text
[14:07:12] Laptop Battery: 62% | Plugged | Threshold: 80% | 11.10V, 35.2°C, Lithium-ion
[14:08:12] Laptop Battery: 65% | Plugged | Threshold: 80% | 11.15V, 36.1°C, Lithium-ion
```

With degraded battery health:

```text
[14:09:12] Laptop Battery: 68% | Plugged | Threshold: 80% | 11.20V, 36.5°C, Lithium-ion, Health: Degraded (78.5%)
```

**Phone Battery Monitoring:**

When phone is connected and charging:

```text
Phone connected: ABC123XYZ (Li-ion)
[14:07:12] Phone Battery: 85% | Charging | Threshold: 80% | 4.15V, 32.5°C, Li-ion
[14:08:12] Phone Battery: 87% | Charging | Threshold: 80% | 4.18V, 33.1°C, Li-ion
```

With health warnings:

```text
[14:09:12] Phone Battery: 89% | Charging | Threshold: 80% | 4.20V, 45.2°C, Li-ion, Health: Overheat
```

**1-Minute Difference Tracking:**

Every full minute, a 1-minute difference is printed:

```text
[14:08:12] Δ1m: +1.0%
```

When the threshold is reached, total time and min/max Δ1m are shown:

```text
[14:15:12] Laptop Battery: 80% | Plugged | Threshold: 80% | Time to reach: 8m 0s | Δ1m min: +0.8% max: +1.3%
```

### Web Interface

The application includes a web interface that displays real-time battery information:

- Battery percentage (font size 50)
- Difference from start percentage
- Estimated time to reach 80% (font size 20)
- Windows notification when battery reaches threshold

To start the web interface, use the `--web` flag:

```bash
python app.py --web
```

The web interface will be available at http://127.0.0.1:5000 and will automatically open in your default browser.

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
- **Phone Monitoring**: The app automatically prioritizes phone battery monitoring when a phone is connected via ADB and charging. If no phone is detected, it falls back to laptop monitoring.
- **Battery Details**: Voltage, temperature, and health information are retrieved from Windows WMI (laptop) and ADB (phone). Some information may not be available on all systems.
- **Temperature**: Laptop temperature availability depends on hardware/drivers. Phone temperature is available via ADB.
- Δ1m values use battery percentage. Voltage is now displayed but differences are calculated using percentage per minute.

### FAQ

**Q: How do I enable phone battery monitoring?**

A: Install Android SDK Platform Tools and ensure ADB is in your PATH. Connect your phone via USB, enable USB debugging, and when the phone is charging, the app will automatically detect and monitor it.

**Q: Why does the app show percentage differences and not voltage differences?**

A: While voltage is now displayed for both devices, Δ1m is calculated using percentage per minute for consistency and because percentage changes are more meaningful for monitoring charging progress.

**Q: My poll interval isn't exactly 60s. Will Δ1m still work?**

A: Yes. The app tracks an internal 1-minute anchor and will print Δ1m once each full minute has elapsed since the last anchor. If your poll interval is longer than 60s, the Δ1m line may appear on the next update after a minute (or more) has passed.

**Q: Does Δ1m track when discharging too?**

A: It records percent changes continuously, whether plugged in or on battery. Positive values typically indicate charging; negative values indicate discharging.

**Q: Why don't I see temperature for my laptop?**

A: Temperature availability depends on your laptop's hardware and drivers. The app tries multiple WMI sources, but some systems don't expose battery temperature. Phone temperature is available via ADB when supported.

**Q: What does "Health: Degraded" mean?**

A: For laptops, health is calculated from design capacity vs. full charge capacity. If the battery can only hold less than 80% of its original capacity, it's marked as degraded. For phones, health status comes directly from the Android system.

