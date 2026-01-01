"""
Scheduler for Battery Monitor
Handles scheduled monitoring and Windows Task Scheduler integration
"""
import os
import sys
import subprocess
from datetime import datetime, time
from typing import Optional, Tuple
import threading
from xml.sax.saxutils import escape as xml_escape


class MonitorScheduler:
    """Handles scheduled monitoring"""
    
    def __init__(self, start_time: str = None, stop_time: str = None):
        """
        Initialize scheduler
        Args:
            start_time: Time to start monitoring (HH:MM format)
            stop_time: Time to stop monitoring (HH:MM format)
        """
        self.start_time = self._parse_time(start_time) if start_time else None
        self.stop_time = self._parse_time(stop_time) if stop_time else None
        self.enabled = False
        self.check_interval = 60  # Check every minute
        self._stop_event = threading.Event()
        self._scheduler_thread = None
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string in HH:MM format"""
        try:
            hour, minute = map(int, time_str.split(':'))
            return time(hour=hour, minute=minute)
        except Exception as e:
            raise ValueError(f"Invalid time format: {time_str}. Use HH:MM format")
    
    def set_schedule(self, start_time: str, stop_time: str):
        """Set monitoring schedule"""
        self.start_time = self._parse_time(start_time)
        self.stop_time = self._parse_time(stop_time)
    
    def enable(self):
        """Enable scheduled monitoring"""
        self.enabled = True
    
    def disable(self):
        """Disable scheduled monitoring"""
        self.enabled = False
    
    def should_monitor_now(self) -> bool:
        """Check if monitoring should be active at current time"""
        if not self.enabled or not self.start_time or not self.stop_time:
            return True  # Always monitor if scheduling disabled
        
        current_time = datetime.now().time()
        
        if self.start_time < self.stop_time:
            # Normal case: start=09:00, stop=17:00
            return self.start_time <= current_time <= self.stop_time
        else:
            # Overnight case: start=22:00, stop=07:00
            return current_time >= self.start_time or current_time <= self.stop_time
    
    def get_next_transition(self) -> Tuple[str, datetime]:
        """
        Get next schedule transition (start or stop)
        Returns: (action, datetime) where action is 'start' or 'stop'
        """
        if not self.enabled or not self.start_time or not self.stop_time:
            return None, None
        
        now = datetime.now()
        current_time = now.time()
        
        # Calculate next start time
        next_start = datetime.combine(now.date(), self.start_time)
        if current_time >= self.start_time:
            next_start = datetime.combine(now.date(), self.start_time)
            next_start = next_start.replace(day=next_start.day + 1)
        
        # Calculate next stop time
        next_stop = datetime.combine(now.date(), self.stop_time)
        if current_time >= self.stop_time:
            next_stop = next_stop.replace(day=next_stop.day + 1)
        
        # Determine which comes first
        if next_start < next_stop:
            return 'start', next_start
        else:
            return 'stop', next_stop
    
    def start_scheduler(self, on_start_callback=None, on_stop_callback=None):
        """Start the scheduler thread"""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            args=(on_start_callback, on_stop_callback),
            daemon=True
        )
        self._scheduler_thread.start()
    
    def stop_scheduler(self):
        """Stop the scheduler thread"""
        self._stop_event.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=2)
    
    def _scheduler_loop(self, on_start_callback, on_stop_callback):
        """Main scheduler loop"""
        was_monitoring = self.should_monitor_now()
        
        while not self._stop_event.is_set():
            should_monitor = self.should_monitor_now()
            
            # Check for state change
            if should_monitor and not was_monitoring:
                # Start monitoring
                print(f"[Scheduler] Starting monitoring at {datetime.now().strftime('%H:%M:%S')}")
                if on_start_callback:
                    on_start_callback()
            elif not should_monitor and was_monitoring:
                # Stop monitoring
                print(f"[Scheduler] Stopping monitoring at {datetime.now().strftime('%H:%M:%S')}")
                if on_stop_callback:
                    on_stop_callback()
            
            was_monitoring = should_monitor
            
            # Sleep for check interval
            self._stop_event.wait(self.check_interval)


class WindowsTaskScheduler:
    """Windows Task Scheduler integration for auto-start"""
    
    TASK_NAME = "BatteryMonitorAutoStart"
    
    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows"""
        return sys.platform == 'win32'
    
    @staticmethod
    def create_startup_task(script_path: str = None, args: str = "") -> bool:
        """
        Create Windows Task Scheduler task for auto-start
        Args:
            script_path: Path to the Python script (defaults to current app.py)
            args: Additional command-line arguments
        """
        if not WindowsTaskScheduler.is_windows():
            print("Windows Task Scheduler is only available on Windows")
            return False
        
        if script_path is None:
            script_path = os.path.abspath(sys.argv[0])
        
        python_exe = sys.executable
        
        # Escape special characters in paths and args
        script_path_escaped = xml_escape(script_path)
        args_escaped = xml_escape(args)
        working_dir_escaped = xml_escape(os.path.dirname(script_path))
        
        # Create XML for task
        task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Battery Monitor - Auto-start on login</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions>
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>"{script_path_escaped}" {args_escaped}</Arguments>
      <WorkingDirectory>{working_dir_escaped}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""
        
        # Save XML to temp file
        temp_xml = os.path.join(os.path.dirname(script_path), 'battery_monitor_task.xml')
        try:
            with open(temp_xml, 'w', encoding='utf-16') as f:
                f.write(task_xml)
            
            # Create task using schtasks
            cmd = [
                'schtasks',
                '/Create',
                '/TN', WindowsTaskScheduler.TASK_NAME,
                '/XML', temp_xml,
                '/F'  # Force overwrite if exists
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Clean up temp file
            os.remove(temp_xml)
            
            if result.returncode == 0:
                print(f"Successfully created startup task: {WindowsTaskScheduler.TASK_NAME}")
                return True
            else:
                print(f"Failed to create startup task: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error creating startup task: {e}")
            if os.path.exists(temp_xml):
                os.remove(temp_xml)
            return False
    
    @staticmethod
    def remove_startup_task() -> bool:
        """Remove the auto-start task"""
        if not WindowsTaskScheduler.is_windows():
            return False
        
        try:
            cmd = [
                'schtasks',
                '/Delete',
                '/TN', WindowsTaskScheduler.TASK_NAME,
                '/F'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Successfully removed startup task: {WindowsTaskScheduler.TASK_NAME}")
                return True
            else:
                print(f"Failed to remove startup task: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error removing startup task: {e}")
            return False
    
    @staticmethod
    def task_exists() -> bool:
        """Check if the auto-start task exists"""
        if not WindowsTaskScheduler.is_windows():
            return False
        
        try:
            cmd = [
                'schtasks',
                '/Query',
                '/TN', WindowsTaskScheduler.TASK_NAME
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception:
            return False
    
    @staticmethod
    def enable_task() -> bool:
        """Enable the auto-start task"""
        if not WindowsTaskScheduler.is_windows():
            return False
        
        try:
            cmd = [
                'schtasks',
                '/Change',
                '/TN', WindowsTaskScheduler.TASK_NAME,
                '/ENABLE'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error enabling task: {e}")
            return False
    
    @staticmethod
    def disable_task() -> bool:
        """Disable the auto-start task"""
        if not WindowsTaskScheduler.is_windows():
            return False
        
        try:
            cmd = [
                'schtasks',
                '/Change',
                '/TN', WindowsTaskScheduler.TASK_NAME,
                '/DISABLE'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error disabling task: {e}")
            return False
