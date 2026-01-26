"""
Wireless ADB Connection Script
Helps connect your Android phone via wireless debugging
"""
import subprocess
import sys
import re


def check_adb_installed():
    """Check if ADB is installed and accessible"""
    try:
        result = subprocess.run(['adb', 'version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ ADB is installed")
            print(f"  {result.stdout.strip()}")
            return True
        else:
            print("✗ ADB is not working properly")
            return False
    except FileNotFoundError:
        print("✗ ADB not found in PATH")
        print("\nPlease install Android SDK Platform Tools:")
        print("  1. Download from: https://developer.android.com/tools/releases/platform-tools")
        print("  2. Extract and add to system PATH")
        return False
    except Exception as e:
        print(f"✗ Error checking ADB: {e}")
        return False


def get_connected_devices():
    """Get list of currently connected ADB devices"""
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return []
        
        devices = []
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        for line in lines:
            if line.strip() and '\t' in line:
                device_id, status = line.strip().split('\t')
                devices.append((device_id, status))
        return devices
    except Exception as e:
        print(f"Error getting devices: {e}")
        return []


def connect_wireless(ip_address, port):
    """Connect to device via wireless debugging"""
    try:
        print(f"\nConnecting to {ip_address}:{port}...")
        result = subprocess.run(
            ['adb', 'connect', f'{ip_address}:{port}'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if 'connected' in output.lower() or 'already connected' in output.lower():
                print(f"✓ Successfully connected!")
                print(f"  {output}")
                return True
            else:
                print(f"✗ Connection failed: {output}")
                return False
        else:
            print(f"✗ Connection failed: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print("✗ Connection timed out")
        return False
    except Exception as e:
        print(f"✗ Error connecting: {e}")
        return False


def disconnect_wireless(ip_address, port):
    """Disconnect wireless device"""
    try:
        result = subprocess.run(
            ['adb', 'disconnect', f'{ip_address}:{port}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(f"Disconnected from {ip_address}:{port}")
        return True
    except Exception as e:
        print(f"Error disconnecting: {e}")
        return False


def pair_device(ip_address, port, pairing_code):
    """Pair device using pairing code (Android 11+)"""
    try:
        print(f"\nPairing with {ip_address}:{port}...")
        result = subprocess.run(
            ['adb', 'pair', f'{ip_address}:{port}', pairing_code],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if 'successfully' in output.lower():
                print(f"✓ Successfully paired!")
                print(f"  {output}")
                return True
            else:
                print(f"✗ Pairing failed: {output}")
                return False
        else:
            print(f"✗ Pairing failed: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print("✗ Pairing timed out")
        return False
    except Exception as e:
        print(f"✗ Error pairing: {e}")
        return False


def main():
    print("=" * 60)
    print("Wireless ADB Connection Helper")
    print("=" * 60)
    
    # Check ADB installation
    if not check_adb_installed():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Current Connected Devices:")
    print("=" * 60)
    devices = get_connected_devices()
    if devices:
        for device_id, status in devices:
            print(f"  {device_id:<30} {status}")
    else:
        print("  No devices connected")
    
    print("\n" + "=" * 60)
    print("Wireless Debugging Setup Instructions:")
    print("=" * 60)
    print("\nOn your Android phone:")
    print("  1. Go to Settings → Developer Options")
    print("  2. Enable 'Wireless debugging'")
    print("  3. Tap 'Wireless debugging' to open it")
    print("  4. Tap 'Pair device with pairing code'")
    print("  5. Note the IP address, port, and pairing code shown")
    print("\nOR (for older method):")
    print("  1. Enable 'Wireless debugging'")
    print("  2. Note the IP address and port shown")
    print("  3. Make sure phone and computer are on same WiFi network")
    
    print("\n" + "=" * 60)
    print("Connection Options:")
    print("=" * 60)
    print("1. Connect directly (if you have IP:Port)")
    print("2. Pair first, then connect (Android 11+ with pairing code)")
    print("3. Disconnect wireless device")
    print("4. List connected devices")
    print("5. Exit")
    
    while True:
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            ip_port = input("Enter IP address and port (e.g., 192.168.1.100:5555): ").strip()
            if ':' in ip_port:
                ip, port = ip_port.rsplit(':', 1)
                if connect_wireless(ip, port):
                    print("\n✓ Device connected! You can now use it with the battery monitor.")
                    # Verify connection
                    devices = get_connected_devices()
                    print("\nCurrent devices:")
                    for device_id, status in devices:
                        print(f"  {device_id:<30} {status}")
            else:
                print("✗ Invalid format. Use IP:Port (e.g., 192.168.1.100:5555)")
        
        elif choice == '2':
            ip_port = input("Enter pairing IP address and port (e.g., 192.168.1.100:XXXXX): ").strip()
            pairing_code = input("Enter pairing code: ").strip()
            if ':' in ip_port:
                ip, port = ip_port.rsplit(':', 1)
                if pair_device(ip, port, pairing_code):
                    # After pairing, get the connection port (usually different)
                    print("\nAfter pairing, you need to connect using the connection port.")
                    print("Check your phone's Wireless debugging screen for the connection port.")
                    conn_port = input("Enter connection port (e.g., 37XXX): ").strip()
                    if conn_port:
                        connect_wireless(ip, conn_port)
            else:
                print("✗ Invalid format. Use IP:Port (e.g., 192.168.1.100:XXXXX)")
        
        elif choice == '3':
            ip_port = input("Enter IP address and port to disconnect (e.g., 192.168.1.100:5555): ").strip()
            if ':' in ip_port:
                ip, port = ip_port.rsplit(':', 1)
                disconnect_wireless(ip, port)
            else:
                print("✗ Invalid format. Use IP:Port")
        
        elif choice == '4':
            print("\n" + "=" * 60)
            print("Connected Devices:")
            print("=" * 60)
            devices = get_connected_devices()
            if devices:
                for device_id, status in devices:
                    print(f"  {device_id:<30} {status}")
            else:
                print("  No devices connected")
        
        elif choice == '5':
            print("\nGoodbye!")
            break
        
        else:
            print("✗ Invalid choice. Please enter 1-5.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
        sys.exit(0)
