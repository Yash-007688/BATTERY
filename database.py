"""
Database manager for Battery Monitor
"""
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import sessionmaker, Session
from models import Base, Device, BatteryReading, ChargeCycle, NotificationLog, UserProfile


class DatabaseManager:
    """Manages all database operations"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 'battery_monitor.db')
        
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()
    
    # Device operations
    def get_or_create_device(self, device_id: str, device_type: str, **kwargs) -> Device:
        """Get existing device or create new one"""
        session = self.get_session()
        try:
            device = session.query(Device).filter_by(device_id=device_id).first()
            if device is None:
                device = Device(
                    device_id=device_id,
                    device_type=device_type,
                    **kwargs
                )
                session.add(device)
                session.commit()
                session.refresh(device)
            else:
                # Update last_seen
                device.last_seen = datetime.now()
                session.commit()
            return device
        finally:
            session.close()
    
    def update_device(self, device_id: str, **kwargs):
        """Update device information"""
        session = self.get_session()
        try:
            device = session.query(Device).filter_by(device_id=device_id).first()
            if device:
                for key, value in kwargs.items():
                    if hasattr(device, key):
                        setattr(device, key, value)
                device.last_seen = datetime.now()
                session.commit()
        finally:
            session.close()
    
    # Battery reading operations
    def add_reading(self, device_id: str, percentage: float, is_charging: bool, 
                   voltage: int = None, temperature: int = None, 
                   health_status: str = None, delta_1m: float = None) -> BatteryReading:
        """Add a new battery reading"""
        session = self.get_session()
        try:
            device = session.query(Device).filter_by(device_id=device_id).first()
            if device is None:
                raise ValueError(f"Device {device_id} not found")
            
            reading = BatteryReading(
                device_id=device.id,
                percentage=percentage,
                voltage=voltage,
                temperature=temperature,
                is_charging=is_charging,
                health_status=health_status,
                delta_1m=delta_1m
            )
            session.add(reading)
            session.commit()
            session.refresh(reading)
            return reading
        finally:
            session.close()
    
    def get_recent_readings(self, device_id: str, hours: int = 24, limit: int = None) -> List[BatteryReading]:
        """Get recent readings for a device"""
        session = self.get_session()
        try:
            device = session.query(Device).filter_by(device_id=device_id).first()
            if device is None:
                return []
            
            since = datetime.now() - timedelta(hours=hours)
            query = session.query(BatteryReading).filter(
                and_(
                    BatteryReading.device_id == device.id,
                    BatteryReading.timestamp >= since
                )
            ).order_by(BatteryReading.timestamp.desc())
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
        finally:
            session.close()
    
    def get_reading_stats(self, device_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get statistics for recent readings"""
        session = self.get_session()
        try:
            device = session.query(Device).filter_by(device_id=device_id).first()
            if device is None:
                return {}
            
            since = datetime.now() - timedelta(hours=hours)
            stats = session.query(
                func.avg(BatteryReading.percentage).label('avg_percentage'),
                func.min(BatteryReading.percentage).label('min_percentage'),
                func.max(BatteryReading.percentage).label('max_percentage'),
                func.avg(BatteryReading.temperature).label('avg_temperature'),
                func.count(BatteryReading.id).label('count')
            ).filter(
                and_(
                    BatteryReading.device_id == device.id,
                    BatteryReading.timestamp >= since
                )
            ).first()
            
            return {
                'avg_percentage': round(stats.avg_percentage, 1) if stats.avg_percentage else 0,
                'min_percentage': round(stats.min_percentage, 1) if stats.min_percentage else 0,
                'max_percentage': round(stats.max_percentage, 1) if stats.max_percentage else 0,
                'avg_temperature': round(stats.avg_temperature / 10.0, 1) if stats.avg_temperature else None,
                'reading_count': stats.count or 0
            }
        finally:
            session.close()
    
    # Charge cycle operations
    def start_charge_cycle(self, device_id: str, start_percentage: float, 
                          target_percentage: float) -> ChargeCycle:
        """Start a new charge cycle"""
        session = self.get_session()
        try:
            device = session.query(Device).filter_by(device_id=device_id).first()
            if device is None:
                raise ValueError(f"Device {device_id} not found")
            
            cycle = ChargeCycle(
                device_id=device.id,
                start_time=datetime.now(),
                start_percentage=start_percentage,
                target_percentage=target_percentage,
                completed=False
            )
            session.add(cycle)
            session.commit()
            session.refresh(cycle)
            return cycle
        finally:
            session.close()
    
    def end_charge_cycle(self, cycle_id: int, end_percentage: float, 
                        min_delta: float = None, max_delta: float = None, 
                        avg_delta: float = None):
        """End a charge cycle"""
        session = self.get_session()
        try:
            cycle = session.query(ChargeCycle).filter_by(id=cycle_id).first()
            if cycle:
                cycle.end_time = datetime.now()
                cycle.end_percentage = end_percentage
                cycle.duration_seconds = int((cycle.end_time - cycle.start_time).total_seconds())
                cycle.min_delta_1m = min_delta
                cycle.max_delta_1m = max_delta
                cycle.avg_delta_1m = avg_delta
                cycle.completed = True
                session.commit()
        finally:
            session.close()
    
    def get_active_cycle(self, device_id: str) -> Optional[ChargeCycle]:
        """Get active (incomplete) charge cycle for device"""
        session = self.get_session()
        try:
            device = session.query(Device).filter_by(device_id=device_id).first()
            if device is None:
                return None
            
            return session.query(ChargeCycle).filter(
                and_(
                    ChargeCycle.device_id == device.id,
                    ChargeCycle.completed == False
                )
            ).first()
        finally:
            session.close()
    
    def get_charge_history(self, device_id: str, limit: int = 10) -> List[ChargeCycle]:
        """Get recent completed charge cycles"""
        session = self.get_session()
        try:
            device = session.query(Device).filter_by(device_id=device_id).first()
            if device is None:
                return []
            
            return session.query(ChargeCycle).filter(
                and_(
                    ChargeCycle.device_id == device.id,
                    ChargeCycle.completed == True
                )
            ).order_by(ChargeCycle.end_time.desc()).limit(limit).all()
        finally:
            session.close()
    
    # Notification log operations
    def log_notification(self, notification_type: str, device_type: str = None,
                        title: str = None, message: str = None,
                        threshold: float = None, battery_percentage: float = None,
                        action_taken: str = None) -> NotificationLog:
        """Log a notification"""
        session = self.get_session()
        try:
            log = NotificationLog(
                notification_type=notification_type,
                device_type=device_type,
                title=title,
                message=message,
                threshold=threshold,
                battery_percentage=battery_percentage,
                action_taken=action_taken
            )
            session.add(log)
            session.commit()
            session.refresh(log)
            return log
        finally:
            session.close()
    
    def get_notification_history(self, hours: int = 24, limit: int = 50) -> List[NotificationLog]:
        """Get recent notifications"""
        session = self.get_session()
        try:
            since = datetime.now() - timedelta(hours=hours)
            return session.query(NotificationLog).filter(
                NotificationLog.timestamp >= since
            ).order_by(NotificationLog.timestamp.desc()).limit(limit).all()
        finally:
            session.close()
    
    # Profile operations
    def create_profile(self, name: str, **kwargs) -> UserProfile:
        """Create a new user profile"""
        session = self.get_session()
        try:
            profile = UserProfile(name=name, **kwargs)
            session.add(profile)
            session.commit()
            session.refresh(profile)
            return profile
        finally:
            session.close()
    
    def get_profile(self, name: str) -> Optional[UserProfile]:
        """Get profile by name"""
        session = self.get_session()
        try:
            return session.query(UserProfile).filter_by(name=name).first()
        finally:
            session.close()
    
    def get_active_profile(self) -> Optional[UserProfile]:
        """Get the currently active profile"""
        session = self.get_session()
        try:
            return session.query(UserProfile).filter_by(is_active=True).first()
        finally:
            session.close()
    
    def set_active_profile(self, name: str):
        """Set a profile as active (deactivates others)"""
        session = self.get_session()
        try:
            # Deactivate all profiles
            session.query(UserProfile).update({'is_active': False})
            # Activate the specified profile
            profile = session.query(UserProfile).filter_by(name=name).first()
            if profile:
                profile.is_active = True
                session.commit()
        finally:
            session.close()
    
    def get_all_profiles(self) -> List[UserProfile]:
        """Get all profiles"""
        session = self.get_session()
        try:
            return session.query(UserProfile).all()
        finally:
            session.close()
    
    def update_profile(self, name: str, **kwargs):
        """Update profile settings"""
        session = self.get_session()
        try:
            profile = session.query(UserProfile).filter_by(name=name).first()
            if profile:
                for key, value in kwargs.items():
                    if hasattr(profile, key):
                        setattr(profile, key, value)
                profile.updated_at = datetime.now()
                session.commit()
        finally:
            session.close()
    
    def delete_profile(self, name: str):
        """Delete a profile"""
        session = self.get_session()
        try:
            profile = session.query(UserProfile).filter_by(name=name).first()
            if profile:
                session.delete(profile)
                session.commit()
        finally:
            session.close()
    
    # Cleanup operations
    def cleanup_old_data(self, days: int = 30):
        """Remove old readings and logs"""
        session = self.get_session()
        try:
            cutoff = datetime.now() - timedelta(days=days)
            
            # Delete old readings
            session.query(BatteryReading).filter(
                BatteryReading.timestamp < cutoff
            ).delete()
            
            # Delete old notification logs
            session.query(NotificationLog).filter(
                NotificationLog.timestamp < cutoff
            ).delete()
            
            session.commit()
        finally:
            session.close()
