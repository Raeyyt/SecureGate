"""
SecureGate - Python Log Collector (Stage 10)

Reads JSON event lines from the Arduino over serial and:
  1. Prints each event to the console as it arrives
  2. Appends it to a local log file (securegate_log.jsonl)

Each line in the log file is one JSON object - this format is called
"JSON Lines" (.jsonl), and is easy to load later for a dashboard.

Usage:
    python securegate_collector.py
"""

import serial
import json
from datetime import datetime

# ---- Configuration ----
COM_PORT = "COM3"      # Change this to match your Arduino's port
BAUD_RATE = 9600
LOG_FILE = "securegate_log.jsonl"


def main():
    print(f"Connecting to {COM_PORT} at {BAUD_RATE} baud...")

    try:
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
    except serial.SerialException as e:
        print(f"Could not open {COM_PORT}: {e}")
        print("Check that the Arduino IDE's Serial Monitor is closed,")
        print("and that COM_PORT above matches your Arduino's port.")
        return

    print(f"Connected. Logging events to {LOG_FILE}")
    print("Press Ctrl+C to stop.\n")

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as log_file:
            while True:
                raw_line = ser.readline().decode("utf-8", errors="ignore").strip()

                if not raw_line:
                    continue

                try:
                    event = json.loads(raw_line)
                except json.JSONDecodeError:
                    # Not a JSON line (could be a boot message) - skip it
                    continue

                # Print a readable summary to the console
                print(f"[{event.get('timestamp')}] "
                      f"{event.get('event')} - {event.get('detail')}"
                      + (f" (UID: {event.get('uid')})" if "uid" in event else ""))

                # Save the raw JSON line to the log file
                log_file.write(raw_line + "\n")
                log_file.flush()

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        ser.close()
        print("Serial connection closed.")


if __name__ == "__main__":
    main()
