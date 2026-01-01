"""
Battery Monitor - Enhanced Version with All Features
Comprehensive battery monitoring with database, ML predictions, web interface, and more
"""
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
import argparse

import psutil

# Import new modules
from database import DatabaseManager
from notifications import NotificationManager, NotificationTemplates
from ml_predictor import BatteryPredictor, BatteryHealthAnalyzer
from device_manager import DeviceManager
from config_manager import ConfigManager
from scheduler import MonitorScheduler, WindowsTaskScheduler

# Flask and WebSocket imports
from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO, emit
import webbrowser

try:
    import winsound
except ImportError:
    winsound = None


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "battery_config.json")


class EnhancedBatteryMonitor:
    """Enhanced Battery Monitor with all features"""
    
    def __init__(self, threshold_percent: int = None, poll_interval_seconds: int = None):
        # Initialize configuration manager
        self.config_manager = ConfigManager(CONFIG_PATH)
        self.active_profile = self.config_manager.get_active_profile()
        
        # Override with command-line arguments if provided
        if threshold_percent is not None:
            self.threshold_percent = int(threshold_percent)
        else:
            self.threshold_percent = self.active_profile.threshold_percent
            
        if poll_interval_seconds is not None:
            self.poll_interval_seconds = int(poll_interval_seconds)
        else:
            self.poll_interval_seconds = self.active_profile.poll_interval_seconds
        
        # Initialize core components
        self.db_manager = DatabaseManager()
        self.notification_manager = NotificationManager(self.db_manager)
        self.ml_predictor = BatteryPredictor(self.db_manager)
        self.health_analyzer = BatteryHealthAnalyzer(self.db_manager)
        self.device_manager = DeviceManager(self.db_manager)
        
        # Configure notifications from profile
        self._configure_notifications()
        
        # Initialize scheduler if enabled
        self.scheduler = None
        if self.active_profile.enable_scheduling:
            self.scheduler = MonitorScheduler(
                start_time=self.active_profile.start_time,
                stop_time=self.active_profile.stop_time
            )
            self.scheduler.enable()
        
        # Monitoring state
        self._stop_event = threading.Event()
        self._input_thread = None
        self._start_percent = None
        self._start_time = None
        self._reached_time = None
        self._alerted = False
        self._alert_active = False
        self._snooze_until = None
        self._dismissed_until_below = False
        self._last_below_threshold = True
        
        # Per-minute change tracking
        self._minute_anchor_time = None
        self._minute_anchor_percent = None
        self._per_minute_diffs = []
        
        # Current device tracking
        self._current_device_id = None
        self._current_device_type = 'laptop'
        self._active_charge_cycle = None
        
        # WebSocket clients
        self.socketio_clients = []
        
        # System tray app
        self.tray_app = None
    
    def _configure_notifications(self):
        """Configure notification manager from profile settings"""
        profile = self.active_profile
        
        # Email configuration
        if profile.enable_email and all([profile.smtp_server, profile.smtp_username, profile.smtp_password]):
            self.notification_manager.configure_email(
                smtp_server=profile.smtp_server,
                smtp_port=profile.smtp_port,
                username=profile.smtp_username,
                password=profile.smtp_password,
                from_email=profile.email_address
            )
        
        # SMS configuration
        if profile.enable_sms and all([profile.twilio_account_sid, profile.twilio_auth_token, profile.twilio_from_number]):
            try:
                self.notification_manager.configure_sms(
                    account_sid=profile.twilio_account_sid,
                    auth_token=profile.twilio_auth_token,
                    from_number=profile.twilio_from_number
                )
            except ImportError:
                print("Twilio not installed. SMS notifications disabled.")
    
    def start(self):
        """Start monitoring"""
        self._start_time = datetime.now()
        self._start_percent = self._get_battery_percent()
        self._reached_time = None
        self._alerted = False
        
        # Initialize 1-minute tracking
        self._minute_anchor_time = self._start_time
        self._minute_anchor_percent = self._start_percent
        
        # Start charge cycle tracking
        percent, plugged, device_type, device_id, _ = self._get_battery_info()
        if plugged and device_id:
            self._start_charge_cycle(device_id, percent)
        
        print(
            f"Enhanced Battery Monitor started at {self._start_time.strftime('%H:%M:%S')}. "
            f"Initial battery: {self._start_percent:.0f}% | Threshold: {self.threshold_percent}% | "
            f"Poll every {self.poll_interval_seconds}s"
        )
        print("Type 'set <percent>' to change threshold, or 'quit' to exit.")
        print(f"Active profile: {self.active_profile.name}")
        
        # Train ML model from history
        if self.active_profile.enable_ml_predictions:
            threading.Thread(target=self._train_ml_models, daemon=True).start()
        
        # Start scheduler if enabled
        if self.scheduler:
            self.scheduler.start_scheduler(
                on_start_callback=lambda: print("Scheduler: Monitoring started"),
                on_stop_callback=lambda: print("Scheduler: Monitoring paused")
            )
        
        # Start input thread
        self._input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self._input_thread.start()
        
        try:
            self._monitor_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self):
        """Stop monitoring"""
        self._stop_event.set()
        
        # End active charge cycle
        if self._active_charge_cycle:
            percent, _, _, _, _ = self._get_battery_info()
            self._end_charge_cycle(percent)
        
        # Stop scheduler
        if self.scheduler:
            self.scheduler.stop_scheduler()
        
        print("Stopping monitor...")
    
    def _train_ml_models(self):
        """Train ML models in background"""
        print("Training ML models from historical data...")
        self.ml_predictor.train_from_history('laptop')
        self.ml_predictor.train_from_history('phone')
    
    def _input_loop(self):
        """Handle user input"""
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
            elif user_input.lower().startswith("set "):
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
            elif user_input.lower() == "stats":
                self._show_stats()
            elif user_input.lower() == "health":
                self._show_health()
            elif user_input.lower() == "devices":
                self._show_devices()
            elif user_input.lower().startswith("profile "):
                profile_name = user_input.split(maxsplit=1)[1]
                self._switch_profile(profile_name)
            else:
                print("Commands: set <percent>, snooze, dismiss, stats, health, devices, profile <name>, quit")
    
    def _update_threshold(self, new_threshold: int):
        """Update battery threshold"""
        new_threshold = max(1, min(100, new_threshold))
        self.threshold_percent = new_threshold
        self._alerted = False
        
        current_percent = self._get_battery_percent()
        
        if current_percent < self.threshold_percent:
            self._start_time = datetime.now()
            self._start_percent = current_percent
            self._reached_time = None
            print(
                f"Threshold updated to {self.threshold_percent}%. "
                f"Restarting timer from {self._start_time.strftime('%H:%M:%S')} at {current_percent:.0f}%."
            )
        else:
            self._reached_time = datetime.now()
            self._trigger_alert()
            self._alerted = True
            print(f"Threshold updated to {self.threshold_percent}%. Already at {current_percent:.0f}% – alerting now.")
        
        # Update profile
        self.config_manager.update_profile(self.active_profile.name, threshold_percent=new_threshold)
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while not self._stop_event.is_set():
            # Check if we should monitor now (scheduling)
            if self.scheduler and not self.scheduler.should_monitor_now():
                time.sleep(60)  # Check every minute
                continue
            
            percent, plugged, device_type, device_id, extra_info = self._get_battery_info()
            now_str = datetime.now().strftime('%H:%M:%S')
            
            # Register/update device
            if device_id:
                self.device_manager.register_device(
                    device_id=device_id,
                    device_type=device_type,
                    technology=extra_info.get('technology') if extra_info else None
                )
                self._current_device_id = device_id
                self._current_device_type = device_type
            
            # Log to database
            if device_id:
                delta_1m = self._per_minute_diffs[-1] if self._per_minute_diffs else None
                self.db_manager.add_reading(
                    device_id=device_id,
                    percentage=percent,
                    is_charging=plugged,
                    voltage=extra_info.get('voltage') if extra_info else None,
                    temperature=extra_info.get('temperature') if extra_info else None,
                    health_status=extra_info.get('health') if extra_info else None,
                    delta_1m=delta_1m
                )
            
            # Update ML predictor
            if self.active_profile.enable_ml_predictions:
                delta_1m = self._per_minute_diffs[-1] if self._per_minute_diffs else None
                self.ml_predictor.update_with_reading(device_type, percent, delta_1m)
            
            # Build status line
            status = "Charging" if device_type == 'phone' else ("Plugged" if plugged else "On battery")
            line = f"[{now_str}] {device_type.capitalize()} Battery: {percent:.0f}% | {status} | Threshold: {self.threshold_percent}%"
            
            # Add device details
            if extra_info:
                details = []
                if 'voltage' in extra_info:
                    voltage_v = extra_info['voltage'] / 1000.0
                    details.append(f"{voltage_v:.2f}V")
                if 'temperature' in extra_info:
                    temp_c = extra_info['temperature'] / 10.0
                    details.append(f"{temp_c:.1f}°C")
                if 'technology' in extra_info:
                    details.append(extra_info['technology'])
                if 'health' in extra_info:
                    if device_type == 'phone' and extra_info['health'] != "Good":
                        details.append(f"Health: {extra_info['health']}")
                    elif device_type == 'laptop':
                        details.append(f"Health: {extra_info['health']}")
                if details:
                    line += f" | {', '.join(details)}"
            
            # Handle threshold alerts
            current_below = percent < self.threshold_percent
            if current_below and not self._last_below_threshold:
                self._dismissed_until_below = False
                self._alerted = False
                self._alert_active = False
                self._reached_time = None
                # End charge cycle
                if self._active_charge_cycle:
                    self._end_charge_cycle(percent)
            self._last_below_threshold = current_below
            
            # Check snooze
            if self._snooze_until and datetime.now() < self._snooze_until:
                remaining = self._snooze_until - datetime.now()
                line += f" | Snoozed {self._format_timedelta(remaining)}"
            else:
                if self._snooze_until:
                    self._snooze_until = None
                
                # Trigger alert if threshold reached
                if plugged and not self._dismissed_until_below and percent >= self.threshold_percent:
                    if self._reached_time is None:
                        self._reached_time = datetime.now()
                        # End charge cycle
                        if self._active_charge_cycle:
                            self._end_charge_cycle(percent)
                    
                    if not self._alert_active:
                        self._trigger_alert(device_type, percent)
                        self._alert_active = True
                        self._alerted = True
                    
                    line += " | Reached threshold! (type 'snooze' or 'dismiss')"
            
            # Track 1-minute changes
            now_dt = datetime.now()
            if self._minute_anchor_time is None:
                self._minute_anchor_time = now_dt
                self._minute_anchor_percent = percent
            else:
                elapsed = (now_dt - self._minute_anchor_time).total_seconds()
                while elapsed >= 60.0 and self._minute_anchor_percent is not None:
                    diff = percent - self._minute_anchor_percent
                    self._per_minute_diffs.append(diff)
                    print(f"[{now_str}] Δ1m: {diff:+.1f}%")
                    self._minute_anchor_time += timedelta(seconds=60)
                    self._minute_anchor_percent = percent
                    elapsed -= 60.0
            
            # Show time to reach threshold
            if self._start_time and self._reached_time:
                delta = self._reached_time - self._start_time
                line += f" | Time to reach: {self._format_timedelta(delta)}"
                if self._per_minute_diffs:
                    min_diff = min(self._per_minute_diffs)
                    max_diff = max(self._per_minute_diffs)
                    line += f" | Δ1m min: {min_diff:+.1f}% max: {max_diff:+.1f}%"
            
            # ML prediction for time to threshold
            if self.active_profile.enable_ml_predictions and percent < self.threshold_percent and plugged:
                recent_delta = self._per_minute_diffs[-1] if self._per_minute_diffs else None
                predicted_time, confidence = self.ml_predictor.predict_charge_time(
                    device_type, percent, self.threshold_percent, recent_delta
                )
                if predicted_time is not None:
                    line += f" | Est. time: {predicted_time:.0f}min (conf: {confidence:.0%})"
            
            print(line)
            
            # Broadcast to WebSocket clients
            self._broadcast_update(percent, plugged, device_type, extra_info)
            
            # Update system tray if available
            if self.tray_app:
                self.tray_app.update_icon(int(percent), plugged)
            
            # Adaptive polling
            if self.active_profile.enable_adaptive_polling:
                poll_interval = self.ml_predictor.get_adaptive_poll_interval(
                    device_type, percent, self.threshold_percent, self.poll_interval_seconds
                )
            else:
                poll_interval = self.poll_interval_seconds
            
            # Sleep in chunks
            remaining = poll_interval
            while remaining > 0 and not self._stop_event.is_set():
                time.sleep(min(0.5, remaining))
                remaining -= 0.5
    
    def _get_battery_info(self):
        """Get battery information (laptop or phone)"""
        # Check for phone first
        phone_level, phone_charging, device_id, phone_extra = self._get_phone_battery()
        if phone_level is not None and phone_charging:
            return float(phone_level), True, 'phone', device_id, phone_extra
        
        # Fall back to laptop
        batt = psutil.sensors_battery()
        if batt is None:
            return 0.0, False, 'laptop', 'laptop_default', None
        
        laptop_extra = self._get_laptop_battery_details()
        return float(batt.percent), bool(batt.power_plugged), 'laptop', 'laptop_default', laptop_extra
    
    def _get_battery_percent(self):
        """Get current battery percentage"""
        percent, _, _, _, _ = self._get_battery_info()
        return percent
    
    def _get_phone_battery(self):
        """Get phone battery via ADB (from original app.py)"""
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return None, None, None, None
            
            devices_lines = [line.strip() for line in result.stdout.strip().split('\n')[1:] 
                           if line.strip() and '\tdevice' in line]
            if not devices_lines:
                return None, None, None, None
            
            device_id = devices_lines[0].split('\t')[0]
            
            result = subprocess.run(['adb', 'shell', 'dumpsys', 'battery'], 
                                  capture_output=True, text=True, timeout=5)
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
                    status = status_code == 2
                elif line.startswith('voltage:'):
                    voltage = int(line.split(':')[1].strip())
                elif line.startswith('temperature:'):
                    temperature = int(line.split(':')[1].strip())
                elif line.startswith('health:'):
                    health_code = int(line.split(':')[1].strip())
                    health_map = {1: "Unknown", 2: "Good", 3: "Overheat", 4: "Dead", 
                                5: "Over voltage", 6: "Failure", 7: "Cold"}
                    health = health_map.get(health_code, f"Code {health_code}")
                elif line.startswith('technology:'):
                    technology = line.split(':')[1].strip()
            
            if level is not None and status is not None:
                extra_info = {}
                if voltage: extra_info['voltage'] = voltage
                if temperature: extra_info['temperature'] = temperature
                if health: extra_info['health'] = health
                if technology: extra_info['technology'] = technology
                return level, status, device_id, extra_info if extra_info else None
            
            return None, None, None, None
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return None, None, None, None
    
    def _get_laptop_battery_details(self):
        """Get laptop battery details via WMI (from original app.py)"""
        try:
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
                Write-Output "$voltage|$chemistry|$designCap|$fullCap|$health|$status|$temp"
            }
            """
            result = subprocess.run(['powershell', '-Command', ps_cmd],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0 or not result.stdout.strip():
                return None
            
            parts = result.stdout.strip().split('|')
            if len(parts) < 6:
                return None
            
            extra_info = {}
            
            # Voltage
            if parts[0] and parts[0] != '':
                try:
                    voltage_mv = int(parts[0])
                    if voltage_mv > 0:
                        extra_info['voltage'] = voltage_mv
                except ValueError:
                    pass
            
            # Chemistry
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
            
            # Health
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
                except ValueError:
                    pass
            
            return extra_info if extra_info else None
        except (subprocess.TimeoutExpired, Exception):
            return None
    
    def _start_charge_cycle(self, device_id: str, start_percentage: float):
        """Start tracking a charge cycle"""
        try:
            cycle = self.db_manager.start_charge_cycle(
                device_id=device_id,
                start_percentage=start_percentage,
                target_percentage=self.threshold_percent
            )
            self._active_charge_cycle = cycle.id
        except Exception as e:
            print(f"Error starting charge cycle: {e}")
    
    def _end_charge_cycle(self, end_percentage: float):
        """End the current charge cycle"""
        if not self._active_charge_cycle:
            return
        
        try:
            min_delta = min(self._per_minute_diffs) if self._per_minute_diffs else None
            max_delta = max(self._per_minute_diffs) if self._per_minute_diffs else None
            avg_delta = sum(self._per_minute_diffs) / len(self._per_minute_diffs) if self._per_minute_diffs else None
            
            self.db_manager.end_charge_cycle(
                cycle_id=self._active_charge_cycle,
                end_percentage=end_percentage,
                min_delta=min_delta,
                max_delta=max_delta,
                avg_delta=avg_delta
            )
            self._active_charge_cycle = None
            
            # Retrain ML model with new data
            if self.active_profile.enable_ml_predictions:
                threading.Thread(target=self._train_ml_models, daemon=True).start()
        except Exception as e:
            print(f"Error ending charge cycle: {e}")
    
    def _trigger_alert(self, device_type: str, battery_percentage: float):
        """Trigger threshold alert"""
        profile_settings = {
            'enable_desktop_notifications': self.active_profile.enable_desktop_notifications,
            'enable_sound': self.active_profile.enable_sound,
            'enable_email': self.active_profile.enable_email,
            'enable_sms': self.active_profile.enable_sms,
            'custom_sound_path': self.active_profile.custom_sound_path,
            'email_address': self.active_profile.email_address,
            'phone_number': self.active_profile.phone_number
        }
        
        self.notification_manager.send_threshold_alert(
            device_type=device_type,
            battery_percentage=battery_percentage,
            threshold=self.threshold_percent,
            profile_settings=profile_settings
        )
        
        print("Battery reached threshold. Type 'snooze' to mute for 1 minute or 'dismiss' (requires unplugging charger).")
    
    def _handle_snooze(self):
        """Snooze alerts for 1 minute"""
        self._snooze_until = datetime.now() + timedelta(minutes=1)
        self._alert_active = False
        print(f"Snoozed until {self._snooze_until.strftime('%H:%M:%S')}")
    
    def _handle_dismiss(self):
        """Dismiss alerts"""
        percent, plugged, device_type, _, _ = self._get_battery_info()
        if plugged:
            charger_type = "charging" if device_type == 'phone' else "charger"
            print(f"Cannot dismiss while {charger_type} is plugged in. Unplug the {charger_type}, then type 'dismiss' again.")
            return
        
        self._dismissed_until_below = True
        self._alert_active = False
        print("Dismissed. Alerts will resume after battery drops below threshold and rises again.")
    
    def _show_stats(self):
        """Show battery statistics"""
        if not self._current_device_id:
            print("No device data available yet.")
            return
        
        stats = self.db_manager.get_reading_stats(self._current_device_id, hours=24)
        print("\n=== Battery Statistics (24h) ===")
        print(f"Average: {stats.get('avg_percentage', 0):.1f}%")
        print(f"Min: {stats.get('min_percentage', 0):.1f}%")
        print(f"Max: {stats.get('max_percentage', 0):.1f}%")
        if stats.get('avg_temperature'):
            print(f"Avg Temperature: {stats.get('avg_temperature'):.1f}°C")
        print(f"Readings: {stats.get('reading_count', 0)}")
        print()
    
    def _show_health(self):
        """Show battery health information"""
        if not self._current_device_id:
            print("No device data available yet.")
            return
        
        # Get health score
        score, status = self.health_analyzer.calculate_health_score(
            self._current_device_type,
            self._current_device_id
        )
        
        print("\n=== Battery Health ===")
        print(f"Health Score: {score:.1f}% ({status})")
        
        # Get recommendations
        cycles = self.db_manager.get_charge_history(self._current_device_id, limit=100)
        recommendations = self.health_analyzer.get_recommendations(score, len(cycles))
        
        print("\nRecommendations:")
        for rec in recommendations:
            print(f"  {rec}")
        print()
    
    def _show_devices(self):
        """Show all monitored devices"""
        devices = self.device_manager.get_all_devices()
        
        print("\n=== Monitored Devices ===")
        for device in devices:
            status = "✓ Enabled" if device.enabled else "✗ Disabled"
            active = " [ACTIVE]" if device.device_id == self._current_device_id else ""
            print(f"{device.device_name} ({device.device_type}): {status}{active}")
            print(f"  ID: {device.device_id}")
            print(f"  Threshold: {device.threshold}%")
            print(f"  Last seen: {device.last_seen.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def _switch_profile(self, profile_name: str):
        """Switch to a different profile"""
        try:
            self.config_manager.set_active_profile(profile_name)
            self.active_profile = self.config_manager.get_active_profile()
            
            # Update settings
            self.threshold_percent = self.active_profile.threshold_percent
            self.poll_interval_seconds = self.active_profile.poll_interval_seconds
            
            # Reconfigure notifications
            self._configure_notifications()
            
            print(f"Switched to profile: {profile_name}")
            print(f"Threshold: {self.threshold_percent}%, Poll interval: {self.poll_interval_seconds}s")
        except ValueError as e:
            print(f"Error: {e}")
    
    def _broadcast_update(self, percentage: float, is_charging: bool, 
                         device_type: str, extra_info: dict):
        """Broadcast update to WebSocket clients"""
        if not hasattr(self, 'socketio') or not self.socketio:
            return
        
        data = {
            'type': 'battery_update',
            'percentage': percentage,
            'is_charging': is_charging,
            'device_type': device_type,
            'voltage': extra_info.get('voltage') if extra_info else None,
            'temperature': extra_info.get('temperature') if extra_info else None,
            'health': extra_info.get('health') if extra_info else None,
            'delta_1m': self._per_minute_diffs[-1] if self._per_minute_diffs else None,
            'time_to_threshold': self._format_timedelta(self._reached_time - self._start_time) if self._reached_time and self._start_time else None
        }
        
        try:
            self.socketio.emit('battery_update', data)
        except Exception as e:
            pass  # Silently ignore WebSocket errors
    
    @staticmethod
    def _format_timedelta(delta: timedelta) -> str:
        """Format timedelta to readable string"""
        total_seconds = int(delta.total_seconds())
        hours, rem = divmod(total_seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        if hours:
            return f"{hours}h {minutes}m {seconds}s"
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"


def create_flask_app(monitor):
    """Create Flask app with WebSocket support"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'battery-monitor-secret-key'
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Store socketio reference in monitor
    monitor.socketio = socketio
    
    @app.route('/')
    def index():
        return render_template('index.html', 
                             threshold=monitor.threshold_percent,
                             poll_interval=monitor.poll_interval_seconds)
    
    @app.route('/api/stats')
    def get_stats():
        if not monitor._current_device_id:
            return jsonify({'error': 'No device data'}), 404
        
        stats = monitor.db_manager.get_reading_stats(monitor._current_device_id, hours=24)
        cycles = monitor.db_manager.get_charge_history(monitor._current_device_id, limit=10)
        
        return jsonify({
            'avg_percentage': stats.get('avg_percentage', 0),
            'charge_cycles': len(cycles),
            'health_score': 100.0,  # Placeholder
            'avg_charge_time': '45m'  # Placeholder
        })
    
    @app.route('/api/settings', methods=['POST'])
    def save_settings():
        data = request.json
        try:
            # Update profile settings
            monitor.config_manager.update_profile(
                monitor.active_profile.name,
                **data
            )
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    
    @app.route('/api/export')
    def export_data():
        # Export battery data
        # Placeholder - would implement CSV/JSON export
        return jsonify({'message': 'Export not yet implemented'}), 501
    
    @socketio.on('connect')
    def handle_connect():
        print('WebSocket client connected')
        emit('connected', {'status': 'ok'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print('WebSocket client disconnected')
    
    return app, socketio


def main():
    """Main entry point"""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Enhanced Battery Monitor")
    parser.add_argument("threshold", nargs="?", type=int, help="Threshold percent")
    parser.add_argument("interval", nargs="?", type=int, help="Poll interval seconds")
    parser.add_argument("--web", action="store_true", help="Start web interface")
    parser.add_argument("--tray", action="store_true", help="Start system tray app")
    parser.add_argument("--profile", type=str, help="Use specific profile")
    parser.add_argument("--install-startup", action="store_true", help="Install auto-start task")
    parser.add_argument("--remove-startup", action="store_true", help="Remove auto-start task")
    
    args = parser.parse_args()
    
    # Handle startup task installation
    if args.install_startup:
        if WindowsTaskScheduler.create_startup_task(args="--web --tray"):
            print("Auto-start task installed successfully!")
        else:
            print("Failed to install auto-start task.")
        return
    
    if args.remove_startup:
        if WindowsTaskScheduler.remove_startup_task():
            print("Auto-start task removed successfully!")
        else:
            print("Failed to remove auto-start task.")
        return
    
    # Create monitor
    monitor = EnhancedBatteryMonitor(args.threshold, args.interval)
    
    # Set profile if specified
    if args.profile:
        try:
            monitor.config_manager.set_active_profile(args.profile)
            monitor.active_profile = monitor.config_manager.get_active_profile()
            print(f"Using profile: {args.profile}")
        except ValueError as e:
            print(f"Error: {e}")
            return
    
    # Start web interface if requested
    if args.web:
        app, socketio = create_flask_app(monitor)
        
        def run_flask():
            socketio.run(app, host='127.0.0.1', port=5000, debug=False, allow_unsafe_werkzeug=True)
        
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        time.sleep(1)
        webbrowser.open('http://127.0.0.1:5000')
        print("Web interface started at http://127.0.0.1:5000")
    
    # Start system tray if requested
    if args.tray:
        try:
            from tray_app import start_tray_app
            monitor.tray_app = start_tray_app(monitor)
            print("System tray app started")
        except ImportError as e:
            print(f"System tray not available: {e}")
    
    # Start monitoring
    monitor.start()


if __name__ == "__main__":
    main()
