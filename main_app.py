#!/usr/bin/env python3
import threading
import json
import time
import logging
from flask import Flask, jsonify
from flow_server import start_flow_server, update_metrics_from_pm , get_flow_data
from power_meter_server import loop_powermeter , get_pm_data
from mqtt_publisher import connect_mqtt, publish_data
#import serial


LOG_FILE = "/var/log/main_app.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")

PM_JSON = "/root/flow-sensor-app/power_data.json"

app = Flask(__name__)

start_flow_server()  # from flow_server

# -------------------------------
# HTTP API endpoint for power meter data
# -------------------------------
@app.route("/api/pm_data", methods=["GET"])
def read_pm_data():
    try:
        with open(PM_JSON, "r") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# HTTP API endpoint for flow meter data
# -------------------------------
@app.route("/api/flow_data", methods=["GET"])
def api_flow_data():
    return jsonify(get_flow_data())

# -------------------------------
# Power meter polling thread
# -------------------------------
def pm_thread():
    """Read Modbus data and forward power/energy to flow server."""
    while True:
        try:
            with open(PM_JSON, "r") as f:
                data = json.load(f)
                pw = data.get("total_active_power", 0.0)
                en = data.get("total_pos_active_energy", 0.0)
                update_metrics_from_pm(pw, en)
        except Exception:
            pass
        time.sleep(2)


# -------------------------------
# Nextion HMI
# -------------------------------
"""
# Nextion command terminator
END_COMMAND = b'\xFF\xFF\xFF'

ser = serial.Serial(
    port='/dev/ttyS5',
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

def nextion_send_command(cmd_str):
    #Sends a command to the Nextion display
    ser.write(command.encode('utf-8') + END_COMMAND)

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
        
"""

# -------------------------------
# Initialize MQTT
# -------------------------------
connect_mqtt()

def mqtt_thread():
    while True:
        pm_info = get_pm_data()
        flow_info = get_flow_data()

        publish_data(flow_info, pm_info)
        #print(flow_info);
        #print(pm_info);
        
        time.sleep(5)

threading.Thread(target=loop_powermeter, daemon=True).start()
threading.Thread(target=pm_thread, daemon=True).start()
threading.Thread(target=mqtt_thread, daemon=True).start()



if __name__ == "__main__":
    logging.info("Starting integrated main-app...")
    app.run(host="0.0.0.0", port=5012, threaded=True)
