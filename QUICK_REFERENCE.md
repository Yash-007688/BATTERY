# Battery Monitor - Quick Reference Guide

## 🚀 Quick Start

### First Time Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# OR use the setup script
setup.bat

# 2. Run with web interface
python app_enhanced.py --web

# 3. Open browser to http://127.0.0.1:5000
```

### Daily Use
```bash
# Console only
python app_enhanced.py

# Web interface
python app_enhanced.py --web

# Web + System Tray
python app_enhanced.py --web --tray

# Custom threshold
python app_enhanced.py 85 --web

# Use specific profile
python app_enhanced.py --web --profile work
```

---

## ⌨️ Console Commands

While the app is running, type these commands:

| Command | Description |
|---------|-------------|
| `set 90` | Change threshold to 90% |
| `snooze` | Mute alerts for 1 minute |
| `dismiss` | Silence until battery drops below threshold |
| `stats` | Show 24-hour battery statistics |
| `health` | Show battery health information |
| `devices` | List all monitored devices |
| `profile work` | Switch to 'work' profile |
| `quit` | Exit the application |

---

## 🌐 Web Interface

### Access
- **URL**: [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **Features**: Real-time updates, charts, statistics, settings

### Dashboard Sections
1. **Battery Display** - Current percentage with animated icon
2. **Statistics** - Avg battery, cycles, health, charge time
3. **Battery History Chart** - Last 20 data points
4. **Recent Notifications** - Alert history
5. **Quick Settings** - Threshold, polling, preferences

### Theme Toggle
- Click **🌙 Dark** / **☀️ Light** button in header
- Preference saved in browser localStorage

---

## 📱 Phone Monitoring

### Setup ADB
1. Download [Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools)
2. Extract and add to system PATH
3. Enable USB Debugging on phone (Settings → Developer Options)
4. Connect phone via USB
5. Authorize computer on phone
6. Start charging - app will auto-detect!

### Verify ADB
```bash
adb devices
# Should show your device
```

---

## 🔔 Notification Setup

### Desktop Notifications
✅ Enabled by default - no setup needed!

### Email Notifications
```python
# Edit battery_config.json or use web settings
{
  "profiles": {
    "default": {
      "enable_email": true,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_username": "your_email@gmail.com",
      "smtp_password": "your_app_password",
      "email_address": "your_email@gmail.com"
    }
  }
}
```

**Gmail Users**: Use [App Password](https://support.google.com/accounts/answer/185833), not regular password!

### SMS Notifications
1. Sign up for [Twilio](https://www.twilio.com/) (free trial available)
2. Get Account SID, Auth Token, and phone number
3. Configure in profile:
```python
{
  "enable_sms": true,
  "twilio_account_sid": "ACxxxxx",
  "twilio_auth_token": "your_token",
  "twilio_from_number": "+1234567890",
  "phone_number": "+0987654321"
}
```

### Custom Sounds
1. Place `.wav` files in `sounds/` directory
2. Set in profile:
```python
{
  "custom_sound_path": "C:/path/to/sounds/alert.wav"
}
```

---

## 👤 Configuration Profiles

### Built-in Presets

| Profile | Threshold | Polling | Notifications | Use Case |
|---------|-----------|---------|---------------|----------|
| `conservative` | 80% | 30s | All enabled | Daily use, battery health |
| `aggressive` | 95% | 60s | Desktop only | Maximum charge |
| `gaming` | 85% | 45s | Silent | Gaming sessions |
| `overnight` | 80% | 120s | Silent | Overnight charging |
| `work` | 80% | 30s | Email + Desktop | Work hours |

### Create Custom Profile
```bash
# Via console
python
>>> from config_manager import ConfigManager
>>> config = ConfigManager()
>>> config.create_profile('my_profile', threshold_percent=85, poll_interval_seconds=45)
>>> config.set_active_profile('my_profile')
```

### Switch Profiles
```bash
# Command line
python app_enhanced.py --profile gaming

# While running
profile gaming
```

---

## 🖥️ System Tray

### Enable
```bash
python app_enhanced.py --tray
```

### Tray Menu
- **Battery: X%** - Current level
- **Charging/On Battery** - Status
- **Set Threshold** → 80%, 85%, 90%, 95%
- **Snooze Alerts** - Mute for 1 minute
- **Dismiss Alerts** - Silence until drop
- **Open Dashboard** - Launch web UI
- **Settings** - Open settings page
- **Exit** - Close application

### Icon Colors
- 🟢 **Green**: 80-100%
- 🟡 **Yellow**: 50-79%
- 🟠 **Orange**: 20-49%
- 🔴 **Red**: 0-19%

---

## ⏰ Auto-Start Setup

### Install
```bash
python app_enhanced.py --install-startup
```

This creates a Windows Task Scheduler task that:
- Runs on login
- Starts with web interface and tray
- Runs in background

### Remove
```bash
python app_enhanced.py --remove-startup
```

### Verify
1. Open Task Scheduler (Win + R → `taskschd.msc`)
2. Look for "BatteryMonitorAutoStart"

---

## 📊 Database & Analytics

### Database Location
- **File**: `battery_monitor.db` (SQLite)
- **Location**: Same directory as app

### View Data
```python
from database import DatabaseManager

db = DatabaseManager()

# Get statistics
stats = db.get_reading_stats('laptop_default', hours=24)
print(stats)

# Get charge history
cycles = db.get_charge_history('laptop_default', limit=10)
for cycle in cycles:
    print(f"{cycle.start_percentage}% → {cycle.end_percentage}% in {cycle.duration_seconds}s")
```

### Cleanup Old Data
```python
db.cleanup_old_data(days=30)  # Keep last 30 days
```

### Export Data
```bash
# Via web interface: Click "Export Data" button
# Exports to JSON/CSV
```

---

## 🧠 ML Predictions

### How It Works
- Trains on your historical charge cycles
- Uses polynomial regression for accuracy
- Improves over time with more data
- Provides confidence scores

### Requirements
- Minimum 5 complete charge cycles
- Better accuracy with 20+ cycles
- Retrains automatically after each cycle

### View Predictions
- Shown in console: `Est. time: 45min (conf: 85%)`
- Updates every poll when charging

---

## 🔧 Troubleshooting

### Phone Not Detected
```bash
# Check ADB
adb devices

# If empty:
# 1. Enable USB Debugging on phone
# 2. Reconnect USB cable
# 3. Authorize computer on phone
# 4. Try different USB port/cable
```

### Web Interface Won't Load
```bash
# Check if port 5000 is in use
netstat -ano | findstr :5000

# Try different port (edit app_enhanced.py)
# Or kill process using port 5000
```

### Email Not Sending
- ✅ Check SMTP settings
- ✅ For Gmail, use App Password
- ✅ Check firewall/antivirus
- ✅ Test with: `telnet smtp.gmail.com 587`

### System Tray Not Working
```bash
# Install dependencies
pip install pystray Pillow

# Run with --tray flag
python app_enhanced.py --tray
```

### Database Errors
```bash
# Backup database
copy battery_monitor.db battery_monitor_backup.db

# Delete and recreate
del battery_monitor.db
python app_enhanced.py
```

---

## 📁 File Structure

```
BATTERY/
├── app_enhanced.py          # Main application (use this!)
├── app_original.py          # Original version (backup)
├── models.py                # Database models
├── database.py              # Database manager
├── notifications.py         # Notification system
├── ml_predictor.py          # ML & health analysis
├── device_manager.py        # Multi-device management
├── config_manager.py        # Configuration system
├── scheduler.py             # Scheduling & auto-start
├── tray_app.py             # System tray app
├── battery_config.json      # Configuration file
├── battery_monitor.db       # SQLite database
├── requirements.txt         # Python dependencies
├── setup.bat               # Quick setup script
├── README.md               # Full documentation
├── CHANGELOG.md            # Version history
├── templates/
│   └── index.html          # Web dashboard
├── static/
│   ├── css/styles.css      # UI styles
│   └── js/app.js           # WebSocket client
└── sounds/                  # Custom alert sounds
```

---

---

## 💡 Pro Tips

### Maximize Battery Life
1. Set threshold to 80% (conservative profile)
2. Enable adaptive polling
3. Use scheduled monitoring for overnight
4. Monitor battery health regularly

### Best Performance
1. Use adaptive polling (faster when near threshold)
2. Set reasonable poll interval (30s default)
3. Cleanup old data periodically
4. Use system tray to minimize resource usage

### Multiple Devices
1. Enable priority for main device
2. Set different thresholds per device
3. Use device comparison view
4. Monitor health for all devices

### Notifications
1. Use desktop for immediate alerts
2. Add email for important thresholds
3. SMS for critical alerts only
4. Custom sounds for different scenarios

---

## 🆘 Getting Help

### Check Logs
- Console output shows all operations
- Database logs all notifications
- WebSocket errors in browser console

### Common Issues
1. **"Battery info not available"** → Check psutil installation
2. **"ADB not found"** → Install Android SDK Platform Tools
3. **"Port already in use"** → Change port or kill process
4. **"Import error"** → Run `pip install -r requirements.txt`

### Resources
- **README.md** - Full documentation
- **CHANGELOG.md** - Version history
- **walkthrough.md** - Implementation details

---

## 🎯 Recommended Setup

### For Daily Use
```bash
python app_enhanced.py --web --tray --profile conservative
```

### For Overnight
```bash
python app_enhanced.py --profile overnight
```

### For Work
```bash
python app_enhanced.py --web --profile work
```

### For Gaming
```bash
python app_enhanced.py --tray --profile gaming
```

---

# Happy Monitoring! 🔋⚡
