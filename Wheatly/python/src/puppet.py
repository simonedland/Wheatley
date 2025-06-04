#!/usr/bin/env python3
"""
servo_puppet.py – GUI for OpenRB-150 / Core-2
rev 12.0 · 2025-06-04
────────────────────────────────────────────────────────────────────────
UI refresh
• LED picker, preset bar and “Send ALL Config” now live **under the servo
  table** (left pane) for quicker access.
• Right pane holds only the scrolling log.
• Numeric fields align perfectly with sliders by defining the column
  widths once (instead of per-row) and using uniform padding.
• All functionality from rev 11.9 is retained.
"""

import argparse, json, os, queue, sys, threading, time
import tkinter as tk
from functools import partial
from tkinter import (
    BOTH, END, HORIZONTAL, Y,
    Tk, PanedWindow, colorchooser, simpledialog, TclError
)
from tkinter import ttk

# ── constants ──────────────────────────────────────────────────────────
SERVO_NAMES = ("lens", "eyelid1", "eyelid2",
               "eyeX", "eyeY", "handle1", "handle2")
DEFAULT_MIN = [0,180,140,130,140,-60,-60]
DEFAULT_MAX = [0,220,180,220,210, 60,60]
ACCENT      = "#00c3ff"
BAR_COLOR   = "#00c851"
PX          = 6
BAR_HEIGHT  = 28

COL_NAME, COL_SCALE, COL_VEL, COL_VEL_LBL, COL_IDLE, COL_IDLE_LBL, \
COL_INTV, COL_INTV_LBL, COL_MOVE, COL_CFG = range(10)

# ── optional serial ----------------------------------------------------
try:
    import serial
except ImportError:
    serial = None

# ── Serial backend (unchanged) ─────────────────────────────────────────
class SerialBackend:
    def __init__(self, port, baud, dry):
        self.port, self.baud, self.dry = port, baud, dry
        self.ser=None
        self.rx_q, self.tx_q = queue.Queue(), queue.Queue()
        self._stop = threading.Event()

    def open(self):
        if self.dry or serial is None:
            return True
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
        except serial.SerialException as e:
            print(e)
            return False
        threading.Thread(target=self._reader, daemon=True).start()
        return True

    def _reader(self):
        while not self._stop.is_set():
            if self.ser and self.ser.in_waiting:
                try:
                    line = self.ser.readline().decode(errors="ignore").strip()
                    self.rx_q.put(line)
                except serial.SerialException:
                    break
            time.sleep(0.02)

    def send(self, txt: str):
        if not txt.endswith("\n"):
            txt += "\n"
        self.tx_q.put(txt.rstrip())
        if not self.dry and self.ser and self.ser.is_open:
            self.ser.write(txt.encode())

    def close(self):
        self._stop.set()
        self.ser and self.ser.close()


# ╔════════════ GUI class ═══════════════════════════════════════════════╗
class PuppetGUI(Tk):
    def __init__(self, backend: SerialBackend):
        super().__init__()
        self.backend = backend
        self.title("Servo Puppet")
        self.geometry("1280x860")

        self.anim_file = "animations.json"
        self.animations = self._load_json()
        self.row_vars = []  # (scale, vel, idle, intv, canvas)

        self._theme()
        self._layout()
        self.after(50, self._pump)

    # ── theme ----------------------------------------------------------
    def _theme(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except TclError:
            pass
        base = "#1e1e1e"
        s.configure(".", background=base, foreground="#e8e8e8",
                    font=("Segoe UI", 10))
        s.configure("TEntry", fieldbackground="#2d2d2d",
                    foreground="#e8e8e8", borderwidth=0)
        s.configure("Horizontal.TScale", troughcolor="#2d2d2d",
                    sliderthickness=18, background=ACCENT)
        s.map("TButton",
              foreground=[("!disabled", "#ffffff")],
              background=[("active", ACCENT), ("pressed", "#0094c2")])
        self.configure(background=base)

    # ── JSON helpers ---------------------------------------------------
    def _load_json(self):
        try:
            with open(self.anim_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_json(self):
        with open(self.anim_file, "w", encoding="utf-8") as f:
            json.dump(self.animations, f, indent=2)

    # ── layout ---------------------------------------------------------
    def _layout(self):
        main = PanedWindow(self, orient="horizontal",
                           sashrelief="raised", bg="#1e1e1e")
        main.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # left pane – servo grid + controls
        left = ttk.Frame(main)
        main.add(left, minsize=720)

        grid = ttk.Frame(left)
        grid.pack(fill="x", expand=False)
        # common column widths for alignment
        grid.grid_columnconfigure(COL_NAME,   minsize=70)
        grid.grid_columnconfigure(COL_SCALE,  weight=1)
        grid.grid_columnconfigure(COL_VEL,    minsize=50)
        grid.grid_columnconfigure(COL_IDLE,   minsize=50)
        grid.grid_columnconfigure(COL_INTV,   minsize=70)
        grid.grid_columnconfigure(COL_MOVE,   minsize=60)
        grid.grid_columnconfigure(COL_CFG,    minsize=60)

        for r, (sid, name) in enumerate(zip(range(7), SERVO_NAMES)):
            self._servo_row(grid, r, sid, name)

        # controls directly under servo table
        ctrl = ttk.Frame(left)
        ctrl.pack(fill="x", pady=(12, 0))
        ctrl.columnconfigure(0, weight=1)

        self._led_row(ctrl)
        self._preset_bar(ctrl)
        ttk.Button(ctrl, text="Send ALL Config", style="Accent.TButton",
                   command=self._send_all).pack(pady=(4, 0))

        # right pane – log only
        right = ttk.Frame(main)
        main.add(right, minsize=520)
        right.rowconfigure(0, weight=1)
        self._log_area(right).grid(row=0, column=0, sticky="nsew")

    # ── servo row ------------------------------------------------------
    def _servo_row(self, parent, r, sid, name):
        ttk.Label(parent, text=f"{sid}:{name}").grid(
            row=r, column=COL_NAME, sticky="e", padx=(0, PX)
        )

        holder = ttk.Frame(parent)
        holder.grid(row=r, column=COL_SCALE, sticky="ew", padx=PX)
        holder.grid_columnconfigure(0, weight=1)

        scale = ttk.Scale(holder, from_=DEFAULT_MIN[sid], to=DEFAULT_MAX[sid],
                          orient=HORIZONTAL)
        scale.grid(row=0, column=0, sticky="ew")

        canvas = tk.Canvas(holder, height=BAR_HEIGHT, background="#2d2d2d",
                           highlightthickness=0)
        canvas.grid(row=1, column=0, sticky="ew")

        def ent(default, width, col):
            e = ttk.Entry(parent, width=width, justify="center")
            e.insert(0, default)
            e.grid(row=r, column=col, padx=(0, 2))
            return e

        vel  = ent("5",     5, COL_VEL)
        idle = ent("10",    5, COL_IDLE)
        intv = ent("2000",  7, COL_INTV)

        ttk.Label(parent, text="vel").grid (row=r, column=COL_VEL_LBL , sticky="w")
        ttk.Label(parent, text="idle").grid(row=r, column=COL_IDLE_LBL, sticky="w")
        ttk.Label(parent, text="ms").grid  (row=r, column=COL_INTV_LBL, sticky="w")

        ttk.Button(parent, text="Move",
                   command=partial(self._send_move, sid, scale, vel)
                  ).grid(row=r, column=COL_MOVE, padx=4)

        ttk.Button(parent, text="Cfg",
                   command=partial(self._send_cfg_one, sid, scale, vel, idle, intv)
                  ).grid(row=r, column=COL_CFG)

        idx = len(self.row_vars)
        self.row_vars.append((scale, vel, idle, intv, canvas))
        idle .bind("<FocusOut>", lambda e, row=idx: self._draw_band(row))
        scale.configure(command=lambda _, row=idx: self._draw_band(row))
        canvas.bind("<Configure>", lambda e, row=idx: self._draw_band(row))

    # draw idle band + ticks + labels ----------------------------------
    def _draw_band(self, row):
        sc, _v, idle_ent, _i, cv = self.row_vars[row]
        try:    ir = int(idle_ent.get())
        except ValueError: ir = 0
        cur = float(sc.get())
        mn, mx = DEFAULT_MIN[row], DEFAULT_MAX[row]
        span = mx - mn
        w = cv.winfo_width()
        cv.delete("all")
        if w < 4 or span == 0:
            return

        for frac in (0, .25, .5, .75, 1):
            x = int(frac * w)
            h = 14 if frac in (0, 1) else 8
            cv.create_line(x, 0, x, h, fill="#606060", width=1)

        lbl_y = 15
        cv.create_text(2, lbl_y, anchor="nw", text=str(mn),
                       fill="#909090", font=("Segoe UI", 7))
        cv.create_text(w-2, lbl_y, anchor="ne", text=str(mx),
                       fill="#909090", font=("Segoe UI", 7))

        lo = max(mn, cur - ir); hi = min(mx, cur + ir)
        x0 = int((lo - mn) / span * w)
        x1 = int((hi - mn) / span * w)
        cv.create_rectangle(x0, 20, x1, BAR_HEIGHT, fill=BAR_COLOR, width=0)

        x_cur = int((cur - mn) / span * w)
        cv.create_line(x_cur, 0, x_cur, BAR_HEIGHT,
                       fill="#ffffff", width=1)

    # LED row -----------------------------------------------------------
    def _led_row(self, parent):
        fr = ttk.Frame(parent); fr.pack(fill="x")
        ttk.Label(fr, text="LED RGB").pack(side="left", padx=(0, 12))
        self.r = self._rgb(fr, "255")
        self.g = self._rgb(fr, "255")
        self.b = self._rgb(fr, "255")
        ttk.Button(fr, text="Pick", command=self._pick_color
                   ).pack(side="left", padx=(10, 6))
        ttk.Button(fr, text="Send LED", command=self._send_led
                   ).pack(side="left")

    def _rgb(self, parent, default):
        e = ttk.Entry(parent, width=5, justify="center")
        e.insert(0, default)
        e.pack(side="left", padx=2)
        return e

    # preset bar --------------------------------------------------------
    def _preset_bar(self, parent):
        fr = ttk.Frame(parent); fr.pack(fill="x", pady=(6, 0))
        ttk.Label(fr, text="Preset").pack(side="left", padx=(0, 8))
        self.cb = ttk.Combobox(fr, state="readonly", width=22,
                               values=list(self.animations.keys()))
        self.cb.pack(side="left")
        ttk.Button(fr, text="Apply", command=self._apply_preset
                   ).pack(side="left", padx=6)
        ttk.Button(fr, text="Save…", style="Accent.TButton",
                   command=self._save_preset).pack(side="left")

    # log ---------------------------------------------------------------
    def _log_area(self, parent):
        container = ttk.Frame(parent)
        self.log = tk.Text(container, wrap="word", background="#121212",
                           foreground="#dcdcdc", borderwidth=0,
                           font=("Consolas", 10))
        sb = ttk.Scrollbar(container, command=self.log.yview, orient="vertical")
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left", fill=BOTH, expand=True)
        sb.pack(side="right", fill=Y)
        return container

    # preset save / apply ----------------------------------------------
    def _save_preset(self):
        name = simpledialog.askstring("Save animation", "Preset name:", parent=self)
        if not name:
            return
        velocities, factors, idle_ranges, intervals = [], [], [], []
        for sid, (sc, vel_e, idle_e, intv_e, _c) in enumerate(self.row_vars):
            try:
                angle = int(sc.get())
                velocities.append(int(float(vel_e.get())))
                idle_ranges.append(int(idle_e.get()))
                intervals.append(int(intv_e.get()))
            except ValueError:
                return self._msg("bad number")
            mn, mx = DEFAULT_MIN[sid], DEFAULT_MAX[sid]
            span = mx - mn
            factor = (angle - mn) / span if span else 0.0
            factors.append(round(factor, 3))

        try:
            r, g, b = (int(self.r.get()), int(self.g.get()), int(self.b.get()))
        except ValueError:
            return self._msg("bad LED")

        self.animations[name] = {
            "velocities": velocities,
            "target_factors": factors,
            "idle_ranges": idle_ranges,
            "intervals": intervals,
            "color": [r, g, b],
        }
        self._save_json()
        self.cb["values"] = list(self.animations.keys())
        self.cb.set(name)
        self._msg("preset saved")

    def _apply_preset(self):
        d = self.animations.get(self.cb.get())
        if not d:
            return
        for sid, (sc, vel_e, idle_e, intv_e, _c) in enumerate(self.row_vars):
            vel_e.delete(0, END); vel_e.insert(0, d["velocities"][sid])
            idle_e.delete(0, END); idle_e.insert(0, d["idle_ranges"][sid])
            intv_e.delete(0, END); intv_e.insert(0, d["intervals"][sid])
            mn, mx = DEFAULT_MIN[sid], DEFAULT_MAX[sid]
            sc.set(mn + d["target_factors"][sid] * (mx - mn))
            self._draw_band(sid)
        r,g,b = d["color"]
        for e,val in zip((self.r,self.g,self.b),(r,g,b)):
            e.delete(0,END); e.insert(0,val)
        self._msg("preset applied"); self._send_all()

    # command helpers ---------------------------------------------------
    def _send_move(self, sid, sc, vel_e):
        try:
            self.backend.send(
                f"MOVE_SERVO;ID={sid};TARGET={int(sc.get())};VELOCITY={int(float(vel_e.get()))};"
            )
        except ValueError:
            self._msg("bad move")

    def _send_cfg_one(self, sid, sc, vel, idle, intv):
        try:
            self.backend.send(
                f"SET_SERVO_CONFIG:{sid},{int(sc.get())},{int(float(vel.get()))},{int(idle.get())},{int(intv.get())}"
            )
        except ValueError:
            self._msg("bad cfg")

    def _send_all(self):
        chunks=[]
        for sid,(sc,vel,idle,intv,_c) in enumerate(self.row_vars):
            try:
                chunks.append(
                    f"{sid},{int(sc.get())},{int(float(vel.get()))},{int(idle.get())},{int(intv.get())}"
                )
            except ValueError:
                return self._msg("bad bulk")
        self.backend.send("SET_SERVO_CONFIG:" + ";".join(chunks))
        self._send_led()

    def _send_led(self):
        try:
            r, g, b = (int(self.r.get()), int(self.g.get()), int(self.b.get()))
        except ValueError:
            return self._msg("bad LED")
        self.backend.send(
            f"SET_LED;R={max(0,min(255,r))};G={max(0,min(255,g))};B={max(0,min(255,b))};"
        )

    # utilities ---------------------------------------------------------
    def _pick_color(self):
        col = colorchooser.askcolor()[0]
        if col:
            for e, val in zip((self.r, self.g, self.b), map(int, col)):
                e.delete(0, END); e.insert(0, val)

    def _msg(self, txt: str):
        self.log.configure(state="normal")
        self.log.insert(END, txt + "\n")
        self.log.configure(state="disabled")
        self.log.yview_moveto(1.0)

    def _pump(self):
        while not self.backend.tx_q.empty():
            self._msg("→ " + self.backend.tx_q.get_nowait())
        while not self.backend.rx_q.empty():
            self._msg("← " + self.backend.rx_q.get_nowait())
        self.after(50, self._pump)


# ── auto port helper ---------------------------------------------------
def auto_port():
    if serial is None:
        return None
    from serial.tools import list_ports
    for p in list_ports.comports():
        if "USB" in p.description or "CP210" in p.description:
            return p.device

# ── main --------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--port")
    ap.add_argument("-b", "--baud", type=int, default=115200)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.port is None and not args.dry_run:
        args.port = auto_port() or ""
        args.dry_run = not bool(args.port)

    backend = SerialBackend(args.port, args.baud, args.dry_run)
    if not args.dry_run and not backend.open():
        sys.exit(1)

    gui = PuppetGUI(backend)
    if not args.dry_run:
        backend.send("GET_SERVO_CONFIG")
    gui.mainloop()
    backend.close()

if __name__ == "__main__":
    main()
