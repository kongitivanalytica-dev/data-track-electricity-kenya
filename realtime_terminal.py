import json
import time
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "live" / "simulation.csv"
LOG_PATH = ROOT / "logs" / "scenario-terminal.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def classify(row):
    if row["unmet_mw"] > 1:
        return "SUPPLY GAP", f"Unmet demand is {row['unmet_mw']:.1f} MW."
    if row["soc_mwh"] < 300:
        return "LOW BATTERY RESERVE", f"Battery state is {row['soc_mwh']:.1f} MWh."
    if row["battery_action"] == "CHARGING":
        return "RENEWABLE SURPLUS / CHARGING", f"Battery charging at {row['charge_mw']:.1f} MW."
    if row["battery_action"] == "DISCHARGING":
        return "PEAK SUPPORT / DISCHARGING", f"Battery discharging at {row['discharge_mw']:.1f} MW."
    if row["demand_mw"] > 3000:
        return "HIGH-DEMAND PERIOD", f"Demand is {row['demand_mw']:.1f} MW."
    return "NORMAL BALANCE", f"Supply balance is normal at {row['demand_mw']:.1f} MW demand."


def main():
    last_signature = None
    with LOG_PATH.open("w", encoding="utf-8") as log:
        while True:
            if CSV_PATH.exists():
                frame = pd.read_csv(CSV_PATH)
                if not frame.empty:
                    latest = str(frame.iloc[-1]["timestamp"])
                    if last_signature is None or latest < last_signature:
                        new_rows = frame
                    else:
                        new_rows = frame[frame["timestamp"].astype(str) > last_signature]
                    for _, row in new_rows.iterrows():
                        last_signature = str(row["timestamp"])
                        row = row.to_dict()
                        scenario, explanation = classify(row)
                        line = (
                            f"{row['timestamp']} | demand {row['demand_mw']:.1f} MW "
                            f"| RF forecast {row['random_forest_forecast_mw']:.1f} MW "
                            f"| SOC {row['soc_mwh']:.1f} MWh | {scenario} | {explanation}"
                        )
                        print(line, flush=True)
                        log.write(line + "\n")
                        log.flush()
            time.sleep(1)


if __name__ == "__main__":
    main()
