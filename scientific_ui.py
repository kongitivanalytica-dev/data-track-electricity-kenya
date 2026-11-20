import json
import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import matplotlib
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

matplotlib.use("TkAgg")

from agents import DataAgent, ReportingAgent


ROOT = Path(__file__).resolve().parent
LIVE_CSV = ROOT / "live" / "simulation.csv"
LIVE_JSON = ROOT / "live" / "simulation.json"
SCENARIO_LOG = ROOT / "logs" / "scenario-terminal.log"


class ScientificDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Data Track Electricity Kenya")
        self.geometry("1380x820")
        self.configure(bg="#09111f")
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.frame = pd.DataFrame()
        self.meta = {}
        self.last_snapshot = None
        self._load_data()
        self._build_ui()
        self._poll_snapshot()

    def _load_data(self):
        if LIVE_CSV.exists():
            self.frame = pd.read_csv(LIVE_CSV)
            self.frame["timestamp"] = pd.to_datetime(self.frame["timestamp"])
        if LIVE_JSON.exists():
            self.meta = json.loads(LIVE_JSON.read_text(encoding="utf-8"))

    def _build_ui(self):
        header = tk.Frame(self, bg="#09111f", height=62)
        header.pack(fill="x")
        tk.Label(
            header,
            text="DATA TRACK  /  ELECTRICITY KENYA",
            fg="#63e6be",
            bg="#09111f",
            font=("Segoe UI", 18, "bold"),
        ).pack(side="left", padx=20, pady=12)
        tk.Label(
            header,
            text="Incorporated and designed by Aristote Kuji",
            fg="#8fa5bd",
            bg="#09111f",
            font=("Segoe UI", 9),
        ).pack(side="right", padx=20)

        self.cards = []
        cards = tk.Frame(self, bg="#09111f")
        cards.pack(fill="x", padx=14, pady=(2, 10))
        for title in ("CURRENT DEMAND", "RF FORECAST", "RENEWABLE SHARE", "BATTERY STATE"):
            panel = tk.Frame(cards, bg="#132238", highlightthickness=1, highlightbackground="#263d59")
            panel.pack(side="left", expand=True, fill="x", padx=5)
            tk.Label(panel, text=title, fg="#8fa5bd", bg="#132238", font=("Segoe UI", 9)).pack(pady=(8, 0))
            value = tk.Label(panel, text="--", fg="#ffffff", bg="#132238", font=("Segoe UI", 20, "bold"))
            value.pack(pady=(2, 9))
            self.cards.append(value)

        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill="both", padx=14, pady=(0, 12))
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background="#09111f", borderwidth=0)
        style.configure("TNotebook.Tab", background="#132238", foreground="#b9c8d8",
                        padding=(18, 8), font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#1d3d5b")])

        self.demand_tab = tk.Frame(notebook, bg="#09111f")
        self.generation_tab = tk.Frame(notebook, bg="#09111f")
        self.battery_tab = tk.Frame(notebook, bg="#09111f")
        self.residual_tab = tk.Frame(notebook, bg="#09111f")
        self.scores_tab = tk.Frame(notebook, bg="#09111f")
        self.history_tab = tk.Frame(notebook, bg="#09111f")
        self.terminal_tab = tk.Frame(notebook, bg="#09111f")
        for tab, name in (
            (self.demand_tab, "Demand & forecasts"),
            (self.generation_tab, "Generation"),
            (self.battery_tab, "Battery state"),
            (self.residual_tab, "Forecast residual"),
            (self.scores_tab, "Model scores"),
            (self.history_tab, "Historical OWID"),
            (self.terminal_tab, "Live scenario terminal"),
        ):
            notebook.add(tab, text=name)

        controls = tk.Frame(self.demand_tab, bg="#09111f")
        controls.pack(fill="x", pady=8)
        tk.Label(controls, text="Demand scenario", fg="#b9c8d8", bg="#09111f").pack(side="left", padx=8)
        self.scenario = tk.Scale(
            controls, from_=50, to=150, orient="horizontal", length=260,
            bg="#09111f", fg="#ffffff", highlightthickness=0, troughcolor="#263d59",
        )
        self.scenario.set(100)
        self.scenario.pack(side="left")

        self.demand_fig = Figure(figsize=(10, 4), dpi=100, facecolor="#09111f")
        self.demand_ax = self.demand_fig.add_subplot(111)
        self.demand_canvas = FigureCanvasTkAgg(self.demand_fig, master=self.demand_tab)
        self.demand_canvas.get_tk_widget().pack(fill="both", expand=True)
        self._style_axis(self.demand_ax)

        self.generation_fig = Figure(figsize=(10, 4), dpi=100, facecolor="#09111f")
        self.generation_ax = self.generation_fig.add_subplot(111)
        FigureCanvasTkAgg(self.generation_fig, master=self.generation_tab).get_tk_widget().pack(fill="both", expand=True)
        self._style_axis(self.generation_ax)

        self.battery_fig = Figure(figsize=(10, 4), dpi=100, facecolor="#09111f")
        self.battery_ax = self.battery_fig.add_subplot(111)
        FigureCanvasTkAgg(self.battery_fig, master=self.battery_tab).get_tk_widget().pack(fill="both", expand=True)
        self._style_axis(self.battery_ax)

        self.residual_fig = Figure(figsize=(10, 4), dpi=100, facecolor="#09111f")
        self.residual_ax = self.residual_fig.add_subplot(111)
        FigureCanvasTkAgg(self.residual_fig, master=self.residual_tab).get_tk_widget().pack(fill="both", expand=True)
        self._style_axis(self.residual_ax)
        self.scenario.configure(command=lambda _value: self._render_charts())

        self._build_scores_tab()
        self._build_history_tab()
        self._build_terminal_tab()

        actions = tk.Frame(self, bg="#09111f")
        actions.pack(fill="x", padx=14, pady=(0, 12))
        tk.Button(actions, text="Export Excel", command=self.export_excel,
                  bg="#1d3d5b", fg="white", relief="flat", padx=14).pack(side="left", padx=5)
        tk.Button(actions, text="Save to SQLite", command=self.save_sqlite,
                  bg="#1d3d5b", fg="white", relief="flat", padx=14).pack(side="left", padx=5)

    def _style_axis(self, ax):
        ax.set_facecolor("#0d1929")
        ax.tick_params(colors="#a9bacb")
        ax.xaxis.label.set_color("#a9bacb")
        ax.yaxis.label.set_color("#a9bacb")
        for spine in ax.spines.values():
            spine.set_color("#263d59")
        ax.grid(True, color="#263d59", alpha=0.35)

    def _build_scores_tab(self):
        metrics = self.meta.get("linear_metrics", {})
        rf_metrics = self.meta.get("random_forest_metrics", {})
        panel = tk.Frame(self.scores_tab, bg="#09111f")
        panel.pack(fill="both", expand=True)
        tk.Label(panel, text="CHRONOLOGICAL HOLDOUT SCORES", fg="#63e6be",
                 bg="#09111f", font=("Segoe UI", 13, "bold")).pack(pady=14)
        table = tk.Frame(panel, bg="#09111f")
        table.pack()
        for column, text in enumerate(("Model", "MAE (MW)", "RMSE (MW)")):
            tk.Label(table, text=text, width=22, bg="#132238", fg="#8fa5bd",
                     font=("Segoe UI", 9, "bold"), pady=8).grid(row=0, column=column, padx=2)
        for row, (name, values) in enumerate((
            ("Linear regression", metrics),
            ("Random Forest", rf_metrics),
        ), start=1):
            tk.Label(table, text=name, width=22, bg="#132238", fg="white").grid(row=row, column=0, padx=2, pady=2)
            tk.Label(table, text=f"{values.get('MAE', 0):.2f}", width=22, bg="#132238", fg="white").grid(row=row, column=1)
            tk.Label(table, text=f"{values.get('RMSE', 0):.2f}", width=22, bg="#132238", fg="white").grid(row=row, column=2)

        importance = self.meta.get("feature_importance", {})
        fig = Figure(figsize=(8, 3.2), dpi=100, facecolor="#09111f")
        ax = fig.add_subplot(111)
        ax.set_facecolor("#0d1929")
        if importance:
            names = list(importance)
            values = list(importance.values())
            ax.barh(names, values, color="#63e6be")
        ax.tick_params(colors="#a9bacb")
        ax.set_title("Random Forest feature importance", color="white")
        FigureCanvasTkAgg(fig, master=panel).get_tk_widget().pack(pady=18)

    def _build_history_tab(self):
        text = tk.Text(self.history_tab, bg="#0d1929", fg="#d7e3ef", insertbackground="white",
                       font=("Consolas", 10), padx=12, pady=12)
        text.pack(fill="both", expand=True)
        try:
            owid, source = DataAgent().load_owid_kenya()
            text.insert("1.0", f"Source: {source}\n\n")
            columns = [c for c in (
                "year", "electricity_demand", "electricity_generation",
                "hydro_generation", "solar_generation", "wind_generation",
            ) if c in owid.columns]
            text.insert("end", owid[columns].tail(80).to_string(index=False))
        except Exception as exc:
            text.insert("1.0", f"Historical data unavailable: {exc}")

    def _build_terminal_tab(self):
        self.terminal = tk.Text(
            self.terminal_tab, bg="#061018", fg="#63e6be",
            font=("Consolas", 10), insertbackground="#63e6be", padx=12, pady=12,
        )
        self.terminal.pack(fill="both", expand=True)

    def _update_cards(self, row):
        if row is None:
            return
        renewable = row.get("solar_available_mw", 0) + row.get("wind_available_mw", 0) + \
                    row.get("hydro_available_mw", 0) + row.get("geothermal_available_mw", 0)
        share = 100 * renewable / max(row["demand_mw"], 1)
        values = (
            f"{row['demand_mw']:.1f} MW",
            f"{row['random_forest_forecast_mw']:.1f} MW",
            f"{share:.1f}%",
            f"{row['soc_mwh']:.1f} MWh",
        )
        for card, value in zip(self.cards, values):
            card.config(text=value)

    def _render_charts(self):
        if not self.frame.empty:
            row = self.frame.iloc[-1]
            self._update_cards(row)
            window = self.frame.tail(336)
            x = range(len(window))
            scale = self.scenario.get() / 100
            self.demand_ax.clear()
            self._style_axis(self.demand_ax)
            self.demand_ax.plot(x, window["demand_mw"] * scale, color="#63e6be", label="Actual synthetic demand")
            self.demand_ax.plot(x, window["linear_forecast_mw"] * scale, color="#58a6ff", alpha=0.9, label="Linear")
            self.demand_ax.plot(x, window["random_forest_forecast_mw"] * scale, color="#f4b860", alpha=0.9, label="Random Forest")
            self.demand_ax.legend(facecolor="#132238", labelcolor="white")
            self.demand_canvas.draw_idle()

            self.generation_ax.clear()
            self._style_axis(self.generation_ax)
            for column, color in (
                ("geothermal_available_mw", "#b18cff"),
                ("hydro_available_mw", "#58a6ff"),
                ("wind_available_mw", "#63e6be"),
                ("solar_available_mw", "#f4b860"),
            ):
                self.generation_ax.plot(x, window[column], color=color, label=column.replace("_available_mw", "").title())
            self.generation_ax.legend(facecolor="#132238", labelcolor="white")
            self.generation_fig.canvas.draw_idle()

            self.battery_ax.clear()
            self._style_axis(self.battery_ax)
            self.battery_ax.plot(x, window["soc_mwh"], color="#63e6be")
            self.battery_ax.axhline(180, linestyle="--", color="#ff6b6b", alpha=0.8)
            self.battery_ax.axhline(1620, linestyle="--", color="#ff6b6b", alpha=0.8)
            self.battery_fig.canvas.draw_idle()

            residual = window["demand_mw"] - window["random_forest_forecast_mw"]
            self.residual_ax.clear()
            self._style_axis(self.residual_ax)
            self.residual_ax.axhline(0, color="#b9c8d8", linewidth=0.8)
            self.residual_ax.plot(x, residual, color="#f4b860")
            self.residual_fig.canvas.draw_idle()

    def _poll_snapshot(self):
        if LIVE_CSV.exists():
            frame = pd.read_csv(LIVE_CSV)
            if not frame.empty:
                frame["timestamp"] = pd.to_datetime(frame["timestamp"])
                latest = frame.iloc[-1]["timestamp"]
                if latest != self.last_snapshot:
                    self.frame = frame
                    self.last_snapshot = latest
                    self._render_charts()
                    self.meta = json.loads(LIVE_JSON.read_text(encoding="utf-8"))
        if SCENARIO_LOG.exists():
            lines = SCENARIO_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
            if lines:
                desired = "\n".join(lines[-12:])
                if self.terminal.get("1.0", "end-1c") != desired:
                    self.terminal.delete("1.0", "end")
                    self.terminal.insert("1.0", desired)
        self.after(250, self._poll_snapshot)

    def export_excel(self):
        try:
            owid, source = DataAgent().load_owid_kenya()
            metrics = {
                "linear": self.meta.get("linear_metrics", {}),
                "random_forest": self.meta.get("random_forest_metrics", {}),
            }
            summary = self.meta.get("summary", {})
            path = ReportingAgent().export_excel(
                self.frame, summary, metrics, owid, source
            )
            messagebox.showinfo("Excel export", f"Workbook saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def save_sqlite(self):
        try:
            metrics = {
                "linear": self.meta.get("linear_metrics", {}),
                "random_forest": self.meta.get("random_forest_metrics", {}),
            }
            path = ReportingAgent().save_sqlite(
                self.frame, self.meta.get("summary", {}),
                metrics, self.meta.get("data_source", "unknown"),
            )
            messagebox.showinfo("SQLite save", f"Database saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("SQLite save failed", str(exc))


if __name__ == "__main__":
    ScientificDashboard().mainloop()
