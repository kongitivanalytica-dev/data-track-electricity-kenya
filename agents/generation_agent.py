import numpy as np


class GenerationAgent:
    def calculate(self, frame):
        return {
            "geothermal": np.clip(frame["geothermal_mw"].to_numpy(), 700, 1100),
            "hydro": np.clip(frame["hydro_mw"].to_numpy(), 0, 2200),
            "wind": np.clip(frame["wind_mw"].to_numpy(), 0, 1700),
            "solar": np.clip(frame["solar_mw"].to_numpy(), 0, 2200),
        }
