import json
import os
import signal
import time
from datetime import timedelta
from pathlib import Path

import pandas as pd

from agents import DataAgent, ForecastAgent, GenerationAgent, OptimizationAgent, ReportingAgent


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
LIVE = ROOT / "live"
LOG = ROOT / "logs" / "realtime-simulation.log"
for directory in (OUTPUT, LIVE, LOG.parent):
    directory.mkdir(parents=True, exist_ok=True)


def atomic_csv(frame, path):
    temporary = path.with_suffix(".tmp")
    frame.to_csv(temporary, index=False)
    os.replace(temporary, path)


def atomic_json(payload, path):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def main():
    data_agent = DataAgent()
    forecast_agent = ForecastAgent()
    generation_agent = GenerationAgent()
    optimization_agent = OptimizationAgent()
    ReportingAgent(str(OUTPUT))

    _, data_source = data_agent.load_owid_kenya()
    hourly = data_agent.generate_hourly()
    forecast = forecast_agent.fit(hourly)
    available = generation_agent.calculate(hourly)
    payload = {
        "data_source": data_source,
        "linear_metrics": forecast["linear_metrics"],
        "random_forest_metrics": forecast["random_forest_metrics"],
        "feature_importance": forecast["feature_importance"],
    }
    atomic_json(payload, LIVE / "simulation.json")
    LOG.write_text("Live simulation started.\n", encoding="utf-8")

    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    rows = []
    step = 0
    columns = [
        "timestamp", "demand_mw", "linear_forecast_mw", "random_forest_forecast_mw",
        "temperature_c", "irradiance_w_m2", "geothermal_available_mw",
        "hydro_available_mw", "wind_available_mw", "solar_available_mw",
        "geothermal_mw", "hydro_mw", "wind_mw", "solar_mw",
        "battery_action", "charge_mw", "discharge_mw", "soc_mwh", "unmet_mw",
    ]
    atomic_csv(pd.DataFrame(columns=columns), LIVE / "simulation.csv")

    while running:
        index = step % len(hourly)
        cycle = step // len(hourly)
        source_row = hourly.iloc[index]
        dispatch = optimization_agent.dispatch(
            float(source_row["demand_mw"]),
            (
                available["geothermal"][index],
                available["hydro"][index],
                available["wind"][index],
                available["solar"][index],
            ),
        )
        rows.append({
            "timestamp": source_row["timestamp"] + timedelta(hours=cycle * len(hourly)),
            "demand_mw": float(source_row["demand_mw"]),
            "linear_forecast_mw": float(forecast["linear"][index]),
            "random_forest_forecast_mw": float(forecast["random_forest"][index]),
            "temperature_c": float(source_row["temperature_c"]),
            "irradiance_w_m2": float(source_row["irradiance_w_m2"]),
            "geothermal_available_mw": float(available["geothermal"][index]),
            "hydro_available_mw": float(available["hydro"][index]),
            "wind_available_mw": float(available["wind"][index]),
            "solar_available_mw": float(available["solar"][index]),
            "geothermal_mw": dispatch["geothermal"],
            "hydro_mw": dispatch["hydro"],
            "wind_mw": dispatch["wind"],
            "solar_mw": dispatch["solar"],
            "battery_action": dispatch["action"],
            "charge_mw": dispatch["charge"],
            "discharge_mw": dispatch["discharge"],
            "soc_mwh": dispatch["soc"],
            "unmet_mw": dispatch["unmet"],
        })
        rows = rows[-len(hourly):]
        simulation = pd.DataFrame(rows, columns=columns)
        summary = {
            "rows": len(simulation),
            "mean_demand_mw": float(simulation["demand_mw"].mean()),
            "peak_demand_mw": float(simulation["demand_mw"].max()),
            "mean_unmet_mw": float(simulation["unmet_mw"].mean()),
            "total_unserved_mwh": float(simulation["unmet_mw"].sum()),
            "final_soc_mwh": float(simulation["soc_mwh"].iloc[-1]),
        }
        payload["summary"] = summary
        atomic_json(payload, LIVE / "simulation.json")
        atomic_csv(simulation, LIVE / "simulation.csv")
        print(
            f"{simulation.iloc[-1]['timestamp']} | "
            f"demand {source_row['demand_mw']:.1f} MW "
            f"| SOC {dispatch['soc']:.1f} MWh",
            flush=True,
        )
        step += 1
        for _ in range(10):
            if not running:
                break
            time.sleep(0.1)


if __name__ == "__main__":
    main()
