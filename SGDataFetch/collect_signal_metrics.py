# collect_signal_metrics.py  (RPi side)
# Save signal metrics locally (no network send)
# CSV headers: Exp_ID, Sample_No, Timestamp, RSRP, RSRQ, SINR

import csv
import time
from serial.serialutil import SerialException
from modem_metrics import (
    stop_modemmanager_if_active,
    port_is_free,
    open_at_port,
    get_metrics,
)

# ---- User settings ----
EXP_ID = "EXP_001"         # change per experiment
SAMPLES = 10               # number of readings
INTERVAL_S = 0.5           # seconds between readings
CSV_FILE = f"signal_metrics_{EXP_ID}.csv"
# -----------------------

def main():
    # Free the port if ModemManager holds it
    stop_modemmanager_if_active()
    if not port_is_free():
        print("Warning: AT port appears busy. Close minicom or other tools if open.")

    with open(CSV_FILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Exp_ID", "Sample_No", "Timestamp", "RSRP", "RSRQ", "SINR"])

        print(f"Collecting {SAMPLES} signal samples... (saving to {CSV_FILE})")
        ser = open_at_port()   # open once, reuse
        try:
            for i in range(1, SAMPLES + 1):
                ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                try:
                    m = get_metrics(ser)
                except SerialException as e:
                    print("Serial error:", e)
                    m = {"RSRP": None, "RSRQ": None, "SINR": None}

                w.writerow([EXP_ID, i, ts, m["RSRP"], m["RSRQ"], m["SINR"]])
                f.flush()
                print(f"[{ts}] RSRP={m['RSRP']}  RSRQ={m['RSRQ']}  SINR={m['SINR']}")
                time.sleep(INTERVAL_S)
        finally:
            ser.close()

    print(f"Data collection complete. Saved to {CSV_FILE}")

if __name__ == "__main__":
    main()
