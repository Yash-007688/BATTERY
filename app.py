import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
import argparse

import psutil

# Flask imports
from flask import Flask, render_template_string
import webbrowser

try:
    import winsound
except ImportError:  # Fallback (non-Windows) – single bell
    winsound = None

# Windows notification imports
try:
    from plyer import notification
except ImportError:
    notification = None
    print("Warning: plyer not installed. Windows notifications will not be available.")


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "battery_config.json")


class BatteryMonitor:
    def __init__(self, threshold_percent: int, poll_interval_seconds: int) -> None:
        self.threshold_percent = int(threshold_percent)
        self.poll_interval_seconds = int(poll_interval_seconds)

        self._stop_event = threading.Event()
        self._input_thread: threading.Thread | None = None

        self._start_percent: float | None = None
        self._start_time: datetime | None = None
        self._reached_time: datetime | None = None
        self._alerted: bool = False
        self._alert_active: bool = False
        self._snooze_until: datetime | None = None
        self._dismissed_until_below: bool = False
        self._last_below_threshold: bool = True

        # Per-minute change tracking (percent-based; voltage not available via psutil)
        self._minute_anchor_time: datetime | None = None
        self._minute_anchor_percent: float | None = None
        self._per_minute_diffs: list[float] = []

    def start(self) -> None:
        self._start_time = datetime.now()
        self._start_percent = self._get_battery_percent()
        self._reached_time = None
        self._alerted = False

        # Initialize 1-minute tracking window
        self._minute_anchor_time = self._start_time
        self._minute_anchor_percent = self._start_percent

        print(
            f"Monitoring started at {self._start_time.strftime('%H:%M:%S')}. "
            f"Initial battery: {self._start_percent:.0f}% | Threshold: {self.threshold_percent}% | "
            f"Poll every {self.poll_interval_seconds}s"
        )
        print("Type 'set <percent>' to change threshold (e.g., set 90), or 'quit' to exit.")

        self._input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self._input_thread.start()

        try:
            self._monitor_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        self._stop_event.set()
        print("Stopping monitor...")

    def _input_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                user_input = input().strip()
            except EOFError:
                break
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                self.stop()
                break
            if user_input.lower().startswith("set "):
                parts = user_input.split()
                if len(parts) == 2 and parts[1].isdigit():
                    new_threshold = int(parts[1])
                    self._update_threshold(new_threshold)
                else:
                    print("Usage: set <percent>  (e.g., set 90)")
            elif user_input.lower() == "snooze":
                self._handle_snooze()
            elif user_input.lower() == "dismiss":
                self._handle_dismiss()
            else:
                print("Unknown command. Use 'set <percent>' or 'quit'.")

    def _update_threshold(self, new_threshold: int) -> None:
        new_threshold = max(1, min(100, new_threshold))
        self.threshold_percent = new_threshold
        self._alerted = False

        current_percent = self._get_battery_percent()
        # Reset timing window from now for new threshold if below target
        if current_percent < self.threshold_percent:
            self._start_time = datetime.now()
            self._start_percent = current_percent
            self._reached_time = None
            print(
                f"Threshold updated to {self.threshold_percent}%. "
                f"Restarting timer from {self._start_time.strftime('%H:%M:%S')} at {current_percent:.0f}%."
            )
        else:
            # Already at/above threshold – alert now and mark reached
            self._reached_time = datetime.now()
            self._beep()
            self._alerted = True
            print(
                f"Threshold updated to {self.threshold_percent}%. Already at {current_percent:.0f}% – alerting now."
            )

        # Persist to config for next run
        self._save_config()

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            percent, plugged, device, device_id, extra_info = self._get_battery_info()
            now_str = datetime.now().strftime('%H:%M:%S')

            if device == 'phone' and device_id and not hasattr(self, '_phone_printed'):
                tech_info = f" ({extra_info.get('technology', 'Unknown')})" if extra_info and 'technology' in extra_info else ""
                print(f"Phone connected: {device_id}{tech_info}")
                self._phone_printed = True
            elif device == 'laptop' and hasattr(self, '_phone_printed'):
                delattr(self, '_phone_printed')

            status = "Charging" if device == 'phone' else ("Plugged" if plugged else "On battery")
            line = f"[{now_str}] {device.capitalize()} Battery: {percent:.0f}% | {status} | Threshold: {self.threshold_percent}%"
            
            # Add device-specific details (voltage, temperature, health, technology)
            if extra_info:
                details = []
                if 'voltage' in extra_info:
                    voltage_v = extra_info['voltage'] / 1000.0  # Convert mV to V
                    details.append(f"{voltage_v:.2f}V")
                if 'temperature' in extra_info:
                    temp_c = extra_info['temperature'] / 10.0  # Convert 0.1°C to °C
                    details.append(f"{temp_c:.1f}°C")
                if 'technology' in extra_info:
                    details.append(extra_info['technology'])
                if 'health' in extra_info:
                    # For phone: only show if not "Good", for laptop: show if degraded
                    if device == 'phone' and extra_info['health'] != "Good":
                        details.append(f"Health: {extra_info['health']}")
                    elif device == 'laptop':
                        details.append(f"Health: {extra_info['health']}")
                if details:
                    line += f" | {', '.join(details)}"

            # Reset dismissal when battery drops below threshold
            current_below = percent < self.threshold_percent
            if current_below and not self._last_below_threshold:
                self._dismissed_until_below = False
                self._alerted = False
                self._alert_active = False
                self._reached_time = None
            self._last_below_threshold = current_below

            # If snoozed, skip alert until snooze ends
            if self._snooze_until is not None and datetime.now() < self._snooze_until:
                remaining = self._snooze_until - datetime.now()
                line += f" | Snoozed {format_timedelta(remaining)}"
            else:
                if self._snooze_until is not None and datetime.now() >= self._snooze_until:
                    # Snooze expired
                    self._snooze_until = None

                # Only trigger alert when plugged and at/above threshold and not dismissed
                if plugged and not self._dismissed_until_below and percent >= self.threshold_percent:
                    if self._reached_time is None:
                        self._reached_time = datetime.now()
                    if not self._alert_active:
                        self._trigger_alert()
                        self._alert_active = True
                        self._alerted = True
                    line += " | Reached threshold! (type 'snooze' or 'dismiss')"

            # Every full minute since last anchor, compute percent difference and record
            now_dt = datetime.now()
            if self._minute_anchor_time is None:
                self._minute_anchor_time = now_dt
                self._minute_anchor_percent = percent
            else:
                elapsed = (now_dt - self._minute_anchor_time).total_seconds()
                # Handle multiple minutes elapsed in case of longer polling intervals/sleeps
                while elapsed >= 60.0 and self._minute_anchor_percent is not None:
                    diff = percent - self._minute_anchor_percent
                    self._per_minute_diffs.append(diff)
                    # Report the just-computed 1-minute change
                    print(f"[{now_str}] Δ1m: {diff:+.1f}%")
                    # Advance anchor by 60s and set anchor percent to current percent
                    self._minute_anchor_time = self._minute_anchor_time + timedelta(seconds=60)
                    self._minute_anchor_percent = percent
                    elapsed -= 60.0

            if self._start_time is not None and self._reached_time is not None:
                delta = self._reached_time - self._start_time
                line += f" | Time to reach: {format_timedelta(delta)}"
                # When showing total charging time, also include min/max per-minute differences
                if self._per_minute_diffs:
                    min_diff = min(self._per_minute_diffs)
                    max_diff = max(self._per_minute_diffs)
                    line += f" | Δ1m min: {min_diff:+.1f}% max: {max_diff:+.1f}%"
            
            # Show estimated time to charge (to threshold or 100%)
            if plugged:
                estimated_time = self._estimate_charge_time(percent, plugged)
                if estimated_time:
                    if percent < self.threshold_percent:
                        line += f" | Est. to {self.threshold_percent}%: {estimated_time}"
                    else:
                        line += f" | Est. to 100%: {estimated_time}"

            print(line)

            # Sleep in small chunks so we can respond to stop quickly
            remaining = self.poll_interval_seconds
            while remaining > 0 and not self._stop_event.is_set():
                time.sleep(min(0.5, remaining))
                remaining -= 0.5

    def _get_laptop_battery_details(self) -> dict | None:
        """
        Get detailed laptop battery info via Windows WMI.
        Returns dict with: voltage (mV), chemistry, design_capacity (mWh), full_charge_capacity (mWh), health, temperature
        """
        try:
            # Use PowerShell to query WMI for battery details
            ps_cmd = r"""
            $battery = Get-CimInstance -ClassName Win32_Battery | Select-Object -First 1
            $temp = $null
            if ($battery) {
                $voltage = $battery.DesignVoltage
                $chemistry = $battery.Chemistry
                $designCap = $battery.DesignCapacity
                $fullCap = $battery.FullChargeCapacity
                $status = $battery.BatteryStatus
                $health = if ($fullCap -and $designCap) { [math]::Round(($fullCap / $designCap) * 100, 1) } else { $null }
                $statusDesc = switch ($status) {
                    1 { "Other" }
                    2 { "Unknown" }
                    3 { "Fully Charged" }
                    4 { "Low" }
                    5 { "Critical" }
                    6 { "Charging" }
                    7 { "Charging and High" }
                    8 { "Charging and Low" }
                    9 { "Charging and Critical" }
                    10 { "Undefined" }
                    11 { "Partially Charged" }
                    default { "Unknown" }
                }
                # Try to get temperature from Win32_TemperatureProbe (battery-related)
                try {
                    $tempProbes = Get-CimInstance -ClassName Win32_TemperatureProbe -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*battery*" -or $_.Description -like "*battery*" }
                    if ($tempProbes) {
                        $temp = ($tempProbes | Select-Object -First 1).CurrentReading
                    }
                    # If no battery-specific probe, try to get from BatteryStatus (if available)
                    if (-not $temp) {
                        try {
                            $batteryStatus = Get-CimInstance -Namespace "root\wmi" -ClassName "BatteryStatus" -ErrorAction SilentlyContinue | Select-Object -First 1
                            if ($batteryStatus -and $batteryStatus.Temperature) {
                                $temp = $batteryStatus.Temperature
                            }
                        } catch { }
                    }
                } catch { }
                Write-Output "$voltage|$chemistry|$designCap|$fullCap|$health|$statusDesc|$temp"
            }
            """
            result = subprocess.run(
                ['powershell', '-Command', ps_cmd],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None
            
            parts = result.stdout.strip().split('|')
            if len(parts) < 6:
                return None
            
            extra_info = {}
            
            # Voltage (in mV, WMI returns in mW, but we need to check units)
            if parts[0] and parts[0] != '':
                try:
                    voltage_mv = int(parts[0])  # WMI returns voltage in mV
                    if voltage_mv > 0:
                        extra_info['voltage'] = voltage_mv
                except ValueError:
                    pass
            
            # Chemistry (convert code to name)
            if parts[1] and parts[1] != '':
                try:
                    chem_code = int(parts[1])
                    chem_map = {
                        1: "Other", 2: "Unknown", 3: "Lead Acid", 4: "Nickel Cadmium",
                        5: "Nickel Metal Hydride", 6: "Lithium-ion", 7: "Zinc air",
                        8: "Lithium Polymer"
                    }
                    extra_info['technology'] = chem_map.get(chem_code, f"Code {chem_code}")
                except ValueError:
                    if parts[1]:
                        extra_info['technology'] = parts[1]
            
            # Design capacity and full charge capacity for health calculation
            if parts[2] and parts[2] != '' and parts[3] and parts[3] != '':
                try:
                    design_cap = int(parts[2])
                    full_cap = int(parts[3])
                    if design_cap > 0 and full_cap > 0:
                        health_pct = (full_cap / design_cap) * 100
                        if health_pct < 80:
                            extra_info['health'] = f"Degraded ({health_pct:.1f}%)"
                        elif health_pct < 50:
                            extra_info['health'] = f"Poor ({health_pct:.1f}%)"
                        # Only show if degraded
                except ValueError:
                    pass
            
            # Battery status (for health warnings)
            if len(parts) > 5 and parts[5] and parts[5] not in ['', 'Unknown', 'Fully Charged', 'Partially Charged', 'Charging']:
                if 'health' not in extra_info:
                    extra_info['health'] = parts[5]
            
            # Temperature (7th field, if available)
            # Win32_TemperatureProbe returns in tenths of degrees Kelvin
            # BatteryStatus might return in different units, but typically also in 0.1°K
            if len(parts) > 6 and parts[6] and parts[6] != '':
                try:
                    temp_raw = int(parts[6])
                    if temp_raw > 0:
                        # Convert from 0.1°K to °C: (temp_raw / 10) - 273.15
                        # But if value seems reasonable for Celsius (0-100 range), use as-is
                        # Otherwise assume it's in 0.1°K
                        if temp_raw < 1000:  # Likely already in 0.1°C format
                            temp_c = temp_raw / 10.0
                        else:  # Likely in 0.1°K format
                            temp_c = (temp_raw / 10.0) - 273.15
                        if 0 <= temp_c <= 100:  # Reasonable battery temperature range
                            extra_info['temperature'] = int(temp_c * 10)  # Store in 0.1°C format for consistency
                except (ValueError, TypeError):
                    pass
            
            return extra_info if extra_info else None
        except subprocess.TimeoutExpired:
            return None
        except Exception:
            return None

    def _get_battery(self) -> tuple[float, bool]:
        batt = psutil.sensors_battery()
        if batt is None:
            print("Battery info not available on this system.")
            return 0.0, False
        return float(batt.percent), bool(batt.power_plugged)

    def _get_phone_battery(self) -> tuple[float | None, bool | None, str | None, dict | None]:
        """
        Get phone battery info via ADB.
        Returns: (level, is_charging, device_id, extra_info_dict)
        extra_info_dict contains: voltage (mV), temperature (0.1°C), health, technology
        """
        try:
            # Check for connected devices
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return None, None, None, None
            devices_lines = [line.strip() for line in result.stdout.strip().split('\n')[1:] if line.strip() and '\tdevice' in line]
            if not devices_lines:
                return None, None, None, None
            device_id = devices_lines[0].split('\t')[0]
            
            # Get detailed battery info
            result = subprocess.run(['adb', 'shell', 'dumpsys', 'battery'], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return None, None, None, None
                
            lines = result.stdout.split('\n')
            level = None
            status = None
            voltage = None
            temperature = None
            health = None
            technology = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('level:'):
                    level = int(line.split(':')[1].strip())
                elif line.startswith('status:'):
                    status_code = int(line.split(':')[1].strip())
                    # Status codes: 1=Unknown, 2=Charging, 3=Discharging, 4=Not charging, 5=Full
                    status = status_code == 2
                elif line.startswith('voltage:'):
                    voltage = int(line.split(':')[1].strip())  # in mV
                elif line.startswith('temperature:'):
                    temperature = int(line.split(':')[1].strip())  # in 0.1°C (divide by 10 for °C)
                elif line.startswith('health:'):
                    health_code = int(line.split(':')[1].strip())
                    # Health codes: 1=Unknown, 2=Good, 3=Overheat, 4=Dead, 5=Over voltage, 6=Unspecified failure, 7=Cold
                    health_map = {1: "Unknown", 2: "Good", 3: "Overheat", 4: "Dead", 5: "Over voltage", 6: "Failure", 7: "Cold"}
                    health = health_map.get(health_code, f"Code {health_code}")
                elif line.startswith('technology:'):
                    technology = line.split(':')[1].strip()
            
            if level is not None and status is not None:
                extra_info = {}
                if voltage is not None:
                    extra_info['voltage'] = voltage
                if temperature is not None:
                    extra_info['temperature'] = temperature
                if health is not None:
                    extra_info['health'] = health
                if technology is not None:
                    extra_info['technology'] = technology
                return level, status, device_id, extra_info if extra_info else None
            return None, None, None, None
        except subprocess.TimeoutExpired:
            return None, None, None, None
        except FileNotFoundError:
            # ADB not found in PATH
            if not hasattr(self, '_adb_warned'):
                print("Warning: ADB not found. Phone monitoring disabled. Install Android SDK Platform Tools.")
                self._adb_warned = True
            return None, None, None, None
        except Exception:
            return None, None, None, None

    def _get_battery_info(self) -> tuple[float, bool, str, str | None, dict | None]:
        phone_level, phone_charging, device_id, phone_extra = self._get_phone_battery()
        if phone_level is not None and phone_charging:
            return float(phone_level), True, 'phone', device_id, phone_extra
        # laptop
        batt = psutil.sensors_battery()
        if batt is None:
            print("Battery info not available on this system.")
            return 0.0, False, 'laptop', None, None
        # Get detailed laptop battery info
        laptop_extra = self._get_laptop_battery_details()
        return float(batt.percent), bool(batt.power_plugged), 'laptop', None, laptop_extra

    def _get_battery(self) -> tuple[float, bool]:
        percent, plugged, _, _, _ = self._get_battery_info()
        return percent, plugged

    def _get_battery_percent(self) -> float:
        percent, _, _, _, _ = self._get_battery_info()
        return percent

    def _estimate_charge_time(self, current_percent: float, plugged: bool) -> str | None:
        """
        Estimate time to charge to threshold or 100%.
        Returns formatted time string or None if cannot estimate.
        """
        if not plugged or self._start_time is None or self._start_percent is None:
            return None
        
        # Calculate charging rate
        elapsed_time = datetime.now() - self._start_time
        elapsed_seconds = elapsed_time.total_seconds()
        
        if elapsed_seconds < 10:  # Need at least 10 seconds of data
            return None
        
        # Use per-minute diffs if available (more accurate)
        if self._per_minute_diffs:
            # Average per-minute change
            avg_per_minute = sum(self._per_minute_diffs) / len(self._per_minute_diffs)
            if avg_per_minute <= 0:  # Not charging or discharging
                return None
            rate_per_second = avg_per_minute / 60.0
        else:
            # Fallback to overall rate
            difference = current_percent - self._start_percent
            if difference <= 0:
                return None
            rate_per_second = difference / elapsed_seconds
        
        if rate_per_second <= 0:
            return None
        
        # Determine target: threshold if below, 100% if above
        if current_percent < self.threshold_percent:
            target_percent = self.threshold_percent
            target_name = f"{self.threshold_percent}%"
        else:
            target_percent = 100.0
            target_name = "100%"
        
        remaining_percent = target_percent - current_percent
        if remaining_percent <= 0:
            return None
        
        # Calculate estimated seconds
        estimated_seconds = remaining_percent / rate_per_second
        
        # Format time
        return format_timedelta(timedelta(seconds=int(estimated_seconds)))

    def _beep(self) -> None:
        try:
            if winsound is not None:
                winsound.Beep(1000, 300)
            else:
                # Fallback to terminal bell
                sys.stdout.write('\a')
                sys.stdout.flush()
        except Exception:
            # Ignore sound errors
            pass

    def _beep_times(self, times: int, freq1: int = 1000, freq2: int = 1400) -> None:
        for i in range(times):
            try:
                if winsound is not None:
                    winsound.Beep(freq1 if i % 2 == 0 else freq2, 250)
                else:
                    sys.stdout.write('\a')
                    sys.stdout.flush()
                time.sleep(0.07)
            except Exception:
                pass

    def _trigger_alert(self) -> None:
        # 5 beeps, then present options
        self._beep_times(5)
        print("Battery reached threshold. Type 'snooze' to mute for 1 minute or 'dismiss' (requires unplugging charger).")
        
        # Send Windows notification when battery reaches threshold
        if notification:
            try:
                notification.notify(
                    title="Battery Monitor",
                    message=f"Battery reached {self.threshold_percent}% threshold!",
                    timeout=10
                )
            except Exception as e:
                print(f"Failed to send notification: {e}")

    def _handle_snooze(self) -> None:
        self._snooze_until = datetime.now() + timedelta(minutes=1)
        self._alert_active = False
        print(f"Snoozed until {self._snooze_until.strftime('%H:%M:%S')}")

    def _handle_dismiss(self) -> None:
        percent, plugged, device, _, _ = self._get_battery_info()
        if plugged:
            charger_type = "charging" if device == 'phone' else "charger"
            print(f"Cannot dismiss while {charger_type} is plugged in. Unplug the {charger_type}, then type 'dismiss' again.")
            return
        self._dismissed_until_below = True
        self._alert_active = False
        print("Dismissed. Alerts will resume after battery drops below threshold and rises again.")

    def _save_config(self) -> None:
        try:
            cfg = {
                "threshold_percent": self.threshold_percent,
                "poll_interval_seconds": self.poll_interval_seconds,
            }
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save config: {e}")


def format_timedelta(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def load_config() -> tuple[int, int]:
    threshold = 80
    interval = 30
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            threshold = int(data.get("threshold_percent", threshold))
            interval = int(data.get("poll_interval_seconds", interval))
        except Exception as e:
            print(f"Warning: Failed to read config, using defaults. {e}")
    return threshold, interval


def parse_percent_arg(value: str) -> int:
    s = value.strip()
    if s.endswith("%"):
        s = s[:-1]
    if not s.isdigit():
        raise argparse.ArgumentTypeError("Percentage must be an integer like 95 or 95%")
    n = int(s)
    if n < 1 or n > 100:
        raise argparse.ArgumentTypeError("Percentage must be between 1 and 100")
    return n


def create_flask_app(monitor):
    """Create Flask app to display battery information"""
    app = Flask(__name__)
    
    @app.route('/')
    def battery_status():
        # Get current battery information
        percent, plugged, device, device_id, extra_info = monitor._get_battery_info()
        now_str = datetime.now().strftime('%H:%M:%S')
        
        # Calculate battery difference
        start_percent = monitor._start_percent or percent
        current_percent = percent
        
        # Calculate difference from start
        difference = current_percent - start_percent
        
        # Calculate estimated time to charge (to threshold or 100%)
        estimated_charge_time = monitor._estimate_charge_time(percent, plugged)
        charge_time_label = "N/A"
        charge_time_value = "N/A"
        
        if estimated_charge_time:
            if percent < monitor.threshold_percent:
                charge_time_label = f"Time to {monitor.threshold_percent}%"
                charge_time_value = estimated_charge_time
            else:
                charge_time_label = "Time to 100%"
                charge_time_value = estimated_charge_time
        elif monitor._reached_time is not None:
            # Already reached threshold
            delta = monitor._reached_time - monitor._start_time
            charge_time_label = f"Time to reach {monitor.threshold_percent}%"
            charge_time_value = format_timedelta(delta)
        
        # HTML template with styling for requested layout
        html_template = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Battery Monitor</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f0f0f0;
                }
                .container {
                    text-align: center;
                }
                .battery-percent {
                    font-size: 50px;
                    font-weight: bold;
                    color: #333;
                }
                .difference {
                    font-size: 20px;
                    color: #666;
                    margin-top: 20px;
                }
                .charge-time {
                    font-size: 20px;
                    color: #666;
                    margin-top: 10px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="battery-percent">{{ battery_percent }}%</div>
                <div class="difference">Difference: {{ difference }}%</div>
                <div class="charge-time">{{ charge_time_label }}: {{ charge_time_value }}</div>
            </div>
        </body>
        </html>
        '''
        
        return render_template_string(html_template, 
                                   battery_percent=f"{percent:.0f}",
                                   difference=f"{difference:+.1f}",
                                   charge_time_label=charge_time_label,
                                   charge_time_value=charge_time_value)
    
    return app

def start_flask_server(monitor, host='127.0.0.1', port=5000):
    """Start Flask server in a separate thread"""
    app = create_flask_app(monitor)
    
    def run_app():
        app.run(host=host, port=port, debug=False)
    
    flask_thread = threading.Thread(target=run_app, daemon=True)
    flask_thread.start()
    
    # Give the server a moment to start
    time.sleep(1)
    
    # Open browser to the server
    webbrowser.open(f'http://{host}:{port}')
    
    return flask_thread

def main() -> None:
    default_threshold, default_interval = load_config()

    parser = argparse.ArgumentParser(description="Battery monitor with threshold alert")
    # Flags requested: -f 95% -n 85%
    parser.add_argument("threshold", nargs="?", type=parse_percent_arg, help="threshold percent (e.g. 95 or 95 percent)")
    parser.add_argument("interval", nargs="?", type=int, help="poll interval seconds (e.g. 30)")
    parser.add_argument("-f", "--current-threshold", dest="current_threshold", type=parse_percent_arg, help="current threshold value (e.g. 95 percent)")
    parser.add_argument("-n", "--new-threshold", dest="new_threshold", type=parse_percent_arg, help="new threshold value to use (e.g. 85 percent)")
    parser.add_argument("--no-web", action="store_true", help="Run without web dashboard (CLI only)")

    args = parser.parse_args()

    # Determine threshold precedence: new_threshold (-n) > current_threshold (-f) > positional > config
    threshold = (
        args.new_threshold
        if args.new_threshold is not None
        else (
            args.current_threshold
            if args.current_threshold is not None
            else (args.threshold if args.threshold is not None else default_threshold)
        )
    )

    interval = args.interval if args.interval is not None else default_interval

    monitor = BatteryMonitor(threshold, interval)
    
    # Start Flask server by default unless explicitly disabled
    if not args.no_web:
        start_flask_server(monitor)
        print("Web interface started at http://127.0.0.1:5000")
    
    monitor.start()


if __name__ == "__main__":
    main()


