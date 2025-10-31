
# Flow & Power Meter Integration App

## 📘 Overview
This project combines **flow meter** and **power meter** readings on an Orange Pi (or similar SBC), with data accessible via HTTP and MQTT.

It includes:
- Flow measurement via GPIO interrupt counting.
- Power meter data via Modbus RTU.
- REST API endpoints for live data.
- MQTT publishing to a configurable broker.
- Optional Nextion HMI display integration.

---

## ⚙️ Features
- **HTTP API**
  - `GET /api/flow_data` → Returns flow metrics (L/min, total liters).
  - `GET /api/pm_data` → Returns power meter metrics (voltages, power, energy).
- **MQTT Publishing**
  - All sensor data published under one topic.
  - Example: `home/sensors/flow_energy`.
- **Data Persistence**
  - Flow total stored locally in JSON.
- **Nextion Display (optional)**
  - Updates text fields for flow, frequency, power, and energy.
- **Systemd Service**
  - Runs automatically at boot.

---

## 🧩 Project Structure
```
/root/flow-sensor-app/
├── flow-server.py
├── power-meter-server.py
├── main-app.py
├── mqtt_publish.py
├── flow-energy-app.service
├── requirements.txt
├── README.md
└── logs/
```

---

## 🧰 Requirements

### Python Packages
Install system-wide (not in venv):
```bash
apt update
apt install -y python3 python3-pip python3-serial wiringpi
pip3 install flask pymodbus paho-mqtt
```

### Hardware
- Orange Pi / Raspberry Pi with GPIO
- Flow meter with pulse output
- Modbus power meter (RS-485 to USB converter)
- (Optional) Nextion display on serial `/dev/ttyS5`

---

## 🚀 Running the App

### Manual Run (for testing)
```bash
cd /root/flow-sensor-app
python3 main-app.py
```

### As a Service
Copy the service file and enable:
```bash
cp flow-energy-app.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable flow-energy-app
systemctl start flow-energy-app
```

Check status:
```bash
systemctl status flow-energy-app
```

---

## 🌐 HTTP Endpoints
| Endpoint | Method | Description |
|-----------|---------|-------------|
| `/api/flow_data` | GET | Get live flow data |
| `/api/pm_data` | GET | Get power meter data |
| `/status` | GET | Legacy endpoint for flow meter only |
| `/metrics` | PUT | Update power/energy metrics on flow server |

Example:
```bash
curl http://localhost:5010/api/flow_data
```

---

## 🔗 MQTT Example
Broker: `broker.hivemq.com` (public test broker)  
Topic: `home/sensors/flow_energy`

Example publish payload:
```json
{
  "flow": {
    "frequency_hz": 4.83,
    "flow_lpm": 1.01,
    "total_liters": 123.456
  },
  "power": {
    "total_active_power": 0.5,
    "total_reactive_power": 0.1,
    "total_pos_active_energy": 123.45
  }
}
```

---

## 🧾 License
MIT License © 2025 Judin H.

---

## 🧠 Notes
- Adjust serial ports and pin numbers in the `.py` files.
- Logs stored in `/var/log/flowmeter.log` and `/var/log/power_meter.log`.
- Modify `main-app.py` to change MQTT topic or broker.
