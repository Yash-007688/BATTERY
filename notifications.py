"""
Advanced notification manager for Battery Monitor
Supports desktop, email, SMS, and custom sounds
"""
import os
import sys
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, List
from pathlib import Path

try:
    import winsound
except ImportError:
    winsound = None

try:
    from plyer import notification as plyer_notification
except ImportError:
    plyer_notification = None

try:
    from twilio.rest import Client as TwilioClient
except ImportError:
    TwilioClient = None


class NotificationManager:
    """Manages all types of notifications"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.sounds_dir = os.path.join(os.path.dirname(__file__), 'sounds')
        
        # Email configuration
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('SMTP_FROM_EMAIL')
        
        # Configure from environment if available
        self.configure_email_from_env()
        
        # SMS configuration (Twilio)
        self.twilio_account_sid = None
        self.twilio_auth_token = None
        self.twilio_from_number = None
        
        # Create sounds directory if it doesn't exist
        os.makedirs(self.sounds_dir, exist_ok=True)
    
    def configure_email_from_env(self):
        """Configure email from environment variables"""
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('SMTP_FROM_EMAIL') or os.getenv('SMTP_USERNAME')
    
    def configure_email(self, smtp_server: str, smtp_port: int, 
                       username: str, password: str, from_email: str = None):
        """Configure email settings"""
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_username = username
        self.smtp_password = password
        self.from_email = from_email or username
    
    def configure_sms(self, account_sid: str, auth_token: str, from_number: str):
        """Configure SMS settings (Twilio)"""
        if TwilioClient is None:
            raise ImportError("Twilio library not installed. Install with: pip install twilio")
        self.twilio_account_sid = account_sid
        self.twilio_auth_token = auth_token
        self.twilio_from_number = from_number
    
    def play_sound(self, sound_name: str = None, frequency: int = 1000, 
                  duration: int = 300, times: int = 1):
        """Play notification sound"""
        try:
            if sound_name and os.path.exists(sound_name):
                # Play custom sound file
                if winsound:
                    winsound.PlaySound(sound_name, winsound.SND_FILENAME)
            else:
                # Play beep
                if winsound:
                    for i in range(times):
                        freq = frequency if i % 2 == 0 else frequency + 400
                        winsound.Beep(freq, duration)
                        if i < times - 1:
                            time.sleep(0.07)
                else:
                    # Fallback to terminal bell
                    for _ in range(times):
                        sys.stdout.write('\a')
                        sys.stdout.flush()
                        time.sleep(0.1)
            
            # Log notification
            if self.db_manager:
                self.db_manager.log_notification(
                    notification_type='sound',
                    title=f'Sound: {sound_name or "beep"}',
                    message=f'Played {times} time(s)'
                )
        except (OSError, RuntimeError) as e:
            print(f"Error playing sound: {e}")
    
    def send_desktop_notification(self, title: str, message: str, 
                                  timeout: int = 10, device_type: str = None,
                                  threshold: float = None, battery_percentage: float = None):
        """Send desktop notification"""
        try:
            if plyer_notification:
                plyer_notification.notify(
                    title=title,
                    message=message,
                    timeout=timeout
                )
                
                # Log notification
                if self.db_manager:
                    self.db_manager.log_notification(
                        notification_type='desktop',
                        device_type=device_type,
                        title=title,
                        message=message,
                        threshold=threshold,
                        battery_percentage=battery_percentage
                    )
                return True
            else:
                print(f"Desktop notification: {title} - {message}")
                return False
        except Exception as e:
            print(f"Error sending desktop notification: {e}")
            return False
    
    def send_email(self, to_email: str, subject: str, body: str,
                  device_type: str = None, threshold: float = None, 
                  battery_percentage: float = None):
        """Send email notification"""
        if not all([self.smtp_server, self.smtp_port, self.smtp_username, self.smtp_password]):
            print("Email not configured. Use configure_email() first.")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            # Log notification
            if self.db_manager:
                self.db_manager.log_notification(
                    notification_type='email',
                    device_type=device_type,
                    title=subject,
                    message=body,
                    threshold=threshold,
                    battery_percentage=battery_percentage
                )
            
            print(f"Email sent to {to_email}")
            return True
        except smtplib.SMTPException as e:
            print(f"SMTP error sending email: {e}")
        except OSError as e:
            print(f"Network error sending email: {e}")
        else:
            return True
        return False
    
    def send_sms(self, to_number: str, message: str,
                device_type: str = None, threshold: float = None,
                battery_percentage: float = None):
        """Send SMS notification via Twilio"""
        if not all([self.twilio_account_sid, self.twilio_auth_token, self.twilio_from_number]):
            print("SMS not configured. Use configure_sms() first.")
            return False
        
        if TwilioClient is None:
            print("Twilio library not installed. Install with: pip install twilio")
            return False
        
        try:
            client = TwilioClient(self.twilio_account_sid, self.twilio_auth_token)
            
            sms = client.messages.create(
                body=message,
                from_=self.twilio_from_number,
                to=to_number
            )
            
            # Log notification
            if self.db_manager:
                self.db_manager.log_notification(
                    notification_type='sms',
                    device_type=device_type,
                    title='SMS Alert',
                    message=message,
                    threshold=threshold,
                    battery_percentage=battery_percentage
                )
            
            print(f"SMS sent to {to_number}: {sms.sid}")
            return True
        except Exception as e:
            print(f"Error sending SMS: {e}")
            return False
    
    def send_threshold_alert(self, device_type: str, battery_percentage: float,
                           threshold: float, profile_settings: dict = None):
        """Send threshold alert using configured methods"""
        title = f"Battery Monitor - {device_type.capitalize()}"
        message = f"Battery reached {threshold}% threshold! Current: {battery_percentage:.0f}%"
        
        settings = profile_settings or {}
        
        # Desktop notification
        if settings.get('enable_desktop_notifications', True):
            self.send_desktop_notification(
                title=title,
                message=message,
                device_type=device_type,
                threshold=threshold,
                battery_percentage=battery_percentage
            )
        
        # Sound
        if settings.get('enable_sound', True):
            custom_sound = settings.get('custom_sound_path')
            if custom_sound and os.path.exists(custom_sound):
                self.play_sound(sound_name=custom_sound)
            else:
                self.play_sound(times=5, frequency=1000, duration=250)
        
        # Email
        if settings.get('enable_email', False) and settings.get('email_address'):
            email_body = f"""
Battery Monitor Alert

Device: {device_type.capitalize()}
Current Battery: {battery_percentage:.0f}%
Threshold: {threshold}%
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Your battery has reached the configured threshold.
Consider unplugging the charger to preserve battery health.
            """
            self.send_email(
                to_email=settings['email_address'],
                subject=title,
                body=email_body.strip(),
                device_type=device_type,
                threshold=threshold,
                battery_percentage=battery_percentage
            )
        
        # SMS
        if settings.get('enable_sms', False) and settings.get('phone_number'):
            sms_message = f"Battery Alert: {device_type.capitalize()} at {battery_percentage:.0f}% (threshold: {threshold}%)"
            self.send_sms(
                to_number=settings['phone_number'],
                message=sms_message,
                device_type=device_type,
                threshold=threshold,
                battery_percentage=battery_percentage
            )
    
    def get_notification_history(self, hours: int = 24) -> List:
        """Get recent notification history"""
        if self.db_manager:
            return self.db_manager.get_notification_history(hours=hours)
        return []
    
    def get_available_sounds(self) -> List[str]:
        """Get list of available custom sound files"""
        if not os.path.exists(self.sounds_dir):
            return []
        
        sound_extensions = ['.wav', '.mp3', '.ogg']
        sounds = []
        
        for file in os.listdir(self.sounds_dir):
            if any(file.lower().endswith(ext) for ext in sound_extensions):
                sounds.append(os.path.join(self.sounds_dir, file))
        
        return sounds


# Preset notification templates
class NotificationTemplates:
    """Predefined notification templates"""
    
    @staticmethod
    def battery_threshold(device_type: str, percentage: float, threshold: float) -> dict:
        return {
            'title': f'Battery Monitor - {device_type.capitalize()}',
            'message': f'Battery reached {threshold}% threshold! Current: {percentage:.0f}%'
        }
    
    @staticmethod
    def battery_full(device_type: str) -> dict:
        return {
            'title': f'Battery Full - {device_type.capitalize()}',
            'message': 'Battery is fully charged. Consider unplugging the charger.'
        }
    
    @staticmethod
    def battery_low(device_type: str, percentage: float) -> dict:
        return {
            'title': f'Low Battery - {device_type.capitalize()}',
            'message': f'Battery is low at {percentage:.0f}%. Please plug in the charger.'
        }
    
    @staticmethod
    def battery_health_warning(device_type: str, health_status: str) -> dict:
        return {
            'title': f'Battery Health Warning - {device_type.capitalize()}',
            'message': f'Battery health: {health_status}. Consider battery replacement.'
        }
    
    @staticmethod
    def temperature_warning(device_type: str, temperature: float) -> dict:
        return {
            'title': f'Temperature Warning - {device_type.capitalize()}',
            'message': f'Battery temperature is high: {temperature:.1f}°C. Unplug and let it cool down.'
        }
