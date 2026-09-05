# Setup Guide

## Hardware Setup

1. **Assemble the breadboard** according to the wiring diagram in `wiring.md`. All components should be connected before powering anything on.

2. **Upload the Arduino sketch:**
   - Open `arduino/securegate/SecureGate.ino` in the Arduino IDE
   - Select **Board: Arduino UNO** and your **COM port** from Tools menu
   - Click **Upload**
   - Confirm the sketch compiles and uploads successfully (no errors in the output console)

3. **Set the RTC time (one-time):**
   - Upload `arduino/SecureGate_RTC_SetTime.ino` once to set the DS1307 module's clock to the current time
   - This only needs to be done once; the RTC keeps time even after power-off

4. **Verify hardware is working:**
   - Open Serial Monitor (9600 baud)
   - You should see `SYSTEM_START` logged
   - Scan your RFID card — you should see `RFID_AUTH_SUCCESS` or `RFID_AUTH_FAILURE`
   - Try entering the PIN on the keypad

## Software Setup (PC Side)

### Prerequisites
- Python 3.7 or later
- pip (Python package manager)

### Install dependencies

```bash
pip install pyserial flask
```

### Configure the collector

Edit `python/log_collector/securegate_collector.py`:
- Change `COM_PORT = "COM3"` to match your Arduino's port (check Device Manager or Arduino IDE)
- Everything else is pre-configured

### Run the system

**Terminal 1 — Log collector:**
```bash
cd path/to/python/log_collector
python securegate_collector.py
```

You should see: `Connected. Logging events to securegate_log.jsonl`

**Terminal 2 — Dashboard (in a new terminal, same folder):**
```bash
cd path/to/python/dashboard
python securegate_dashboard.py
```

You should see: `Starting SecureGate dashboard at http://127.0.0.1:5000`

Open your browser to `http://127.0.0.1:5000` and you should see the live dashboard.

## Testing

Once both scripts are running:
1. Scan your authorized card
2. Enter the correct PIN (default: "1234")
3. You should see `ACCESS_GRANTED` logged and the relay click
4. Try entering a wrong PIN three times to trigger brute-force lockout

See `testing.md` for detailed test cases.
