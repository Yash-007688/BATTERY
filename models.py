"""
Database models for Battery Monitor
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Device(Base):
    """Represents a monitored device (laptop or phone)"""
    __tablename__ = 'devices'
    
    id = Column(Integer, primary_key=True)
    device_id = Column(String(100), unique=True, nullable=False)  # Serial number or ADB ID
    device_type = Column(String(20), nullable=False)  # 'laptop' or 'phone'
    device_name = Column(String(100))
    technology = Column(String(50))  # Battery technology (Li-ion, etc.)
    design_capacity = Column(Integer)  # in mWh
    created_at = Column(DateTime, default=datetime.now)
    last_seen = Column(DateTime, default=datetime.now)
    
    # Relationships
    readings = relationship('BatteryReading', back_populates='device', cascade='all, delete-orphan')
    cycles = relationship('ChargeCycle', back_populates='device', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Device(id={self.device_id}, type={self.device_type})>"


class BatteryReading(Base):
    """Individual battery reading/measurement"""
    __tablename__ = 'battery_readings'
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    
    # Battery metrics
    percentage = Column(Float, nullable=False)
    voltage = Column(Integer)  # in mV
    temperature = Column(Integer)  # in 0.1°C
    is_charging = Column(Boolean, nullable=False)
    health_status = Column(String(50))
    
    # Calculated fields
    delta_1m = Column(Float)  # 1-minute percentage change
    
    # Relationships
    device = relationship('Device', back_populates='readings')
    
    def __repr__(self):
        return f"<BatteryReading(device={self.device_id}, {self.percentage}%, {self.timestamp})>"


class ChargeCycle(Base):
    """Represents a complete charge cycle"""
    __tablename__ = 'charge_cycles'
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    
    start_percentage = Column(Float, nullable=False)
    end_percentage = Column(Float)
    target_percentage = Column(Float)  # Threshold that was set
    
    duration_seconds = Column(Integer)
    min_delta_1m = Column(Float)
    max_delta_1m = Column(Float)
    avg_delta_1m = Column(Float)
    
    completed = Column(Boolean, default=False)
    
    # Relationships
    device = relationship('Device', back_populates='cycles')
    
    def __repr__(self):
        return f"<ChargeCycle(device={self.device_id}, {self.start_percentage}%->{self.end_percentage}%)>"


class NotificationLog(Base):
    """Log of all notifications sent"""
    __tablename__ = 'notification_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    
    notification_type = Column(String(20), nullable=False)  # 'desktop', 'email', 'sms', 'sound'
    device_type = Column(String(20))  # 'laptop' or 'phone'
    
    title = Column(String(200))
    message = Column(Text)
    
    threshold = Column(Float)
    battery_percentage = Column(Float)
    
    action_taken = Column(String(20))  # 'snooze', 'dismiss', None
    
    def __repr__(self):
        return f"<NotificationLog({self.notification_type}, {self.timestamp})>"


class UserProfile(Base):
    """User configuration profiles"""
    __tablename__ = 'user_profiles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=False)
    
    # Settings
    threshold_percent = Column(Integer, default=80)
    poll_interval_seconds = Column(Integer, default=30)
    
    # Notification preferences
    enable_desktop_notifications = Column(Boolean, default=True)
    enable_sound = Column(Boolean, default=True)
    enable_email = Column(Boolean, default=False)
    enable_sms = Column(Boolean, default=False)
    
    custom_sound_path = Column(String(500))
    email_address = Column(String(200))
    phone_number = Column(String(20))
    
    # Advanced settings
    enable_adaptive_polling = Column(Boolean, default=False)
    enable_ml_predictions = Column(Boolean, default=True)
    dark_mode = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<UserProfile(name={self.name}, active={self.is_active})>"
