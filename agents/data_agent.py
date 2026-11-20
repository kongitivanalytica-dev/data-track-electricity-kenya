import io
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests


OWID_URL = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"


class DataAgent:
    def load_owid_kenya(self):
        try:
            response = requests.get(OWID_URL, timeout=12)
            response.raise_for_status()
            data = pd.read_csv(io.BytesIO(response.content))
            kenya = data[data["country"].eq("Kenya")].copy()
            if kenya.empty:
                raise ValueError("No Kenya rows returned")
            return kenya, "owid_online"
        except Exception:
            years = np.arange(1990, 2024)
            fallback = pd.DataFrame({
                "country": "Kenya",
                "year": years,
                "electricity_demand": 4000 + 180 * (years - 1990),
            })
            return fallback, "synthetic_fallback"

    def generate_hourly(self, hours=336, seed=42, demand_scale=1.0):
        rng = np.random.default_rng(seed)
        start = datetime(2025, 1, 1)
        time = [start + timedelta(hours=i) for i in range(hours)]
        hour = np.arange(hours)
        hour_of_day = hour % 24
        day_of_year = (hour // 24) % 365 + 1
        temperature = 21 + 4 * np.sin(2 * np.pi * (hour_of_day - 8) / 24) + 1.8 * np.sin(
            2 * np.pi * day_of_year / 365
        )
        irradiance = np.clip(
            850 * np.sin(np.pi * (hour_of_day - 6) / 12), 0, 850
        )
        demand = (
            1800
            + 260 * np.sin(2 * np.pi * hour_of_day / 24)
            + 180 * np.sin(2 * np.pi * day_of_year / 365)
            + 120 * np.exp(-((hour_of_day - 19) / 2.5) ** 2)
            + 18 * (temperature - 21)
            + rng.normal(0, 55, hours)
        ) * demand_scale
        solar = np.clip(irradiance * (0.0017 + 0.00002 * rng.normal(0, 1, hours)), 0, 2200)
        wind = np.clip(
            900 + 430 * np.sin(2 * np.pi * hour / 58) + rng.normal(0, 110, hours),
            0,
            1700,
        )
        hydro = np.clip(
            1500 + 350 * np.sin(2 * np.pi * day_of_year / 365 - 1.2),
            400,
            2200,
        )
        geothermal = np.clip(
            950 + 45 * np.sin(2 * np.pi * hour / 96) + rng.normal(0, 20, hours),
            700,
            1100,
        )
        return pd.DataFrame({
            "timestamp": time,
            "demand_mw": demand,
            "temperature_c": temperature,
            "irradiance_w_m2": irradiance,
            "solar_mw": solar,
            "wind_mw": wind,
            "hydro_mw": hydro,
            "geothermal_mw": geothermal,
        })
