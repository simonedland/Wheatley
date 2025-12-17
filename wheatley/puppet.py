"""
servo_puppet.py – GUI for OpenRB-150 / Core-2.

rev 12.3 · 2025-06-06
────────────────────────────────────────────────────────────────────────
• NEW: red dot on every slider shows the *actual* angle coming back from
  the Core-2 (“[→RB] MOVE_SERVO;ID=…;TARGET=…;” lines or the
  “Servo n: angle=…” debug lines).
• Eyelids are no longer treated specially – all servos use 1:1 angles.
• All previous features (idle band, presets, LED, limit-lock) unchanged.
"""

import argparse
import json
import queue
import re
import sys
import threading
import time
import tkinter as tk
from functools import partial
from typing import Any
from tkinter import (
    BOTH,
    END,
    HORIZONTAL,
    Y,
    Tk,
    PanedWindow,
    colorchooser,
    simpledialog,
    TclError,
)
from tkinter import ttk

# ── constants ──────────────────────────────────────────────────────────
SERVO_NAMES = (
    "lens",
    "eyelid1",
    "eyelid2",
    "eyeX",
    "eyeY",
    "handle1",
    "handle2",
    "eyeX2",
    "eyeY2",
    "eyeZ",
)
DEFAULT_MIN = [0, 180, 140, 130, 140, -60, -60, 150, 130, 140]
DEFAULT_MAX = [0, 220, 180, 220, 210, 60, 60, 180, 200, 220]
ACCENT = "#00c3ff"
BAR_COLOR = "#00c851"
DOT_COLOR = "#ff4040"
PX = 6
BAR_HEIGHT = 28

(
    COL_NAME,
    COL_SCALE,
    COL_VEL,
    COL_VEL_LBL,
    COL_IDLE,
    COL_IDLE_LBL,
    COL_INTV,
    COL_INTV_LBL,
    COL_MOVE,
    COL_CFG,
) = range(10)

# ── optional serial ----------------------------------------------------
try:
    import serial  # type: ignore[import-untyped]
except ImportError:
    serial = None


# ╔════════════ thin serial wrapper ════════════════════════════════════╗
class SerialBackend:
    """Thin serial wrapper for communication with hardware."""

    def __init__(self, port, baud, dry):
        """Initialize SerialBackend."""
        self.port, self.baud, self.dry = port, baud, dry
        self.ser = None
        self.rx_q, self.tx_q = queue.Queue(), queue.Queue()
        self._stop = threading.Event()

    def open(self):
        """Open the serial port."""
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
        """Read lines from the serial port."""
        while not self._stop.is_set():
            if self.ser and self.ser.in_waiting:
                try:
                    line = self.ser.readline().decode(errors="ignore").strip()
                    self.rx_q.put(line)
                except serial.SerialException:
                    break
            time.sleep(0.02)

    def send(self, txt: str):
        """Send a line to the serial port."""
        if not txt.endswith("\n"):
            txt += "\n"
        self.tx_q.put(txt.rstrip())
        if not self.dry and self.ser and self.ser.is_open:
            self.ser.write(txt.encode())

    def close(self):
        """Close the serial port."""
        self._stop.set()
        if self.ser:
            self.ser.close()


# ╔════════════ GUI class ═══════════════════════════════════════════════╗
class PuppetGUI(Tk):
    """Main GUI for controlling servos and LEDs."""

    def __init__(self, backend: SerialBackend):
        """Initialize the PuppetGUI."""
        super().__init__()
        self.backend = backend
        self.limits_ready = False
            self.move_buttons: list[Any] = []  # List of move buttons
            self.cfg_buttons: list[Any] = []  # List of config buttons
            self.current_angles: list[Any] = []  # List of actual positions
        self.title("Servo Puppet")
        self.geometry("1280x860")
        self.anim_file = "animations.json"
        self.animations = self._load_json()
            self.row_vars: list[Any] = []  # List of row variables (scale, vel, idle, intv, canvas)
        self.servo_min = list(DEFAULT_MIN)
        self.servo_max = list(DEFAULT_MAX)
        self._theme()
        self._layout()
        self._disable_tx_buttons(True)  # lock UI at boot
        self.after(50, self._pump)

    def _theme(self):
        """Set the theme for the GUI."""
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except TclError:
            pass
        base = "#1e1e1e"
        s.configure(".", background=base, foreground="#e8e8e8", font=("Segoe UI", 10))
        s.configure(
            "TEntry", fieldbackground="#2d2d2d", foreground="#e8e8e8", borderwidth=0
        )
        s.configure(
            "Horizontal.TScale",
            troughcolor="#2d2d2d",
            sliderthickness=18,
            background=ACCENT,
        )
        s.map(
            "TButton",
            foreground=[("!disabled", "#ffffff")],
            background=[("active", ACCENT), ("pressed", "#0094c2")],
        )
        self.configure(background=base)

    def _load_json(self):
        """Load animations from JSON file."""
        try:
            with open(self.anim_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_json(self):
        """Save animations to JSON file."""
        with open(self.anim_file, "w", encoding="utf-8") as f:
            f.write("{" + "\n")
            items = list(self.animations.items())
            for idx, (k, v) in enumerate(items):
                f.write(f'  "{k}": ')
                json_str = json.dumps(v, separators=(",", ": "))
                f.write(json_str)
                if idx < len(items) - 1:
                    f.write(",\n")
                else:
                    f.write("\n")
            f.write("}")

    def _layout(self):
        """Layout the main GUI components."""
        main = PanedWindow(self, orient="horizontal", sashrelief="raised", bg="#1e1e1e")
        main.pack(fill=BOTH, expand=True, padx=10, pady=10)
        left = ttk.Frame(main)
        main.add(left, minsize=720)
        grid = ttk.Frame(left)
        grid.pack(fill="x", expand=False)
        for col, minsize in {
            COL_NAME: 70,
            COL_VEL: 50,
            COL_IDLE: 50,
            COL_INTV: 70,
            COL_MOVE: 60,
            COL_CFG: 60,
        }.items():
            grid.grid_columnconfigure(col, minsize=minsize)
        grid.grid_columnconfigure(COL_SCALE, weight=1)
        for sid, name in enumerate(SERVO_NAMES):
            self._servo_row(grid, sid, name)
        ctrl = ttk.Frame(left)
        ctrl.pack(fill="x", pady=(12, 0))
        ctrl.columnconfigure(0, weight=1)
        self._led_row(ctrl)
        self._preset_bar(ctrl)
        self.send_all_btn = ttk.Button(
            ctrl, text="Send ALL Config", style="Accent.TButton", command=self._send_all
        )
        self.send_all_btn.pack(pady=(4, 0))
        right = ttk.Frame(main)
        main.add(right, minsize=520)
        right.rowconfigure(0, weight=1)
        self._log_area(right).grid(row=0, column=0, sticky="nsew")

    def _servo_row(self, parent, sid, name):
        """Create a row for a servo in the GUI."""
        mn, mx = self.servo_min[sid], self.servo_max[sid]
        self.current_angles.append(mn)
        ttk.Label(parent, text=f"{sid}:{name}").grid(
            row=sid, column=COL_NAME, sticky="e", padx=(0, PX)
        )
        holder = ttk.Frame(parent)
        holder.grid(row=sid, column=COL_SCALE, sticky="ew", padx=PX)
        holder.grid_columnconfigure(0, weight=1)
        scale = ttk.Scale(holder, from_=mn, to=mx, orient=HORIZONTAL)
        scale.set(mn)
        scale.grid(row=0, column=0, sticky="ew")
        canvas = tk.Canvas(
            holder, height=BAR_HEIGHT, background="#2d2d2d", highlightthickness=0
        )
        canvas.grid(row=1, column=0, sticky="ew")

        def _entry(default, width, col):
            e = ttk.Entry(parent, width=width, justify="center")
            e.insert(0, default)
            e.grid(row=sid, column=col, padx=(0, 2))
            return e

        vel = _entry("5", 5, COL_VEL)
        idle = _entry("10", 5, COL_IDLE)
        intv = _entry("2000", 7, COL_INTV)
        ttk.Label(parent, text="vel").grid(row=sid, column=COL_VEL_LBL, sticky="w")
        ttk.Label(parent, text="idle").grid(row=sid, column=COL_IDLE_LBL, sticky="w")
        ttk.Label(parent, text="ms").grid(row=sid, column=COL_INTV_LBL, sticky="w")
        move_btn = ttk.Button(
            parent, text="Move", command=partial(self._send_move, sid, scale, vel)
        )
        move_btn.grid(row=sid, column=COL_MOVE, padx=4)
        cfg_btn = ttk.Button(
            parent,
            text="Cfg",
            command=partial(self._send_cfg_one, sid, scale, vel, idle, intv),
        )
        cfg_btn.grid(row=sid, column=COL_CFG)
        self.move_buttons.append(move_btn)
        self.cfg_buttons.append(cfg_btn)
        idx = len(self.row_vars)
        self.row_vars.append((scale, vel, idle, intv, canvas))  # Append row variables
        idle.bind("<FocusOut>", lambda _e, row=idx: self._draw_band(row))
        scale.configure(command=lambda _v, row=idx: self._draw_band(row))
        canvas.bind("<Configure>", lambda _e, row=idx: self._draw_band(row))

    def _draw_band(self, row):
        """Draw idle band, ticks, labels, and red dot for a servo row."""
        sc, _v, idle_e, _i, cv = self.row_vars[row]
        try:
            ir = int(idle_e.get())
        except ValueError:
            ir = 0
        tgt = float(sc.get())
        act = self.current_angles[row]
        mn = self.servo_min[row]
        mx = self.servo_max[row]
        span = mx - mn
        w = cv.winfo_width()
        cv.delete("all")
        if w < 4 or span == 0:
            return
        for frac in (0, 0.25, 0.5, 0.75, 1):
            x = int(frac * w)
            h = 14 if frac in (0, 1) else 8
            cv.create_line(x, 0, x, h, fill="#606060", width=1)
        lbl_y = 15
        cv.create_text(
            2, lbl_y, anchor="nw", text=str(mn), fill="#909090", font=("Segoe UI", 7)
        )
        cv.create_text(
            w - 2,
            lbl_y,
            anchor="ne",
            text=str(mx),
            fill="#909090",
            font=("Segoe UI", 7),
        )
        lo = max(mn, tgt - ir)
        hi = min(mx, tgt + ir)
        x0 = int((lo - mn) / span * w)
        x1 = int((hi - mn) / span * w)
        cv.create_rectangle(x0, 20, x1, BAR_HEIGHT, fill=BAR_COLOR, width=0)
        x_tgt = int((tgt - mn) / span * w)
        cv.create_line(x_tgt, 0, x_tgt, BAR_HEIGHT, fill="#ffffff", width=1)
        x_act = int((act - mn) / span * w)
        cv.create_oval(x_act - 4, 4, x_act + 4, 12, fill=DOT_COLOR, outline="")

    def _led_row(self, parent):
        """Create the LED control row."""
        fr = ttk.Frame(parent)
        fr.pack(fill="x")
        ttk.Label(fr, text="LED RGB").pack(side="left", padx=(0, 12))
        self.r = self._rgb(fr, "255")
        self.g = self._rgb(fr, "255")
        self.b = self._rgb(fr, "255")
        ttk.Button(fr, text="Pick", command=self._pick_color).pack(
            side="left", padx=(10, 6)
        )
        ttk.Button(fr, text="Send LED", command=self._send_led).pack(side="left")
        ttk.Button(fr, text="Send Mic LED", command=self._send_mic_led).pack(
            side="left", padx=(6, 0)
        )

    def _rgb(self, parent, default):
        """Create an RGB entry box."""
        e = ttk.Entry(parent, width=5, justify="center")
        e.insert(0, default)
        e.pack(side="left", padx=2)
        return e

    def _preset_bar(self, parent):
        """Create the preset bar."""
        fr = ttk.Frame(parent)
        fr.pack(fill="x", pady=(6, 0))
        ttk.Label(fr, text="Preset").pack(side="left", padx=(0, 8))
        self.cb = ttk.Combobox(
            fr, state="readonly", width=22, values=list(self.animations.keys())
        )
        self.cb.pack(side="left")
        self.apply_btn = ttk.Button(fr, text="Apply", command=self._apply_preset)
        self.apply_btn.pack(side="left", padx=6)
        ttk.Button(
            fr, text="Save…", style="Accent.TButton", command=self._save_preset
        ).pack(side="left")

    def _log_area(self, parent):
        """Create the log area."""
        container = ttk.Frame(parent)
        self.log = tk.Text(
            container,
            wrap="word",
            background="#121212",
            foreground="#dcdcdc",
            borderwidth=0,
            font=("Consolas", 10),
        )
        sb = ttk.Scrollbar(container, command=self.log.yview, orient="vertical")
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left", fill=BOTH, expand=True)
        sb.pack(side="right", fill=Y)
        return container

    def _save_preset(self):
        """Save the current settings as a preset."""
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
            mn, mx = self.servo_min[sid], self.servo_max[sid]
            span = mx - mn
            factor = (angle - mn) / span if span else 0.0
            factors.append(round(factor, 3))
        try:
            r, g, b = map(int, (self.r.get(), self.g.get(), self.b.get()))
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
        """Apply the selected preset."""
        if not self.limits_ready:
            return self._msg("limits not ready")
        d = self.animations.get(self.cb.get())
        if not d:
            return
        for sid, (sc, vel_e, idle_e, intv_e, _c) in enumerate(self.row_vars):
            vel_e.delete(0, END)
            vel_e.insert(0, d["velocities"][sid])
            idle_e.delete(0, END)
            idle_e.insert(0, d["idle_ranges"][sid])
            intv_e.delete(0, END)
            intv_e.insert(0, d["intervals"][sid])
            mn, mx = self.servo_min[sid], self.servo_max[sid]
            factor = max(0.0, min(1.0, d["target_factors"][sid]))
            angle = mn + factor * (mx - mn)
            sc.set(angle)
            self._draw_band(sid)
            self._msg(
                f"[DEBUG] Apply preset SID={sid} factor={factor:.3f} "
                f"angle={angle} range=({mn},{mx})"
            )
        for e, val in zip((self.r, self.g, self.b), d["color"]):
            e.delete(0, END)
            e.insert(0, val)
        self._msg("preset applied")
        self._send_all()

    def gui_to_hw_angle(self, sid, angle):
        """Convert GUI angle to hardware angle."""
        mn = self.servo_min[sid]
        mx = self.servo_max[sid]
        return int(round(max(mn, min(mx, angle))))

    def _disable_tx_buttons(self, state: bool):
        """Enable or disable all TX buttons."""
        tgt = "disabled" if state else "normal"
        for b in (
            *self.move_buttons,
            *self.cfg_buttons,
            getattr(self, "send_all_btn", None),
            getattr(self, "apply_btn", None),
        ):
            if b is not None:
                b.configure(state=tgt)

    def _send_move(self, sid, sc, vel_e):
        """Send a move command for a servo."""
        if not self.limits_ready:
            return self._msg("limits not ready")
        try:
            gui_angle = float(sc.get())
            hw_angle = self.gui_to_hw_angle(sid, gui_angle)
            velocity = int(float(vel_e.get()))
            self._msg(
                f"[DEBUG] MOVE SID={sid} gui_angle={gui_angle} "
                f"hw_angle={hw_angle} velocity={velocity}"
            )
            self.backend.send(
                f"MOVE_SERVO;ID={sid};TARGET={hw_angle};VELOCITY={velocity};"
            )
        except ValueError:
            self._msg("bad move")

    def _send_cfg_one(self, sid, sc, vel, idle, intv):
        """Send a configuration command for a single servo."""
        if not self.limits_ready:
            return self._msg("limits not ready")
        try:
            gui_angle = float(sc.get())
            hw_angle = self.gui_to_hw_angle(sid, gui_angle)
            velocity = int(float(vel.get()))
            idle_val = int(idle.get())
            intv_val = int(intv.get())
            self._msg(
                f"[DEBUG] CFG SID={sid} gui_angle={gui_angle} "
                f"hw_angle={hw_angle} velocity={velocity} "
                f"idle={idle_val} intv={intv_val}"
            )
            self.backend.send(
                f"SET_SERVO_CONFIG:{sid},{hw_angle},{velocity},{idle_val},{intv_val}"
            )
        except ValueError:
            self._msg("bad cfg")

    def _send_all(self):
        """Send all servo configurations."""
        if not self.limits_ready:
            return self._msg("limits not ready")
        chunks, debug = [], []
        for sid, (sc, vel, idle, intv, _c) in enumerate(self.row_vars):
            try:
                gui_angle = float(sc.get())
                hw_angle = self.gui_to_hw_angle(sid, gui_angle)
                velocity = int(float(vel.get()))
                idle_val = int(idle.get())
                intv_val = int(intv.get())
            except ValueError:
                return self._msg("bad bulk")
            chunks.append(f"{sid},{hw_angle},{velocity},{idle_val},{intv_val}")
            debug.append(
                f"[DEBUG] SEND SID={sid} gui_angle={gui_angle} "
                f"hw_angle={hw_angle} velocity={velocity} "
                f"idle={idle_val} intv={intv_val}"
            )
        for line in debug:
            self._msg(line)
        self.backend.send("SET_SERVO_CONFIG:" + ";".join(chunks))
        self._send_led()

    def _send_led(self):
        """Send LED color command."""
        try:
            r, g, b = map(int, (self.r.get(), self.g.get(), self.b.get()))
            r = int(r // 5)
            g = int(g // 5)
            b = int(b // 5)
        except ValueError:
            return self._msg("bad LED")
        self.backend.send(
            f"SET_LED;R={max(0, min(255, r))};G={max(0, min(255, g))};"
            f"B={max(0, min(255, b))};"
        )

    def _send_mic_led(self):
        """Send microphone LED color command."""
        try:
            r, g, b = map(int, (self.r.get(), self.g.get(), self.b.get()))
            r = int(r // 5)
            g = int(g // 5)
            b = int(b // 5)
        except ValueError:
            return self._msg("bad LED")
        self.backend.send(
            f"SET_MIC_LED;"
            f"R={max(0, min(255, r))};G={max(0, min(255, g))};"
            f"B={max(0, min(255, b))};"
        )

    def _pick_color(self):
        """Open a color picker dialog."""
        col = colorchooser.askcolor()[0]
        if col:
            for e, val in zip((self.r, self.g, self.b), map(int, col)):
                e.delete(0, END)
                e.insert(0, val)

    def _msg(self, txt):
        """Display a message in the log area."""
        self.log.configure(state="normal")
        self.log.insert(END, txt + "\n")
        self.log.configure(state="disabled")
        self.log.yview_moveto(1.0)

    def _parse_servo_config_line(self, line: str):
        """Parse a servo config line from the hardware."""
        if line.startswith("SERVO_CONFIG:"):
            chunks = line.split("SERVO_CONFIG:")[1].split(";")
            got = 0
            for chunk in filter(None, chunks):
                try:
                    sid, mn, mx, _ping = map(int, chunk.split(",")[:4])
                except ValueError:
                    continue
                if 0 <= sid < len(self.servo_min):
                    self.servo_min[sid], self.servo_max[sid] = mn, mx
                    scale = self.row_vars[sid][0]
                    scale.configure(from_=mn, to=mx)
                    self._draw_band(sid)
                    got += 1
            if got >= len(self.servo_min) and not self.limits_ready:
                self.limits_ready = True
                self._disable_tx_buttons(False)
                self._msg("[INFO] Servo limits received – controls enabled")
            return
        m = re.match(r"Servo (\d+): angle=(\-?\d+)", line)
        if m:
            sid, ang = map(int, m.groups())
            if 0 <= sid < len(self.current_angles):
                self.current_angles[sid] = ang
                self._draw_band(sid)

    def _parse_move_line(self, line: str):
        """Parse a move line from the hardware."""
        m = re.search(r"MOVE_SERVO;ID=(\d+);TARGET=(\-?\d+);", line)
        if m:
            sid, tgt = map(int, m.groups())
            if 0 <= sid < len(self.current_angles):
                self.current_angles[sid] = tgt
                self._draw_band(sid)

    def _pump(self):
        """Run event loop for processing serial queues."""
        while not self.backend.tx_q.empty():
            self._msg("→ " + self.backend.tx_q.get_nowait())
        while not self.backend.rx_q.empty():
            msg = self.backend.rx_q.get_nowait()
            self._msg("← " + msg)
            self._parse_servo_config_line(msg)
            self._parse_move_line(msg)
        self.after(50, self._pump)


def auto_port():
    """Auto-detect and return the serial port."""
    if serial is None:
        return None
    from serial.tools import list_ports  # type: ignore[import-untyped]

    for p in list_ports.comports():
        if "USB" in p.description or "CP210" in p.description:
            return p.device


def main():
    """Run the main application."""
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--port", help="Serial port (auto if omitted)")
    ap.add_argument("-b", "--baud", type=int, default=115200)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.port is None and not args.dry_run:
        args.port = auto_port() or ""
        args.dry_run = not bool(args.port)
    backend = SerialBackend("COM7", args.baud, args.dry_run)
    if not args.dry_run and not backend.open():
        sys.exit(1)
    gui = PuppetGUI(backend)
    if not args.dry_run:
        backend.send("GET_SERVO_CONFIG")
    gui.mainloop()
    backend.close()


if __name__ == "__main__":
    main()
