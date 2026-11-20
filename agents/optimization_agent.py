import numpy as np
from scipy.optimize import linprog


class OptimizationAgent:
    def __init__(self):
        self.capacity_mwh = 1800
        self.power_mw = 500
        self.soc_min = 180
        self.soc_max = 1620
        self.soc_mwh = 900
        self.efficiency = 0.92

    def dispatch(self, demand, available):
        geo, hydro, wind, solar = available
        charge_limit = min(self.power_mw, (self.soc_max - self.soc_mwh) / self.efficiency)
        discharge_limit = min(self.power_mw, (self.soc_mwh - self.soc_min) * self.efficiency)
        c = [55, 42, 26, 6, 0, 8, 2000]
        result = linprog(
            c,
            A_eq=[[1, 1, 1, 1, -1, 1, 1]],
            b_eq=[demand],
            bounds=[
                (0, geo), (0, hydro), (0, wind), (0, solar),
                (0, charge_limit), (0, discharge_limit), (0, demand),
            ],
            method="highs",
        )
        if not result.success:
            unmet = demand
            geo_out = hydro_out = wind_out = solar_out = 0
            charge = 0
            discharge = 0
        else:
            geo_out, hydro_out, wind_out, solar_out, charge, discharge, unmet = result.x
        self.soc_mwh = float(
            np.clip(
                self.soc_mwh + self.efficiency * charge - discharge / self.efficiency,
                self.soc_min,
                self.soc_max,
            )
        )
        action = "CHARGING" if charge > 1 else "DISCHARGING" if discharge > 1 else "IDLE"
        return {
            "geothermal": float(geo_out),
            "hydro": float(hydro_out),
            "wind": float(wind_out),
            "solar": float(solar_out),
            "charge": float(charge),
            "discharge": float(discharge),
            "unmet": float(unmet),
            "soc": self.soc_mwh,
            "action": action,
        }
