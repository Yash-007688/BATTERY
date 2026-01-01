"""
Multi-device manager for Battery Monitor
Handles multiple phones and device profiles
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DeviceProfile:
    """Profile for a monitored device"""
    device_id: str
    device_type: str  # 'laptop' or 'phone'
    device_name: str
    threshold: int = 80
    priority: int = 0  # Higher priority = monitored first
    enabled: bool = True
    last_seen: datetime = None
    
    # Device-specific settings
    technology: str = None
    design_capacity: int = None
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = datetime.now()


class DeviceManager:
    """Manages multiple monitored devices"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.devices: Dict[str, DeviceProfile] = {}
        self.active_device_id: Optional[str] = None
        
        # Load devices from database
        if db_manager:
            self.load_devices_from_db()
    
    def load_devices_from_db(self):
        """Load device profiles from database"""
        # This would query the database for known devices
        # For now, we'll discover devices dynamically
        pass
    
    def register_device(self, device_id: str, device_type: str, 
                       device_name: str = None, **kwargs) -> DeviceProfile:
        """Register a new device or update existing one"""
        if device_id in self.devices:
            # Update existing device
            profile = self.devices[device_id]
            profile.last_seen = datetime.now()
            if device_name:
                profile.device_name = device_name
            for key, value in kwargs.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
        else:
            # Create new device profile
            if device_name is None:
                device_name = f"{device_type.capitalize()} ({device_id[:8]})"
            
            profile = DeviceProfile(
                device_id=device_id,
                device_type=device_type,
                device_name=device_name,
                **kwargs
            )
            self.devices[device_id] = profile
            
            # Save to database
            if self.db_manager:
                self.db_manager.get_or_create_device(
                    device_id=device_id,
                    device_type=device_type,
                    device_name=device_name,
                    **kwargs
                )
        
        return profile
    
    def get_device(self, device_id: str) -> Optional[DeviceProfile]:
        """Get device profile by ID"""
        return self.devices.get(device_id)
    
    def get_all_devices(self) -> List[DeviceProfile]:
        """Get all registered devices"""
        return list(self.devices.values())
    
    def get_enabled_devices(self) -> List[DeviceProfile]:
        """Get all enabled devices"""
        return [d for d in self.devices.values() if d.enabled]
    
    def get_devices_by_type(self, device_type: str) -> List[DeviceProfile]:
        """Get all devices of a specific type"""
        return [d for d in self.devices.values() if d.device_type == device_type]
    
    def set_active_device(self, device_id: str):
        """Set the currently active/monitored device"""
        if device_id in self.devices:
            self.active_device_id = device_id
            return True
        return False
    
    def get_active_device(self) -> Optional[DeviceProfile]:
        """Get the currently active device"""
        if self.active_device_id:
            return self.devices.get(self.active_device_id)
        return None
    
    def get_priority_device(self) -> Optional[DeviceProfile]:
        """Get highest priority enabled device"""
        enabled = self.get_enabled_devices()
        if not enabled:
            return None
        
        # Sort by priority (descending), then by last_seen (most recent first)
        enabled.sort(key=lambda d: (d.priority, d.last_seen), reverse=True)
        return enabled[0]
    
    def update_device_threshold(self, device_id: str, threshold: int):
        """Update threshold for a specific device"""
        if device_id in self.devices:
            self.devices[device_id].threshold = threshold
            
            # Update in database
            if self.db_manager:
                self.db_manager.update_device(device_id, threshold=threshold)
    
    def enable_device(self, device_id: str):
        """Enable monitoring for a device"""
        if device_id in self.devices:
            self.devices[device_id].enabled = True
    
    def disable_device(self, device_id: str):
        """Disable monitoring for a device"""
        if device_id in self.devices:
            self.devices[device_id].enabled = False
    
    def set_device_priority(self, device_id: str, priority: int):
        """Set priority for a device"""
        if device_id in self.devices:
            self.devices[device_id].priority = priority
    
    def remove_device(self, device_id: str):
        """Remove a device from monitoring"""
        if device_id in self.devices:
            del self.devices[device_id]
    
    def get_device_comparison(self) -> List[Dict]:
        """Get comparison data for all devices"""
        comparison = []
        
        for device in self.devices.values():
            data = {
                'device_id': device.device_id,
                'device_name': device.device_name,
                'device_type': device.device_type,
                'threshold': device.threshold,
                'enabled': device.enabled,
                'last_seen': device.last_seen
            }
            
            # Get latest battery reading from database
            if self.db_manager:
                readings = self.db_manager.get_recent_readings(device.device_id, hours=1, limit=1)
                if readings:
                    latest = readings[0]
                    data['percentage'] = latest.percentage
                    data['voltage'] = latest.voltage
                    data['temperature'] = latest.temperature
                    data['is_charging'] = latest.is_charging
            
            comparison.append(data)
        
        return comparison
    
    def auto_select_device(self, laptop_available: bool = False, 
                          phones_charging: List[str] = None) -> Optional[str]:
        """
        Automatically select which device to monitor based on availability
        Priority: Charging phones > Laptop (if plugged) > Highest priority device
        """
        if phones_charging:
            # Prioritize charging phones
            for phone_id in phones_charging:
                if phone_id in self.devices and self.devices[phone_id].enabled:
                    return phone_id
        
        # Get priority device
        priority_device = self.get_priority_device()
        if priority_device:
            return priority_device.device_id
        
        return None
    
    def cleanup_stale_devices(self, hours: int = 24):
        """Remove devices not seen in specified hours"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=hours)
        
        stale_devices = [
            device_id for device_id, device in self.devices.items()
            if device.last_seen < cutoff
        ]
        
        for device_id in stale_devices:
            print(f"Removing stale device: {self.devices[device_id].device_name}")
            del self.devices[device_id]
        
        return len(stale_devices)
    
    def export_profiles(self) -> List[Dict]:
        """Export all device profiles"""
        return [
            {
                'device_id': d.device_id,
                'device_type': d.device_type,
                'device_name': d.device_name,
                'threshold': d.threshold,
                'priority': d.priority,
                'enabled': d.enabled,
                'technology': d.technology,
                'design_capacity': d.design_capacity
            }
            for d in self.devices.values()
        ]
    
    def import_profiles(self, profiles: List[Dict]):
        """Import device profiles"""
        for profile_data in profiles:
            device_id = profile_data.pop('device_id')
            device_type = profile_data.pop('device_type')
            device_name = profile_data.pop('device_name', None)
            
            self.register_device(
                device_id=device_id,
                device_type=device_type,
                device_name=device_name,
                **profile_data
            )
