import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import Workbook


class ReportingAgent:
    def __init__(self, output_dir="output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_excel(self, simulation, summary, metrics, owid, data_source):
        path = self.output_dir / "kenya_energy_results.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            simulation.to_excel(writer, sheet_name="Simulation rows", index=False)
            pd.DataFrame([summary]).to_excel(writer, sheet_name="Summary", index=False)
            pd.DataFrame({
                "Model": ["Linear Regression", "Random Forest"],
                "MAE": [metrics["linear"]["MAE"], metrics["random_forest"]["MAE"]],
                "RMSE": [metrics["linear"]["RMSE"], metrics["random_forest"]["RMSE"]],
            }).to_excel(writer, sheet_name="Model metrics", index=False)
            owid.head(500).to_excel(writer, sheet_name="Annual OWID data", index=False)
        return path

    def save_sqlite(self, simulation, summary, metrics, data_source):
        path = self.output_dir / "kenya_energy_simulation.sqlite"
        connection = sqlite3.connect(path)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS simulation_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                data_source TEXT,
                summary_json TEXT,
                model_metrics_json TEXT
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS simulation_readings (
                reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                timestamp TEXT,
                demand_mw REAL,
                random_forest_forecast_mw REAL,
                linear_forecast_mw REAL,
                geothermal_mw REAL,
                hydro_mw REAL,
                wind_mw REAL,
                solar_mw REAL,
                battery_action TEXT,
                soc_mwh REAL,
                unmet_mw REAL,
                FOREIGN KEY(run_id) REFERENCES simulation_runs(run_id)
            )
        """)
        import json
        cursor = connection.execute(
            "INSERT INTO simulation_runs(created_at,data_source,summary_json,model_metrics_json) VALUES(?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), data_source, json.dumps(summary),
             json.dumps(metrics)),
        )
        run_id = cursor.lastrowid
        records = []
        for row in simulation.to_dict("records"):
            records.append((
                run_id, str(row["timestamp"]), row["demand_mw"],
                row["random_forest_forecast_mw"], row["linear_forecast_mw"],
                row["geothermal_mw"], row["hydro_mw"], row["wind_mw"], row["solar_mw"],
                row["battery_action"], row["soc_mwh"], row["unmet_mw"],
            ))
        connection.executemany("""
            INSERT INTO simulation_readings(
                run_id,timestamp,demand_mw,random_forest_forecast_mw,linear_forecast_mw,
                geothermal_mw,hydro_mw,wind_mw,solar_mw,battery_action,soc_mwh,unmet_mw
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, records)
        connection.commit()
        connection.close()
        return path
