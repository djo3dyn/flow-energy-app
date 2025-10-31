#!/usr/bin/env python3
import json
import time
import logging
import threading
import paho.mqtt.client as mqtt

# -------------------------------
# Configuration
# -------------------------------
MQTT_BROKER = "broker.hivemq.com"        # Change to your broker IP
MQTT_PORT = 1883
MQTT_TOPIC = "sensor/flow_energy/data"
MQTT_CLIENT_ID = "flow_energy_publisher"
MQTT_KEEPALIVE = 60

# -------------------------------
# Logging setup
# -------------------------------
LOG_FILE = "/var/log/flow_energy_mqtt.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# -------------------------------
# MQTT setup
# -------------------------------
client = mqtt.Client(MQTT_CLIENT_ID, clean_session=True)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to MQTT broker")
    else:
        logging.error(f"Failed to connect MQTT, code={rc}")

def on_disconnect(client, userdata, rc):
    logging.warning(f"MQTT disconnected with code={rc}, retrying...")
    reconnect_loop()

client.on_connect = on_connect
client.on_disconnect = on_disconnect

# -------------------------------
# Connect and auto-reconnect loop
# -------------------------------
def connect_mqtt():
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            client.loop_start()
            logging.info("MQTT connected")
            return
        except Exception as e:
            logging.error(f"MQTT connect error: {e}")
            time.sleep(5)

def reconnect_loop():
    """Attempt reconnect in background if disconnected."""
    def run():
        while not client.is_connected():
            try:
                client.reconnect()
                time.sleep(2)
            except Exception:
                time.sleep(5)
    threading.Thread(target=run, daemon=True).start()

# -------------------------------
# Publish helper
# -------------------------------
def publish_data(flow_data, pm_data):
    """
    flow_data: dict of flow info (freq, flow, total)
    pm_data: dict of power meter info
    """
    try:
        payload = {
            "flow": flow_data,
            "power": pm_data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        msg = json.dumps(payload)
        client.publish(MQTT_TOPIC, msg, qos=1, retain=True)
        logging.info(f"Published MQTT to {MQTT_TOPIC}")
    except Exception as e:
        logging.error(f"Publish error: {e}")
