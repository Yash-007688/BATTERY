# 🔋 AI-Powered Battery Monitor

A persistent background application that monitors your laptop and connected devices' battery levels, providing smart alerts, AI-driven insights, and remote monitoring via a **Discord Bot**.

## ✨ Key Features

-   **🖥️ Universal Monitoring**: Tracks battery for Laptop and connected Android phones (via KDE Connect/ADB).
-   **🤖 Discord Bot Integration**:
    -   Remote status checks via `/battery`.
    -   **`/insights`**: AI-powered health analysis and usage patterns.
    -   **`/predict`**: ML-based charging time forecasts.
    -   **`/stats`**: Detailed voltage, temperature, and cycle counts.
    -   **`/batterydischarge`**: Real-time discharge estimates.
    -   **`/set <limit>`**: Remotely control charge thresholds.
-   **🧠 AI & Machine Learning**:
    -   Predictions for charge/discharge times.
    -   Battery health degradation analysis.
    -   Usage pattern recognition for smart recommendations.
-   **📢 Smart Notifications**:
    -   Desktop Alerts (Toast).
    -   Discord Webhooks & Bot Messages.
    -   SMS (Twilio) and Email support.
-   **📊 Web Dashboard**: Local web interface for stats and configuration.
-   **⚡ System Tray**: Quick access to status and controls.

## 🚀 Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd BATTERY
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuration**:
    Create a `.env` file in the root directory:
    ```env
    # Discord Bot (Required for Bot features)
    DISCORD_BOT_TOKEN=your_discord_bot_token_here

    # Optional: For Webhook alerts
    DISCORD_WEBHOOK_URL=your_webhook_url

    # Optional: For SMS/Email
    TWILIO_ACCOUNT_SID=...
    TWILIO_AUTH_TOKEN=...
    EMAIL_PASSWORD=...
    ```

## 🎮 Usage

### Running the App
```bash
python app.py
```
The application will start in the background. A system tray icon will appear, and the Discord bot will come online.

### Discord Commands
| Command | Description |
| :--- | :--- |
| `/battery` | Show current level, status, and simple estimate. |
| `/batterydischarge` | Show time remaining and estimated empty time (when unplugged). |
| `/predict` | ML-based forecast for charging time with confidence score. |
| `/insights` | AI analysis of battery health and usage trends. |
| `/stats` | Technical details (Voltage, Temperature, Cycles). |
| `/set <80>` | Set the battery alert threshold to 80%. |

## 🛠️ Tech Stack
-   **Python 3.13+**
-   **discord.py**: Bot framework.
-   **scikit-learn**: Machine Learning models.
-   **Flask**: Web dashboard.
-   **psutil**: System hardware monitoring.
-   **pystray**: System tray integration.

## 🤝 Contributing
Feel free to open issues or submit PRs for new features!
