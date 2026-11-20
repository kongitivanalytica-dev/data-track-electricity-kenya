import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error


class ForecastAgent:
    def fit(self, frame):
        hour = frame["timestamp"].dt.hour
        day = frame["timestamp"].dt.dayofyear
        features = np.column_stack([
            np.sin(2 * np.pi * hour / 24),
            np.cos(2 * np.pi * hour / 24),
            np.sin(2 * np.pi * day / 365),
            np.cos(2 * np.pi * day / 365),
            frame["temperature_c"].to_numpy(),
            frame["irradiance_w_m2"].to_numpy(),
        ])
        target = frame["demand_mw"].to_numpy()
        split = int(len(frame) * 0.8)
        x_train, x_test = features[:split], features[split:]
        y_train, y_test = target[:split], target[split:]

        linear = LinearRegression().fit(x_train, y_train)
        forest = RandomForestRegressor(n_estimators=120, random_state=42, n_jobs=-1).fit(x_train, y_train)
        linear_all = linear.predict(features)
        forest_all = forest.predict(features)
        linear_test = linear.predict(x_test)
        forest_test = forest.predict(x_test)

        return {
            "linear": linear_all,
            "random_forest": forest_all,
            "linear_metrics": self._metrics(y_test, linear_test),
            "random_forest_metrics": self._metrics(y_test, forest_test),
            "feature_importance": dict(zip(
                ["Hour sine", "Hour cosine", "Day sine", "Day cosine", "Temperature", "Irradiance"],
                forest.feature_importances_,
            )),
            "linear_model": linear,
            "forest_model": forest,
        }

    @staticmethod
    def _metrics(actual, predicted):
        return {
            "MAE": float(mean_absolute_error(actual, predicted)),
            "RMSE": float(np.sqrt(mean_squared_error(actual, predicted))),
        }
