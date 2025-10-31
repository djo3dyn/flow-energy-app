#!/usr/bin/env python3
import time
import json
import logging
from pymodbus.client import ModbusSerialClient
from pymodbus.transaction import ModbusRtuFramer
from pymodbus.exceptions import ModbusIOException
from struct import unpack
import serial
import os

# ----------------------------
# Configuration
# ----------------------------
PORT = "/dev/ttyUSB0"
BAUDRATE = 9600
SLAVE_ID = 1
START_ADDR = 66
NUM_REGS = 88
JSON_FILE = "/root/flow-sensor-app/power_data.json"
LOG_FILE = "/var/log/power_meter.log"

# ----- Main Data ------

data = {}

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

REG_MAP = {
    "avg_phase_voltage": (0, 2),
    "avg_line_voltage": (2, 2),
    "a_phase_current": (4, 2),
    "b_phase_current": (6, 2),
    "c_phase_current": (8, 2),
    "total_active_power": (10, 2),
    "total_reactive_power": (12, 2),
    "total_apparent_power": (14, 2),
    "total_power_factor": (16, 2),
    "frequency": (18, 2),
    "total_pos_active_energy": (20, 2),
    "total_neg_active_energy": (22, 2),
    "total_pos_reactive_energy": (24, 2),
    "total_neg_reactive_energy": (26, 2),
}

def decode_float32(registers, index):
    try:
        raw = (registers[index] << 16) + registers[index + 1]
        return unpack('>f', raw.to_bytes(4, 'big'))[0]
    except Exception:
        return None

def check_port_available(port):
    try:
        s = serial.Serial(port)
        s.close()
        return True
    except Exception:
        return False

def get_pm_data() :
    return data

def loop_powermeter():
    """Continuous Modbus polling loop."""
    client = ModbusSerialClient(
        framer=ModbusRtuFramer,
        port=PORT,
        baudrate=BAUDRATE,
        parity='N',
        stopbits=1,
        bytesize=8,
        timeout=2
    )

    logging.info("Starting Power Meter Reader...")

    while True:
        try:
            if not check_port_available(PORT):
                logging.warning("Serial port %s not available", PORT)
                time.sleep(5)
                continue

            if not client.connected:
                client.connect()

            rr = client.read_holding_registers(START_ADDR, NUM_REGS, slave=SLAVE_ID)
            if rr is None or isinstance(rr, ModbusIOException) or rr.isError():
                logging.warning("Modbus read failed.")
                time.sleep(3)
                continue

            regs = rr.registers
            #data = {}

            for name, (idx, size) in REG_MAP.items():
                if size == 2:
                    val = decode_float32(regs, idx)
                else:
                    val = regs[idx]
                data[name] = round(val, 3) if val is not None else None

            with open(JSON_FILE, "w") as f:
                json.dump(data, f, indent=2)
            #logging.info("Updated power data: %s", data)

        except Exception as e:
            logging.error("Loop error: %s", e)
            client.close()
            time.sleep(5)
            client.connect()

        time.sleep(3)
