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
        self._alert_active: bool = False
        self._snooze_until: datetime | None = None
        self._dismissed_until_below: bool = False
        self._last_below_threshold: bool = True

        # Per-minute change tracking (percent-based; voltage not available via psutil)
        self._minute_anchor_time: datetime | None = None
        self._minute_anchor_percent: float | None = None
        self._per_minute_diffs: list[float] = []

    def start(self) -> None:
        self._start_time = datetime.now()
        self._start_percent = self._get_battery_percent()
        self._reached_time = None
        self._alerted = False

        # Initialize 1-minute tracking window
        self._minute_anchor_time = self._start_time
        self._minute_anchor_percent = self._start_percent

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
            elif user_input.lower() == "snooze":
                self._handle_snooze()
            elif user_input.lower() == "dismiss":
                self._handle_dismiss()
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

            # Reset dismissal when battery drops below threshold
            current_below = percent < self.threshold_percent
            if current_below and not self._last_below_threshold:
                self._dismissed_until_below = False
                self._alerted = False
                self._alert_active = False
                self._reached_time = None
            self._last_below_threshold = current_below

            # If snoozed, skip alert until snooze ends
            if self._snooze_until is not None and datetime.now() < self._snooze_until:
                remaining = self._snooze_until - datetime.now()
                line += f" | Snoozed {format_timedelta(remaining)}"
            else:
                if self._snooze_until is not None and datetime.now() >= self._snooze_until:
                    # Snooze expired
                    self._snooze_until = None

                # Only trigger alert when plugged and at/above threshold and not dismissed
                if plugged and not self._dismissed_until_below and percent >= self.threshold_percent:
                    if self._reached_time is None:
                        self._reached_time = datetime.now()
                    if not self._alert_active:
                        self._trigger_alert()
                        self._alert_active = True
                        self._alerted = True
                    line += " | Reached threshold! (type 'snooze' or 'dismiss')"

            # Every full minute since last anchor, compute percent difference and record
            now_dt = datetime.now()
            if self._minute_anchor_time is None:
                self._minute_anchor_time = now_dt
                self._minute_anchor_percent = percent
            else:
                elapsed = (now_dt - self._minute_anchor_time).total_seconds()
                # Handle multiple minutes elapsed in case of longer polling intervals/sleeps
                while elapsed >= 60.0 and self._minute_anchor_percent is not None:
                    diff = percent - self._minute_anchor_percent
                    self._per_minute_diffs.append(diff)
                    # Report the just-computed 1-minute change
                    print(f"[{now_str}] Δ1m: {diff:+.1f}%")
                    # Advance anchor by 60s and set anchor percent to current percent
                    self._minute_anchor_time = self._minute_anchor_time + timedelta(seconds=60)
                    self._minute_anchor_percent = percent
                    elapsed -= 60.0

            if self._start_time is not None and self._reached_time is not None:
                delta = self._reached_time - self._start_time
                line += f" | Time to reach: {format_timedelta(delta)}"
                # When showing total charging time, also include min/max per-minute differences
                if self._per_minute_diffs:
                    min_diff = min(self._per_minute_diffs)
                    max_diff = max(self._per_minute_diffs)
                    line += f" | Δ1m min: {min_diff:+.1f}% max: {max_diff:+.1f}%"

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
                winsound.Beep(1000, 300)
            else:
                # Fallback to terminal bell
                sys.stdout.write('\a')
                sys.stdout.flush()
        except Exception:
            # Ignore sound errors
            pass

    def _beep_times(self, times: int, freq1: int = 1000, freq2: int = 1400) -> None:
        for i in range(times):
            try:
                if winsound is not None:
                    winsound.Beep(freq1 if i % 2 == 0 else freq2, 250)
                else:
                    sys.stdout.write('\a')
                    sys.stdout.flush()
                time.sleep(0.07)
            except Exception:
                pass

    def _trigger_alert(self) -> None:
        # 5 beeps, then present options
        self._beep_times(5)
        print("Battery reached threshold. Type 'snooze' to mute for 1 minute or 'dismiss' (requires unplugging charger).")

    def _handle_snooze(self) -> None:
        self._snooze_until = datetime.now() + timedelta(minutes=1)
        self._alert_active = False
        print(f"Snoozed until {self._snooze_until.strftime('%H:%M:%S')}")

    def _handle_dismiss(self) -> None:
        percent, plugged = self._get_battery()
        if plugged:
            print("Cannot dismiss while charger is plugged in. Unplug the charger, then type 'dismiss' again.")
            return
        self._dismissed_until_below = True
        self._alert_active = False
        print("Dismissed. Alerts will resume after battery drops below threshold and rises again.")

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
    threshold = 80
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
    parser.add_argument("-f", "--current-threshold", dest="current_threshold", type=parse_percent_arg, help="current threshold value (e.g. 95%)")
    parser.add_argument("-n", "--new-threshold", dest="new_threshold", type=parse_percent_arg, help="new threshold value to use (e.g. 85%)")

    args = parser.parse_args()

    # Determine threshold precedence: new_threshold (-n) > current_threshold (-f) > positional > config
    threshold = (
        args.new_threshold
        if args.new_threshold is not None
        else (
            args.current_threshold
            if args.current_threshold is not None
            else (args.threshold if args.threshold is not None else default_threshold)
        )
    )

    interval = args.interval if args.interval is not None else default_interval

    monitor = BatteryMonitor(threshold, interval)
    monitor.start()


if __name__ == "__main__":
    main()


