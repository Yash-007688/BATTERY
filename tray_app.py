"""
System Tray Application for Battery Monitor
"""
import os
import sys
import threading
from PIL import Image, ImageDraw, ImageFont
import pystray
from pystray import MenuItem as item


class TrayApp:
    """System tray application for Battery Monitor"""
    
    def __init__(self, battery_monitor):
        self.monitor = battery_monitor
        self.icon = None
        self.running = False
        self.current_percentage = 0
        self.is_charging = False
    
    def create_icon_image(self, percentage: int, is_charging: bool = False):
        """Create dynamic battery icon with percentage"""
        # Create image
        width = 64
        height = 64
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Determine color based on percentage
        if percentage >= 80:
            color = (76, 222, 128)  # Green
        elif percentage >= 50:
            color = (251, 191, 36)  # Yellow
        elif percentage >= 20:
            color = (251, 146, 60)  # Orange
        else:
            color = (248, 113, 113)  # Red
        
        # Draw battery outline
        battery_x = 10
        battery_y = 20
        battery_width = 40
        battery_height = 28
        
        # Battery body
        draw.rectangle(
            [battery_x, battery_y, battery_x + battery_width, battery_y + battery_height],
            outline=color,
            width=3
        )
        
        # Battery terminal
        terminal_width = 4
        terminal_height = 12
        terminal_x = battery_x + battery_width
        terminal_y = battery_y + (battery_height - terminal_height) // 2
        draw.rectangle(
            [terminal_x, terminal_y, terminal_x + terminal_width, terminal_y + terminal_height],
            fill=color
        )
        
        # Fill battery based on percentage
        fill_height = int((battery_height - 6) * (percentage / 100))
        fill_y = battery_y + battery_height - 3 - fill_height
        draw.rectangle(
            [battery_x + 3, fill_y, battery_x + battery_width - 3, battery_y + battery_height - 3],
            fill=color
        )
        
        # Draw charging indicator
        if is_charging:
            # Lightning bolt
            bolt_points = [
                (battery_x + battery_width + 10, battery_y + 5),
                (battery_x + battery_width + 15, battery_y + 14),
                (battery_x + battery_width + 12, battery_y + 14),
                (battery_x + battery_width + 17, battery_y + 23),
                (battery_x + battery_width + 10, battery_y + 14),
                (battery_x + battery_width + 13, battery_y + 14),
            ]
            draw.polygon(bolt_points, fill=(255, 215, 0))
        
        return image
    
    def update_icon(self, percentage: int, is_charging: bool = False):
        """Update tray icon with new percentage"""
        self.current_percentage = percentage
        self.is_charging = is_charging
        
        if self.icon:
            new_image = self.create_icon_image(percentage, is_charging)
            self.icon.icon = new_image
            self.icon.title = f"Battery: {percentage}% {'(Charging)' if is_charging else ''}"
    
    def create_menu(self):
        """Create tray menu"""
        return pystray.Menu(
            item(
                lambda: f"Battery: {self.current_percentage}%",
                lambda: None,
                enabled=False
            ),
            item(
                lambda: "Charging" if self.is_charging else "On Battery",
                lambda: None,
                enabled=False
            ),
            pystray.Menu.SEPARATOR,
            item(
                'Set Threshold',
                pystray.Menu(
                    item('80%', lambda: self.set_threshold(80)),
                    item('85%', lambda: self.set_threshold(85)),
                    item('90%', lambda: self.set_threshold(90)),
                    item('95%', lambda: self.set_threshold(95)),
                )
            ),
            item('Snooze Alerts', self.snooze_alerts),
            item('Dismiss Alerts', self.dismiss_alerts),
            pystray.Menu.SEPARATOR,
            item('Open Dashboard', self.open_dashboard),
            item('Settings', self.open_settings),
            pystray.Menu.SEPARATOR,
            item('Exit', self.quit_app)
        )
    
    def set_threshold(self, threshold: int):
        """Set battery threshold"""
        if self.monitor:
            self.monitor._update_threshold(threshold)
    
    def snooze_alerts(self):
        """Snooze alerts for 1 minute"""
        if self.monitor:
            self.monitor._handle_snooze()
    
    def dismiss_alerts(self):
        """Dismiss alerts"""
        if self.monitor:
            self.monitor._handle_dismiss()
    
    def open_dashboard(self):
        """Open web dashboard"""
        import webbrowser
        webbrowser.open('http://127.0.0.1:5000')
    
    def open_settings(self):
        """Open settings page"""
        import webbrowser
        webbrowser.open('http://127.0.0.1:5000/settings')
    
    def quit_app(self):
        """Quit the application"""
        self.running = False
        if self.icon:
            self.icon.stop()
        if self.monitor:
            self.monitor.stop()
        sys.exit(0)
    
    def run(self):
        """Run the tray application"""
        self.running = True
        
        # Create initial icon
        initial_image = self.create_icon_image(0)
        
        # Create tray icon
        self.icon = pystray.Icon(
            "BatteryMonitor",
            initial_image,
            "Battery Monitor",
            menu=self.create_menu()
        )
        
        # Run icon in separate thread
        icon_thread = threading.Thread(target=self.icon.run, daemon=True)
        icon_thread.start()
        
        return icon_thread
    
    def stop(self):
        """Stop the tray application"""
        self.running = False
        if self.icon:
            self.icon.stop()


def start_tray_app(battery_monitor):
    """Start system tray application"""
    try:
        tray = TrayApp(battery_monitor)
        tray.run()
        return tray
    except Exception as e:
        print(f"Error starting tray app: {e}")
        print("Tray functionality requires pystray and Pillow. Install with: pip install pystray Pillow")
        return None
