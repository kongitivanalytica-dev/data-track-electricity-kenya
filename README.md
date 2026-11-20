# Data Track Electricity Kenya

A reproducible scientific desktop prototype for synthetic hourly demand forecasting,
renewable availability, battery dispatch, and scenario visualization.

## Run on Windows

```powershell
.\.venv-win\Scripts\python.exe -m pip install -r requirements.txt
.\start.bat
```

## Run on Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./start.sh
```

The application explicitly separates annual OWID historical context from the
synthetic hourly demonstration. The live worker publishes one new simulated hour
per second; the charts and scenario terminal refresh from those new rows. Its
forecasts and dispatch results are not operational recommendations for Kenya's grid.
