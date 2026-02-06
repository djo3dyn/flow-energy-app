#!/usr/bin/env python3
"""
Flow meter + Nextion + HTTP API
- GPIO interrupt counting using wiringpi (external pull-up, falling edge)
- Saves total liters to JSON file
- Sends updates to Nextion HMI via /dev/ttyS5
"""

import wiringpi
import time
import os
import json
import threading
import sys
import traceback
import logging

# -------------------------------
# Logging setup
# -------------------------------
LOG_FILE = "/var/log/flowmeter.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

def log_error(e):
    logging.error(f"{type(e).__name__}: {e}")
    traceback.print_exc(file=sys.stdout)

# -------------------------------
# Configuration
# -------------------------------
FLOW_PIN = 2
MEASURE_INTERVAL = 1.0
DEBOUNCE_US = 200
TOTAL_FILE = "/root/flow-sensor-app/flow_total.json"
SERIAL_PORT = "/dev/ttyS5"
SERIAL_BAUD = 9600

NEXTION_FIELDS = {
    "freq": "txtFreq",
    "flow": "txtFlow",
    "total": "txtTotal",
    "power": "txtPower",
    "energy": "txtEnergy"
}

# -------------------------------
# Shared state
# -------------------------------
state_lock = threading.Lock()
pulse_count = 0
last_pulse = 0
total_liters = 0.0
frequency = 0.0
flow_lpm = 0.0
power_kw = 0.0
energy_kwh = 0.0
ser = -1

# -------------------------------
# Persistence
# -------------------------------
def load_total():
    global total_liters
    try:
        if os.path.exists(TOTAL_FILE):
            with open(TOTAL_FILE, "r") as f:
                total_liters = float(json.load(f).get("total_liters", 0.0))
        else:
            total_liters = 0.0
    except Exception as e:
        logging.error("Failed to load total: %s", e)
        total_liters = 0.0

def save_total():
    try:
        tmp = TOTAL_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"total_liters": total_liters}, f)
        os.replace(tmp, TOTAL_FILE)
    except Exception as e:
        logging.error("Error saving total: %s", e)

# -------------------------------
# Nextion helper
# -------------------------------
def nextion_send_command(cmd_str):
    global ser
    if ser < 0:
        return
    try:
        wiringpi.serialPuts(ser, cmd_str)
        for _ in range(3):
            wiringpi.serialPutchar(ser, 0xFF)
    except Exception as e:
        logging.error("Nextion send error: %s", e)

def nextion_update_all():
    with state_lock:
        f = frequency
        fl = flow_lpm
        tot = total_liters
        pw = power_kw
        en = energy_kwh

    try:
        nextion_send_command(f'{NEXTION_FIELDS["freq"]}.txt="{f:.2f} Hz"')
        nextion_send_command(f'{NEXTION_FIELDS["flow"]}.txt="{fl:.2f} L/min"')
        nextion_send_command(f'{NEXTION_FIELDS["total"]}.txt="{tot:.3f} L"')
        nextion_send_command(f'{NEXTION_FIELDS["power"]}.txt="{pw:.3f} kW"')
        nextion_send_command(f'{NEXTION_FIELDS["energy"]}.txt="{en:.3f} kWh"')
    except Exception as e:
        logging.error("Error updating Nextion: %s", e)

# -------------------------------
# GPIO interrupt handler
# -------------------------------
def pulse_detected():
    global pulse_count
    with state_lock:
        pulse_count += 1
    print(".", end="")

# -------------------------------
# Measurement loop
# -------------------------------
def measurement_loop():
    global pulse_count, frequency, flow_lpm, total_liters
    load_total()
    next_save = time.time() + 10

    while True:
        with state_lock:
            pulse_count = 0
        start = time.time()
        time.sleep(MEASURE_INTERVAL)
        elapsed = time.time() - start

        with state_lock:
            count = pulse_count
        f = count / elapsed if elapsed > 0 else 0.0
        flow = f / 4.8
        flow_lps = flow / 60.0

        with state_lock:
            frequency = f
            flow_lpm = flow
            total_liters += flow_lps * elapsed

        if time.time() >= next_save:
            with state_lock:
                save_total()
            next_save = time.time() + 10

        nextion_update_all()
        
# -------------------------------
# Get main flow data
# -------------------------------

def get_flow_data():
    return {
            #"frequency_hz": round(frequency, 4),
            "flow_lpm": round(flow_lpm, 4),
            "total_liters": round(total_liters, 6),
            #"power_kw": round(power_kw, 6),
            #"energy_kwh": round(energy_kwh, 6)
        }

# -------------------------------
# External update (called by main-app)
# -------------------------------
def update_metrics_from_pm(pw, en):
    """Called from main-app when new power meter data arrives."""
    global power_kw, energy_kwh
    with state_lock:
        power_kw = pw
        energy_kwh = en
    nextion_update_all()

# -------------------------------
# Hardware setup
# -------------------------------
def open_serial():
    global ser
    while True:
        try:
            ser = wiringpi.serialOpen(SERIAL_PORT, SERIAL_BAUD)
            if ser >= 0:
                logging.info(f"Serial opened {SERIAL_PORT} @ {SERIAL_BAUD}")
                return
        except Exception as e:
            log_error(e)
        logging.warning("Serial open failed, retrying in 5 seconds...")
        time.sleep(5)

def setup_hardware():
    wiringpi.wiringPiSetup()
    wiringpi.pinMode(FLOW_PIN, wiringpi.INPUT)
    wiringpi.pullUpDnControl(FLOW_PIN, wiringpi.PUD_UP)
    wiringpi.wiringPiISR(FLOW_PIN, wiringpi.INT_EDGE_FALLING, pulse_detected)
    open_serial()

def init_pin_thread():
    while True:
        time.sleep(600)
        wiringpi.pullUpDnControl(FLOW_PIN, wiringpi.PUD_UP)
threading.Thread(target=init_pin_thread, daemon=True).start()

# -------------------------------
# Unified startup
# -------------------------------
def start_flow_server():
    setup_hardware()
    threading.Thread(target=measurement_loop, daemon=True).start()

# -------------------------------
# Standalone run
# -------------------------------
if __name__ == "__main__":
    app = start_flow_server()
    app.run(host="0.0.0.0", port=5012, threaded=True)
