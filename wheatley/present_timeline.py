"""GUI to display a chronological timeline and detailed graphs from timing and log files.

Key features
------------
• Gantt-width fix (seconds → fraction-of-day).
• Mouse-wheel zoom:
      – Wheel        → horizontal (time) zoom.
      – Shift+Wheel  → vertical (labels) zoom.
• NavigationToolbar2Tk for pan/box-zoom/save.
"""

import os
import json
import datetime as dt
import tkinter as tk
from tkinter import ttk, filedialog
from collections import defaultdict

import matplotlib
matplotlib.use("TkAgg")                     # Tk backend for embedding
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


# ── helpers ────────────────────────────────────────────────────────────────
def load_timings(path: str = "timings.json"):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_logs(path: str = "assistant.log"):
    import re
    if not os.path.exists(path):
        return []
    line_re = re.compile(
        r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+([A-Z]+):\s+(.*)$"
    )
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = line_re.match(line)
            if m:
                ts_str, lvl, msg = m.groups()
                events.append(
                    {"timestamp": dt.datetime.fromisoformat(ts_str),
                     "level": lvl,
                     "message": msg.strip()}
                )
    return events


# ── GUI ────────────────────────────────────────────────────────────────────
class TimelineGUI(tk.Tk):
    ZOOM_STEP = 0.8            # 0.8 → zoom in 20 %, 1/0.8 zoom out

    def __init__(self):
        super().__init__()
        self.title("Timeline & Timing Insights")
        self.geometry("1000x700")

        self.timing_file = "timings.json"
        self.log_file = "assistant.log"
        self.timings = []
        self.logs = []

        self._make_widgets()
        self._reload_everything()

    # ── layout ─────────────────────────────────────────────────────────
    def _make_widgets(self):
        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)

        ttk.Button(top, text="Reload Data",
                   command=self._reload_everything).pack(side=tk.LEFT)
        ttk.Button(top, text="Open Timing File",
                   command=self._pick_timing).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Open Log File",
                   command=self._pick_log).pack(side=tk.LEFT, padx=4)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True)

        self.tab_timeline = ttk.Frame(self.nb)
        self.tab_summary  = ttk.Frame(self.nb)
        self.tab_logs     = ttk.Frame(self.nb)

        self.nb.add(self.tab_timeline, text="Timeline")
        self.nb.add(self.tab_summary , text="Time Summary")
        self.nb.add(self.tab_logs    , text="Logs")

        self.log_txt = tk.Text(self.tab_logs, wrap=tk.NONE, height=20)
        self.log_txt.pack(fill=tk.BOTH, expand=True)

    # ── file pickers ──────────────────────────────────────────────────
    def _pick_timing(self):
        path = filedialog.askopenfilename(
            title="Select Timing JSON", filetypes=[("JSON", "*.json")]
        )
        if path:
            self.timing_file = path
            self._reload_everything()

    def _pick_log(self):
        path = filedialog.askopenfilename(
            title="Select Log File",
            filetypes=[("Log", "*.log"), ("All files", "*.*")]
        )
        if path:
            self.log_file = path
            self._reload_everything()

    # ── data / refresh ────────────────────────────────────────────────
    def _reload_everything(self):
        self.timings = load_timings(self.timing_file)
        self.logs    = load_logs(self.log_file)
        self._draw_timeline()
        self._draw_summary()
        self._show_logs()

    # ── plots ─────────────────────────────────────────────────────────
    def _draw_timeline(self):
        for w in self.tab_timeline.winfo_children():
            w.destroy()

        # pre-process timings
        rows = [
            (dt.datetime.fromisoformat(t["startTime"]),
             float(t["durationMs"]) / 1000.0,
             t["functionality"])
            for t in self.timings if float(t["durationMs"]) > 0
        ]
        if not rows:
            ttk.Label(self.tab_timeline, text="No non-zero duration entries.").pack()
            return

        rows.sort(key=lambda r: r[0])
        starts_dt, secs, labels = zip(*rows)
        starts_num = mdates.date2num(starts_dt)
        widths     = [s / 86400 for s in secs]          # sec → days
        y_pos      = range(len(labels))

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.barh(y_pos, widths, left=starts_num,
                height=0.5, color="skyblue", edgecolor="black")

        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(labels)
        ax.set_xlabel("Time")
        ax.set_title("Functionality Timeline\n"
                     "(Wheel = X-zoom, Shift+Wheel = Y-zoom)")
        ax.xaxis_date()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M:%S"))
        ax.grid(axis="x", linestyle="--", alpha=0.6)

        ax.set_xlim(min(starts_num), max(s + w for s, w in zip(starts_num, widths)))
        ax.set_ylim(-1, len(labels))   # nice starting bounds
        fig.autofmt_xdate()

        # embed in Tk
        canvas  = FigureCanvasTkAgg(fig, master=self.tab_timeline)
        toolbar = NavigationToolbar2Tk(canvas, self.tab_timeline, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(side=tk.TOP, fill=tk.X)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # ── wheel zoom handler ──────────────────────────────────────
        def _on_scroll(event):
            ax = event.inaxes
            if ax is None:           # cursor outside plot
                return

            # choose which axis to zoom
            vert_zoom = (event.key == "shift")
            cur_lim   = ax.get_ylim() if vert_zoom else ax.get_xlim()
            center    = event.ydata if vert_zoom else event.xdata
            if center is None:
                return

            # determine scale
            scale = self.ZOOM_STEP if event.button == "up" else 1 / self.ZOOM_STEP
            span  = (cur_lim[1] - cur_lim[0]) * scale
            rel   = (center - cur_lim[0]) / (cur_lim[1] - cur_lim[0])

            new_min = center - span * rel
            new_max = center + span * (1 - rel)

            # keep sensible bounds (prevent flipping)
            if vert_zoom:
                ax.set_ylim(max(new_min, -1), min(new_max, len(labels)))
            else:
                ax.set_xlim(new_min, new_max)
            canvas.draw_idle()

        fig.canvas.mpl_connect("scroll_event", _on_scroll)

    # ------------------------------------------------------------------
    def _draw_summary(self):
        for w in self.tab_summary.winfo_children():
            w.destroy()

        if not self.timings:
            ttk.Label(self.tab_summary, text="No timing data.").pack()
            return

        totals = defaultdict(float)
        for t in self.timings:
            totals[t["functionality"]] += float(t["durationMs"]) / 1000.0

        labels, secs = zip(*sorted(totals.items(), key=lambda x: -x[1]))

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(labels, secs, color="orange")
        ax.set_xlabel("Total Time (seconds)")
        ax.set_title("Total Time per Functionality")
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.tab_summary)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    def _show_logs(self):
        self.log_txt.delete(1.0, tk.END)
        if not self.logs:
            self.log_txt.insert(tk.END, "No log data.\n")
            return
        for log in self.logs:
            self.log_txt.insert(
                tk.END,
                f"{log['timestamp']} [{log['level']}] {log['message']}\n"
            )


# ── run ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    TimelineGUI().mainloop()
