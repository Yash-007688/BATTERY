import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta
import argparse

import psutil

try:
    import winsound
except ImportError:  # Fallback (non-Windows) – single bell
    winsound = None


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

    def start(self) -> None:
        self._start_time = datetime.now()
        self._start_percent = self._get_battery_percent()
        self._reached_time = None
        self._alerted = False

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
            percent, plugged = self._get_battery()
            now_str = datetime.now().strftime('%H:%M:%S')

            status = "Plugged" if plugged else "On battery"
            line = f"[{now_str}] Battery: {percent:.0f}% | {status} | Threshold: {self.threshold_percent}%"

            if self._reached_time is None and percent >= self.threshold_percent:
                self._reached_time = datetime.now()
                if not self._alerted:
                    self._beep()
                    self._alerted = True
                line += " | Reached threshold!"

            if self._start_time is not None and self._reached_time is not None:
                delta = self._reached_time - self._start_time
                line += f" | Time to reach: {format_timedelta(delta)}"

            print(line)

            # Sleep in small chunks so we can respond to stop quickly
            remaining = self.poll_interval_seconds
            while remaining > 0 and not self._stop_event.is_set():
                time.sleep(min(0.5, remaining))
                remaining -= 0.5

    def _get_battery(self) -> tuple[float, bool]:
        batt = psutil.sensors_battery()
        if batt is None:
            print("Battery info not available on this system.")
            return 0.0, False
        return float(batt.percent), bool(batt.power_plugged)

    def _get_battery_percent(self) -> float:
        percent, _ = self._get_battery()
        return percent

    def _beep(self) -> None:
        try:
            if winsound is not None:
                # Two quick beeps
                winsound.Beep(1000, 500)
                time.sleep(0.1)
                winsound.Beep(1400, 600)
            else:
                # Fallback to terminal bell
                sys.stdout.write('\a')
                sys.stdout.flush()
        except Exception:
            # Ignore sound errors
            pass

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
    threshold = 95
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


def main() -> None:
    default_threshold, default_interval = load_config()

    parser = argparse.ArgumentParser(description="Battery monitor with threshold alert")
    # Flags requested: -f 95% -n 85%
    parser.add_argument("threshold", nargs="?", type=parse_percent_arg, help="threshold percent (e.g. 95 or 95%)")
    parser.add_argument("interval", nargs="?", type=int, help="poll interval seconds (e.g. 30)")
    parser.add_argument("-f", "--from-threshold", dest="from_threshold", type=parse_percent_arg, help="legacy/current threshold value (e.g. 95%)")
    parser.add_argument("-n", "--new-threshold", dest="new_threshold", type=parse_percent_arg, help="new threshold value to use (e.g. 85%)")

    args = parser.parse_args()

    # Determine threshold precedence: new_threshold (-n) > from_threshold (-f) > positional > config
    threshold = (
        args.new_threshold
        if args.new_threshold is not None
        else (
            args.from_threshold
            if args.from_threshold is not None
            else (args.threshold if args.threshold is not None else default_threshold)
        )
    )

    interval = args.interval if args.interval is not None else default_interval

    monitor = BatteryMonitor(threshold, interval)
    monitor.start()


if __name__ == "__main__":
    main()


