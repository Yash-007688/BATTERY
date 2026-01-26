"""
Advanced configuration manager with profiles support
"""
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import dataclasses


@dataclass
class ProfileConfig:
    """Configuration profile"""
    name: str
    threshold_percent: int = 80
    poll_interval_seconds: int = 30
    
    # Notification settings
    enable_desktop_notifications: bool = True
    enable_sound: bool = True
    enable_email: bool = False
    enable_sms: bool = False
    custom_sound_path: str = None
    email_address: str = None
    phone_number: str = None
    
    # Advanced settings
    enable_adaptive_polling: bool = False
    enable_ml_predictions: bool = True
    dark_mode: bool = False
    
    # Email configuration
    smtp_server: str = None
    smtp_port: int = 587
    smtp_username: str = None
    smtp_password: str = None
    
    # SMS configuration (Twilio)
    twilio_account_sid: str = None
    twilio_auth_token: str = None
    twilio_from_number: str = None
    
    # Scheduling
    enable_scheduling: bool = False
    start_time: str = None  # HH:MM format
    stop_time: str = None   # HH:MM format
    
    # Data retention
    data_retention_days: int = 30
    
    # Multiple thresholds
    additional_thresholds: List[int] = None

    # Discord Integration
    discord_channel_id: int = None
    enable_discord_alerts: bool = True
    
    def __post_init__(self):
        if self.additional_thresholds is None:
            self.additional_thresholds = []


class ConfigManager:
    """Manages application configuration and profiles"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'battery_config.json')
        
        self.config_path = config_path
        self.profiles: Dict[str, ProfileConfig] = {}
        self.active_profile_name: str = 'default'
        
        # Load configuration
        self.load()
        
        # Ensure default profile exists
        if 'default' not in self.profiles:
            self.create_profile('default')
    
    def load(self):
        """Load configuration from file"""
        if not os.path.exists(self.config_path):
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load active profile
            self.active_profile_name = data.get('active_profile', 'default')
            
            # Load profiles
            profiles_data = data.get('profiles', {})
            for name, profile_data in profiles_data.items():
                self.profiles[name] = ProfileConfig(name=name, **profile_data)
            
            # Legacy support: if old format, migrate
            if 'threshold_percent' in data and 'profiles' not in data:
                self._migrate_legacy_config(data)
                
        except Exception as e:
            print(f"Error loading config: {e}")
    
    def save(self):
        """Save configuration to file"""
        try:
            data = {
                'active_profile': self.active_profile_name,
                'profiles': {
                    name: {k: v for k, v in asdict(profile).items() if k != 'name'}
                    for name, profile in self.profiles.items()
                },
                'version': '2.0',
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def _migrate_legacy_config(self, old_data: Dict):
        """Migrate from old config format to new profile-based format"""
        default_profile = ProfileConfig(
            name='default',
            threshold_percent=old_data.get('threshold_percent', 80),
            poll_interval_seconds=old_data.get('poll_interval_seconds', 30)
        )
        self.profiles['default'] = default_profile
        self.save()
        print("Migrated legacy configuration to new profile format")
    
    def create_profile(self, name: str, **kwargs) -> ProfileConfig:
        """Create a new profile"""
        if name in self.profiles:
            raise ValueError(f"Profile '{name}' already exists")
        
        profile = ProfileConfig(name=name, **kwargs)
        self.profiles[name] = profile
        self.save()
        return profile
    
    def get_profile(self, name: str) -> Optional[ProfileConfig]:
        """Get a profile by name"""
        return self.profiles.get(name)
    
    def get_active_profile(self) -> ProfileConfig:
        """Get the currently active profile"""
        return self.profiles.get(self.active_profile_name, self.profiles.get('default'))
    
    def set_active_profile(self, name: str):
        """Set the active profile"""
        if name not in self.profiles:
            raise ValueError(f"Profile '{name}' does not exist")
        self.active_profile_name = name
        self.save()
    
    def update_profile(self, name: str, **kwargs):
        """Update profile settings"""
        if name not in self.profiles:
            raise ValueError(f"Profile '{name}' does not exist")
        
        profile = self.profiles[name]
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        self.save()
    
    def delete_profile(self, name: str):
        """Delete a profile"""
        if name == 'default':
            raise ValueError("Cannot delete default profile")
        
        if name not in self.profiles:
            raise ValueError(f"Profile '{name}' does not exist")
        
        # If deleting active profile, switch to default
        if name == self.active_profile_name:
            self.active_profile_name = 'default'
        
        del self.profiles[name]
        self.save()
    
    def list_profiles(self) -> List[str]:
        """Get list of all profile names"""
        return list(self.profiles.keys())
    
    def duplicate_profile(self, source_name: str, new_name: str):
        """Duplicate an existing profile"""
        if source_name not in self.profiles:
            raise ValueError(f"Source profile '{source_name}' does not exist")
        
        if new_name in self.profiles:
            raise ValueError(f"Profile '{new_name}' already exists")
        
        source = self.profiles[source_name]
        new_profile = ProfileConfig(
            name=new_name,
            **{k: v for k, v in asdict(source).items() if k != 'name'}
        )
        self.profiles[new_name] = new_profile
        self.save()
    
    def export_profile(self, name: str, export_path: str):
        """Export a profile to a file"""
        if name not in self.profiles:
            raise ValueError(f"Profile '{name}' does not exist")
        
        profile = self.profiles[name]
        data = asdict(profile)
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def import_profile(self, import_path: str, new_name: str = None):
        """Import a profile from a file"""
        with open(import_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        name = new_name or data.get('name', 'imported')
        
        # Ensure unique name
        original_name = name
        counter = 1
        while name in self.profiles:
            name = f"{original_name}_{counter}"
            counter += 1
        
        data['name'] = name
        # Filter to known ProfileConfig fields
        known_fields = {f.name for f in dataclasses.fields(ProfileConfig)}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        profile = ProfileConfig(**filtered_data)
        
        # Validate the imported profile
        issues = self.validate_profile(profile)
        if issues:
            print(f"Warning: Imported profile has validation issues: {issues}")
        
        self.profiles[name] = profile
        self.save()
        
        return name
    
    def get_preset_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get preset profile configurations"""
        return {
            'conservative': {
                'threshold_percent': 80,
                'poll_interval_seconds': 30,
                'enable_desktop_notifications': True,
                'enable_sound': True,
                'enable_adaptive_polling': True,
                'additional_thresholds': [60, 80, 90]
            },
            'aggressive': {
                'threshold_percent': 95,
                'poll_interval_seconds': 60,
                'enable_desktop_notifications': True,
                'enable_sound': False,
                'enable_adaptive_polling': False
            },
            'gaming': {
                'threshold_percent': 85,
                'poll_interval_seconds': 45,
                'enable_desktop_notifications': False,
                'enable_sound': False,
                'enable_adaptive_polling': True
            },
            'overnight': {
                'threshold_percent': 80,
                'poll_interval_seconds': 120,
                'enable_desktop_notifications': False,
                'enable_sound': False,
                'enable_adaptive_polling': False,
                'enable_scheduling': True,
                'start_time': '22:00',
                'stop_time': '07:00'
            },
            'work': {
                'threshold_percent': 80,
                'poll_interval_seconds': 30,
                'enable_desktop_notifications': True,
                'enable_sound': True,
                'enable_email': True,
                'enable_adaptive_polling': True,
                'additional_thresholds': [20, 80, 90]
            }
        }
    
    def create_from_preset(self, preset_name: str, profile_name: str = None):
        """Create a profile from a preset"""
        presets = self.get_preset_profiles()
        
        if preset_name not in presets:
            raise ValueError(f"Preset '{preset_name}' does not exist")
        
        name = profile_name or preset_name
        preset_config = presets[preset_name]
        
        return self.create_profile(name, **preset_config)
    
    def validate_profile(self, profile: ProfileConfig) -> List[str]:
        """Validate profile configuration and return list of issues"""
        issues = []
        
        # Validate threshold
        if not 1 <= profile.threshold_percent <= 100:
            issues.append("Threshold must be between 1 and 100")
        
        # Validate poll interval
        if profile.poll_interval_seconds < 5:
            issues.append("Poll interval must be at least 5 seconds")
        
        # Validate email settings
        if profile.enable_email:
            if not profile.email_address:
                issues.append("Email address required when email notifications enabled")
            if not all([profile.smtp_server, profile.smtp_username, profile.smtp_password]):
                issues.append("SMTP settings incomplete for email notifications")
        
        # Validate SMS settings
        if profile.enable_sms:
            if not profile.phone_number:
                issues.append("Phone number required when SMS notifications enabled")
            if not all([profile.twilio_account_sid, profile.twilio_auth_token, profile.twilio_from_number]):
                issues.append("Twilio settings incomplete for SMS notifications")
        
        # Validate scheduling
        if profile.enable_scheduling:
            if not profile.start_time or not profile.stop_time:
                issues.append("Start and stop times required when scheduling enabled")
        
        # Validate data retention
        if profile.data_retention_days < 1:
            issues.append("Data retention must be at least 1 day")
        
        return issues
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration"""
        active = self.get_active_profile()
        
        return {
            'active_profile': self.active_profile_name,
            'total_profiles': len(self.profiles),
            'threshold': active.threshold_percent,
            'poll_interval': active.poll_interval_seconds,
            'notifications_enabled': {
                'desktop': active.enable_desktop_notifications,
                'sound': active.enable_sound,
                'email': active.enable_email,
                'sms': active.enable_sms
            },
            'advanced_features': {
                'adaptive_polling': active.enable_adaptive_polling,
                'ml_predictions': active.enable_ml_predictions,
                'scheduling': active.enable_scheduling
            }
        }
