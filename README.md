# Battery Monitor - Enhanced Edition 🔋

A comprehensive, feature-rich battery monitoring application for Windows with real-time web dashboard, ML predictions, multi-device support, and advanced notifications.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.9+-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

## ✨ Features

### Core Monitoring
- **Dual Device Support**: Monitor both laptop and Android phones (via ADB)
- **Real-time Tracking**: Battery percentage, voltage, temperature, and health status
- **Smart Alerts**: Customizable threshold notifications with snooze/dismiss
- **Variable Threshold**: Set custom threshold via command line (e.g., `-t 80` or `-t 100`)
- **Charge Cycle Tracking**: Automatic detection and logging of charge cycles
- **1-Minute Delta Tracking**: Monitor charging/discharging rates

### 🎨 Modern Web Interface
- **Real-time Dashboard**: WebSocket-powered live updates
- **Glassmorphism Design**: Beautiful, modern UI with dark mode support
- **Interactive Charts**: Battery history visualization with Chart.js
- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Statistics Panel**: 24-hour averages, charge cycles, health scores

### 🧠 Smart Features
- **ML Predictions**: Machine learning-based charge time estimation
- **Adaptive Polling**: Faster updates when near threshold
- **Battery Health Analysis**: Degradation tracking and recommendations
- **Optimal Charging Suggestions**: Tips for battery longevity

### 🔔 Advanced Notifications
- **Desktop Notifications**: Windows toast notifications
- **Custom Sounds**: Configurable alert sounds
- **Email Alerts**: SMTP-based email notifications
- **SMS Alerts**: Twilio-powered SMS notifications
- **Notification History**: Complete log of all alerts

### 📱 Multi-Device Management
- **Multiple Phones**: Monitor several Android devices simultaneously
- **Device Profiles**: Individual settings per device
- **Priority System**: Auto-select which device to monitor
- **Comparison View**: Side-by-side device statistics

### 🖥️ System Tray Integration
- **Dynamic Icon**: Shows current battery percentage
- **Quick Actions**: Change threshold, snooze, dismiss from tray
- **Color-coded**: Green/yellow/red based on battery level
- **Minimize to Tray**: Run in background

### ⏰ Automation & Scheduling
- **Scheduled Monitoring**: Start/stop at specific times
- **Auto-start**: Windows Task Scheduler integration
- **Profile Switching**: Different settings for different scenarios

### ⚙️ Configuration Profiles
- **Multiple Profiles**: Work, gaming, overnight, etc.
- **Preset Configurations**: Quick setup with templates
- **Import/Export**: Share settings between machines
- **Live Switching**: Change profiles without restart

### 📊 Data Management
- **SQLite Database**: Persistent storage of all readings
- **Historical Analytics**: Trends and patterns over time
- **Data Export**: CSV/JSON export capabilities
- **Auto-cleanup**: Configurable data retention

## 🚀 Quick Start

### Prerequisites
- Windows 10/11
- Python 3.9 or higher
- **For phone monitoring**: [Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools) (ADB)

### Installation

1. **Clone or download** this repository

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Run the application**:

**Console only** (original mode):
```bash
python app_enhanced.py
```

**With web interface**:
```bash
python app_enhanced.py --web
```

**With web + system tray**:
```bash
python app_enhanced.py --web --tray
```

**Lightweight original script (`app.py`)** – starts CLI + web dashboard:
```bash
python app.py                    # opens http://127.0.0.1:5000 by default
python app.py --no-web           # CLI only if you don't want the dashboard
python app.py -t 90              # Set threshold to 90%
python app.py -s 60              # Poll every 60 seconds (1 minute)
python app.py -s 3600            # Poll every 3600 seconds (1 hour)
python app.py -d                  # Run in discharge calculation mode
python app.py --discharge-mode   # Alternative form for discharge mode
```

**Install auto-start**:
```bash
python app_enhanced.py --install-startup
```

### First Run

On first run, the application will:
1. Create a SQLite database (`battery_monitor.db`)
2. Initialize default configuration profile
3. Start monitoring with default settings (80% threshold, 30s polling)

## 📖 Usage

The application provides multiple modes to suit different needs:

### Standard Mode
Monitor battery with threshold alerts and web dashboard.

### Threshold Setting Mode
Set a specific battery threshold using the `-t` flag. This allows you to customize the battery percentage at which the alert will trigger without modifying the configuration file. Examples:

- `python app.py -t 80` - Set threshold to 80%
- `python app.py -t 100` - Set threshold to 100%
- `python app.py --threshold 95` - Alternative long form

### Discharge Calculation Mode
Calculate battery discharge rate without showing regular logs using the `-d` flag. This mode only logs discharge rate information every 10-15 minutes when the device is discharging (not plugged in).

### Command Line Options

**For app_enhanced.py**:
```bash
python app_enhanced.py [threshold] [interval] [options]

Positional Arguments:
  threshold              Battery threshold percentage (1-100)
  interval               Poll interval in seconds

Options:
  --web                  Start web interface
  --tray                 Start system tray app
  --profile NAME         Use specific profile
  --install-startup      Install Windows auto-start task
  --remove-startup       Remove Windows auto-start task
```

**For app.py (new options)**:
```bash
python app.py [threshold] [interval] [options]

Positional Arguments:
  threshold              Battery threshold percentage (1-100)
  interval               Poll interval in seconds

Options:
  -t, --threshold        Set battery threshold percentage (e.g., -t 90)
  -s, --seconds          Poll interval in seconds (e.g., -s 60 for 1 minute, -s 3600 for 1 hour)
  -d, --discharge-mode   Run in discharge calculation mode - calculates
                         discharge rate without showing regular logs
  --no-web               Run without web dashboard (CLI only)
  -f, --current-threshold Current threshold value
  -n, --new-threshold    New threshold value to use
  -a, --airpods-battery  Print battery percent for AirPods and exit
```

### Console Commands

While running, type these commands:

- `set 90` - Change threshold to 90%
- `snooze` - Mute alerts for 1 minute
- `dismiss` - Silence until battery drops below threshold
- `stats` - Show 24-hour statistics
- `health` - Show battery health information
- `devices` - List all monitored devices
- `profile work` - Switch to 'work' profile
- `quit` - Exit application

### Web Interface

Access the dashboard at: **http://127.0.0.1:5000**

Features:
- Real-time battery percentage with animated indicator
- Live charts showing battery history
- Statistics: average battery, charge cycles, health score
- Recent notifications panel
- Quick settings: threshold, polling, notifications
- Dark mode toggle
- Export data functionality

### Configuration Profiles

Create and manage profiles for different scenarios:

**Preset Profiles**:
- `conservative` - 80% threshold, frequent polling, multiple alerts
- `aggressive` - 95% threshold, less frequent polling
- `gaming` - Silent notifications, adaptive polling
- `overnight` - Scheduled monitoring (22:00-07:00)
- `work` - Email notifications, comprehensive alerts

**Create Custom Profile**:
```python
from config_manager import ConfigManager

config = ConfigManager()
config.create_profile(
    name='my_profile',
    threshold_percent=85,
    poll_interval_seconds=45,
    enable_email=True,
    email_address='you@example.com'
)
```

### Email Notifications

Configure in your profile:
```python
config.update_profile(
    'default',
    enable_email=True,
    smtp_server='smtp.gmail.com',
    smtp_port=587,
    smtp_username='your_email@gmail.com',
    smtp_password='your_app_password',
    email_address='your_email@gmail.com'
)
```

**Note**: For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833).

### SMS Notifications

Requires a [Twilio](https://www.twilio.com/) account:

```python
config.update_profile(
    'default',
    enable_sms=True,
    twilio_account_sid='your_account_sid',
    twilio_auth_token='your_auth_token',
    twilio_from_number='+1234567890',
    phone_number='+0987654321'
)
```

### Phone Monitoring

1. **Install ADB**: Download [Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools)
2. **Add to PATH**: Add the platform-tools folder to your system PATH
3. **Enable USB Debugging** on your Android phone
4. **Connect via USB** and authorize the computer
5. **Start charging** - the app will automatically detect and monitor your phone

## 🏗️ Architecture

```
battery_monitor/
├── app_enhanced.py          # Main application (enhanced version)
├── app.py                   # Original application (backup)
├── models.py                # Database models
├── database.py              # Database manager
├── notifications.py         # Notification system
├── ml_predictor.py          # ML predictions & health analysis
├── device_manager.py        # Multi-device management
├── config_manager.py        # Configuration & profiles
├── scheduler.py             # Scheduling & auto-start
├── tray_app.py             # System tray integration
├── battery_config.json      # Configuration file
├── battery_monitor.db       # SQLite database
├── templates/
│   └── index.html          # Web dashboard
├── static/
│   ├── css/
│   │   └── styles.css      # Modern UI styles
│   └── js/
│       └── app.js          # WebSocket client
└── sounds/                  # Custom notification sounds
```

## 🔧 Advanced Configuration

### Database Cleanup

Automatically remove old data:
```python
from database import DatabaseManager

db = DatabaseManager()
db.cleanup_old_data(days=30)  # Keep last 30 days
```

### ML Model Training

Train prediction models manually:
```python
from ml_predictor import BatteryPredictor
from database import DatabaseManager

db = DatabaseManager()
predictor = BatteryPredictor(db)
predictor.train_from_history('laptop')
predictor.train_from_history('phone')
```

### Custom Notification Sounds

1. Place `.wav` files in the `sounds/` directory
2. Configure in profile:
```python
config.update_profile(
    'default',
    custom_sound_path='C:/path/to/sounds/custom_alert.wav'
)
```

## 📊 Database Schema

The application uses SQLite with the following tables:

- **devices** - Registered devices (laptop/phones)
- **battery_readings** - Individual battery measurements
- **charge_cycles** - Complete charge cycle records
- **notification_logs** - History of all notifications
- **user_profiles** - Configuration profiles

## 🐛 Troubleshooting

### Phone not detected
- Ensure ADB is installed and in PATH
- Check USB debugging is enabled
- Try `adb devices` in terminal to verify connection
- Reconnect USB cable

### Web interface not loading
- Check if port 5000 is available
- Try accessing http://localhost:5000 instead
- Check firewall settings

### System tray not working
- Ensure `pystray` and `Pillow` are installed
- Run with `--tray` flag
- Check for errors in console

### Email notifications not sending
- Verify SMTP settings
- For Gmail, use App Password, not regular password
- Check firewall/antivirus blocking SMTP

### ML predictions inaccurate
- Need at least 5 charge cycles for training
- Accuracy improves over time with more data
- Check database has sufficient historical data

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional notification channels (Slack, Discord, etc.)
- More ML models for better predictions
- Mobile app companion
- Cloud sync for multi-device setups
- Power profile integration (Windows power plans)

## 📝 License

MIT License - feel free to use and modify!

## 🙏 Acknowledgments

- **psutil** - Cross-platform system utilities
- **Flask** & **Flask-SocketIO** - Web framework and real-time communication
- **Chart.js** - Beautiful charts
- **scikit-learn** - Machine learning capabilities
- **SQLAlchemy** - Database ORM

## 📧 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Made with ❤️ for battery health**
