# modem_metrics.py  (RPi side)
# Query RSRP/RSRQ/SINR via AT commands on Quectel 5G HAT
# Requires: pip install pyserial

import re
import time
import subprocess
from serial import Serial
from serial.serialutil import SerialException

AT_PORT = "/dev/ttyUSB2"     # AT command port (adjust if needed)
BAUD = 115200
TIMEOUT = 1.0

# Regex for Quectel responses: +QRSRP: PRX,DRX,RX2,RX3,MODE
_qrsrp_re = re.compile(r"\+QRSRP:\s*(-?\d+),(-?\d+),(-?\d+),(-?\d+),(\w+)")
_qrsrq_re = re.compile(r"\+QRSRQ:\s*(-?\d+),(-?\d+),(-?\d+),(-?\d+),(\w+)")
_qsinr_re = re.compile(r"\+QSINR:\s*(-?\d+),(-?\d+),(-?\d+),(-?\d+),(\w+)")

def _sh(cmd: list[str]) -> str:
    out = subprocess.run(cmd, capture_output=True, text=True)
    return (out.stdout or "").strip()

def stop_modemmanager_if_active():
    """Stop ModemManager only if it's running (prevents port grabs)."""
    state = _sh(["systemctl", "is-active", "ModemManager.service"])
    if state == "active":
        subprocess.run(["sudo", "systemctl", "stop", "ModemManager.service"])
        time.sleep(0.3)  # let it release the device

def port_is_free(dev: str = AT_PORT) -> bool:
    """Return True if no process holds the device."""
    out = _sh(["sudo", "fuser", "-v", dev])
    return dev not in out

def open_at_port(dev: str = AT_PORT, retries: int = 5, sleep_s: float = 0.4) -> Serial:
    """Open the AT serial port and verify with 'AT' -> 'OK'."""
    last_err = None
    for _ in range(retries):
        try:
            ser = Serial(dev, BAUD, timeout=TIMEOUT, exclusive=False)
            # Probe with AT
            ser.reset_input_buffer()
            ser.write(b"AT\r")
            time.sleep(0.15)
            resp = ser.read(128).decode(errors="ignore")
            if "OK" in resp:
                return ser
            ser.close()
        except SerialException as e:
            last_err = e
        time.sleep(sleep_s)
    raise SerialException(f"Could not open/validate AT port {dev}: {last_err}")

def _at_lines(ser: Serial, cmd: str, wait: float = 0.25):
    ser.reset_input_buffer()
    ser.write((cmd + "\r").encode())
    time.sleep(wait)
    lines = []
    while ser.in_waiting:
        line = ser.readline().decode(errors="ignore").strip()
        if line:
            lines.append(line)
    return lines

def _parse_first(pattern: re.Pattern, lines):
    """Parse and return the primary branch (PRX) value."""
    for line in lines:
        m = pattern.search(line)
        if m:
            prx, drx, rx2, rx3, _mode = m.groups()
            return int(prx)
    return None

def get_metrics(ser: Serial) -> dict:
    """Return dict with primary-branch RSRP/RSRQ/SINR."""
    rsrp = _parse_first(_qrsrp_re, _at_lines(ser, "AT+QRSRP"))
    rsrq = _parse_first(_qrsrq_re, _at_lines(ser, "AT+QRSRQ"))
    sinr = _parse_first(_qsinr_re, _at_lines(ser, "AT+QSINR"))
    return {"RSRP": rsrp, "RSRQ": rsrq, "SINR": sinr}

def get_metrics_once() -> dict:
    """One-shot helper that opens/closes the port internally."""
    stop_modemmanager_if_active()
    ser = open_at_port()
    try:
        return get_metrics(ser)
    finally:
        ser.close()

if __name__ == "__main__":
    print(get_metrics_once())
