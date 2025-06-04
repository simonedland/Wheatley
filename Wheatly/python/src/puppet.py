#!/usr/bin/env python3
"""
servo_puppet.py – modern Tk/ttk GUI to puppet an OpenRB-150 / Core-2 stack
rev 9 clean  •  2025-06-04
"""

import argparse, json, os, queue, shutil, sys, tempfile, threading, time
import tkinter as tk
from functools import partial
from tkinter import (
    BOTH, DISABLED, END, HORIZONTAL, NORMAL, Y,
    Tk, PanedWindow, colorchooser, simpledialog, TclError
)
from tkinter import ttk

# ───────── optional serial (needed only without --dry-run) ──────────────
try:
    import serial
except ImportError:
    serial = None

# ───────── constants ────────────────────────────────────────────────────
SERVO_NAMES = ("lens", "eyelid1", "eyelid2", "eyeX", "eyeY", "handle1", "handle2")
DEFAULT_MIN = [-720, 30, 30, 45, 40, 0, 0]
DEFAULT_MAX = [720, 60, 60, 135, 140, 170, 170]
ACCENT      = "#00c3ff"          # highlight colour
PX          = 6                  # horizontal padding between grid columns

# column index helpers for servo grid
COL_NAME, COL_SCALE, COL_VEL, COL_VEL_LBL, COL_IDLE, COL_IDLE_LBL, \
COL_INTV, COL_INTV_LBL, COL_MOVE, COL_CFG = range(10)


# ╔════════════════ Serial backend ═══════════════════════════════════════╗
class SerialBackend:
    def __init__(self, port: str | None, baud: int, dry_run: bool):
        self.port, self.baud, self.dry = port, baud, dry_run
        self.ser = None
        self.rx_q, self.tx_q = queue.Queue(), queue.Queue()
        self._stop = threading.Event()

    def open(self) -> bool:
        if self.dry:
            print("[DRY-RUN] serial disabled")
            return True
        if serial is None:
            print("pyserial missing – pip install pyserial")
            return False
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
        except serial.SerialException as e:
            print(f"[ERROR] {e}")
            return False
        threading.Thread(target=self._reader, daemon=True).start()
        return True

    def _reader(self):
        while not self._stop.is_set():
            if self.ser and self.ser.in_waiting:
                try:
                    line = self.ser.readline().decode(errors="ignore").strip()
                    if line:
                        print(f"[RX] {line}")
                        self.rx_q.put(line)
                except serial.SerialException:
                    break
            time.sleep(0.02)

    def send(self, txt: str):
        if not txt.endswith("\n"):
            txt += "\n"
        print(f"[TX] {txt.strip()}")
        self.tx_q.put(txt.rstrip())
        if not self.dry and self.ser and self.ser.is_open:
            self.ser.write(txt.encode())

    def close(self):
        self._stop.set()
        if self.ser and self.ser.is_open:
            self.ser.close()


# ╔════════════════ GUI class ════════════════════════════════════════════╗
class PuppetGUI(Tk):
    def __init__(self, backend: SerialBackend):
        super().__init__()
        self.backend = backend
        self.title("Servo Puppet")
        self.geometry("1280x860")

        # animation preset bookkeeping
        self.anim_file = "animations.json"
        self.animations: dict[str, dict] = self._load_anims()

        self.row_vars = []  # list of tuples (Scale, velEnt, idleEnt, intvEnt)
        self._init_theme()
        self._build_layout()
        self.after(50, self._pump_queues)

    # ─── theme ----------------------------------------------------------
    def _init_theme(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except TclError:
            pass
        base = "#1e1e1e"
        style.configure(
            ".",
            background=base,
            foreground="#e8e8e8",
            font=("Segoe UI", 10),
        )
        style.configure("TFrame", background=base)
        style.configure("TLabel", background=base)
        style.configure(
            "TEntry",
            fieldbackground="#2d2d2d",
            foreground="#e8e8e8",
            borderwidth=0,
        )
        style.configure(
            "Horizontal.TScale",
            troughcolor="#2d2d2d",
            sliderthickness=18,
            background=ACCENT,
        )
        style.map(
            "TButton",
            foreground=[("!disabled", "#ffffff")],
            background=[("active", ACCENT), ("pressed", "#0094c2")],
        )
        style.configure("TScrollbar", troughcolor="#2d2d2d", arrowcolor="#888")
        self.configure(background=base)

    # ─── JSON helpers ---------------------------------------------------
    def _load_anims(self) -> dict:
        if os.path.isfile(self.anim_file):
            try:
                with open(self.anim_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_anims(self):
        tmp = tempfile.NamedTemporaryFile(delete=False, mode="w",
                                          encoding="utf-8")
        json.dump(self.animations, tmp, indent=2)
        tmp.close()
        shutil.move(tmp.name, self.anim_file)

    # ─── layout ---------------------------------------------------------
    def _build_layout(self):
        paned = PanedWindow(self, orient="horizontal", sashrelief="raised",
                            bg="#1e1e1e")
        paned.pack(fill=BOTH, expand=True, padx=10, pady=10)

        left, right = ttk.Frame(paned), ttk.Frame(paned)
        paned.add(left, minsize=720)
        paned.add(right, minsize=520)

        # servo grid
        grid = ttk.Frame(left); grid.pack(fill=BOTH, expand=True)
        for r, (sid, name) in enumerate(zip(range(7), SERVO_NAMES)):
            self._add_servo_row(grid, r, sid, name)

        # LED row
        self._add_led_row(left)

        # preset bar
        self._add_preset_bar(left)

        ttk.Button(left, text="Send ALL Config", style="Accent.TButton",
                   command=self._send_all_cfg).pack(pady=12)

        # log pane
        self._build_log(right)

    def _build_log(self, parent):
        self.log = tk.Text(
            parent,
            wrap="word",
            background="#121212",
            foreground="#dcdcdc",
            borderwidth=0,
            font=("Consolas", 10),
        )
        sb = ttk.Scrollbar(parent, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left", fill=BOTH, expand=True)
        sb.pack(side="right", fill=Y)

    # servo row ----------------------------------------------------------
    def _add_servo_row(self, parent, r: int, sid: int, name: str):
        for c in range(10):
            parent.grid_columnconfigure(c, weight=0)
        parent.grid_columnconfigure(COL_SCALE, weight=1)

        ttk.Label(parent, text=f"{sid}:{name}").grid(
            row=r, column=COL_NAME, sticky="w", padx=(0, PX)
        )

        scale = ttk.Scale(
            parent,
            from_=DEFAULT_MIN[sid],
            to=DEFAULT_MAX[sid],
            orient=HORIZONTAL,
            length=340,
        )
        scale.set(0)
        scale.grid(row=r, column=COL_SCALE, sticky="ew", padx=PX)

        # helper to spawn numeric entry
        def make_entry(default_value: str, width: int):
            ent = ttk.Entry(parent, width=width, justify="center")
            ent.insert(0, default_value)
            return ent

        vel_ent = make_entry("5", 4)
        vel_ent.grid(row=r, column=COL_VEL, padx=(PX, 2))
        ttk.Label(parent, text="vel").grid(
            row=r, column=COL_VEL_LBL, padx=(0, PX)
        )

        idle_ent = make_entry("10", 4)
        idle_ent.grid(row=r, column=COL_IDLE, padx=(0, 2))
        ttk.Label(parent, text="idle").grid(
            row=r, column=COL_IDLE_LBL, padx=(0, PX)
        )

        intv_ent = make_entry("2000", 6)
        intv_ent.grid(row=r, column=COL_INTV, padx=(0, 2))
        ttk.Label(parent, text="ms").grid(
            row=r, column=COL_INTV_LBL, padx=(0, PX)
        )

        ttk.Button(
            parent,
            text="Move",
            command=partial(self._send_move, sid, scale, vel_ent),
        ).grid(row=r, column=COL_MOVE, padx=4)

        ttk.Button(
            parent,
            text="Cfg",
            command=partial(
                self._send_cfg_one, sid, scale, vel_ent, idle_ent, intv_ent
            ),
        ).grid(row=r, column=COL_CFG)

        self.row_vars.append((scale, vel_ent, idle_ent, intv_ent))

    # LED row ------------------------------------------------------------
    def _add_led_row(self, parent):
        fr = ttk.Frame(parent, padding=(0, 10))
        fr.pack(fill="x")
        ttk.Label(fr, text="LED RGB").pack(side="left", padx=(0, 12))
        self.r = self._rgb_entry(fr, "255")
        self.g = self._rgb_entry(fr, "255")
        self.b = self._rgb_entry(fr, "255")
        ttk.Button(fr, text="Pick", command=self._pick_color
                   ).pack(side="left", padx=(10, 6))
        ttk.Button(fr, text="Send LED", command=self._send_led
                   ).pack(side="left")

    def _rgb_entry(self, parent, default):
        e = ttk.Entry(parent, width=5, justify="center")
        e.insert(0, default); e.pack(side="left", padx=2)
        return e

    # preset bar ---------------------------------------------------------
    def _add_preset_bar(self, parent):
        fr = ttk.Frame(parent, padding=(0, 10)); fr.pack(fill="x")
        ttk.Label(fr, text="Preset").pack(side="left", padx=(0, 8))
        self.preset_cb = ttk.Combobox(
            fr, values=list(self.animations.keys()), state="readonly", width=22
        )
        self.preset_cb.pack(side="left")
        ttk.Button(fr, text="Apply", command=self._apply_preset
                   ).pack(side="left", padx=6)
        ttk.Button(fr, text="Save…", command=self._save_preset_dialog,
                   style="Accent.TButton").pack(side="left")

    # ── preset save / load ---------------------------------------------
    def _save_preset_dialog(self):
        name = simpledialog.askstring(
            "Save animation", "Preset name:", parent=self
        )
        if not name:
            return

        vel, tf, ir, itv = [], [], [], []
        for sid, (scale, v_ent, id_ent, in_ent) in enumerate(self.row_vars):
            try:
                ang = int(scale.get())
                vel_val = int(float(v_ent.get()))
                ir_val = int(id_ent.get())
                it_val = int(in_ent.get())
            except ValueError:
                return self._log("[GUI] save: bad number")

            mn, mx = DEFAULT_MIN[sid], DEFAULT_MAX[sid]
            tf_val = (ang - mn) / (mx - mn) if mx != mn else 0
            vel.append(vel_val)
            tf.append(round(tf_val, 3))
            ir.append(ir_val)
            itv.append(it_val)

        try:
            r = int(self.r.get()); g = int(self.g.get()); b = int(self.b.get())
        except ValueError:
            return self._log("[GUI] save: LED bad number")

        self.animations[name] = {
            "velocities": vel,
            "target_factors": tf,
            "idle_ranges": ir,
            "intervals": itv,
            "color": [r, g, b],
        }
        self._save_anims()
        self.preset_cb["values"] = list(self.animations.keys())
        self.preset_cb.set(name)
        self._log(f"[GUI] preset '{name}' saved")

    def _apply_preset(self):
        name = self.preset_cb.get()
        data = self.animations.get(name)
        if not data:
            return
        if len(data["velocities"]) != len(self.row_vars):
            return self._log("[GUI] preset mismatch")

        for sid, (scale, v_ent, id_ent, in_ent) in enumerate(self.row_vars):
            v_ent.delete(0, END); v_ent.insert(0, str(data["velocities"][sid]))
            id_ent.delete(0, END); id_ent.insert(0, str(data["idle_ranges"][sid]))
            in_ent.delete(0, END); in_ent.insert(0, str(data["intervals"][sid]))
            mn, mx = DEFAULT_MIN[sid], DEFAULT_MAX[sid]
            scale.set(mn + data["target_factors"][sid] * (mx - mn))

        r, g, b = data["color"]
        for ent, val in zip((self.r, self.g, self.b), (r, g, b)):
            ent.delete(0, END); ent.insert(0, str(val))

        self._log(f"[GUI] preset '{name}' loaded")
        self._send_all_cfg()
        self._send_led()

    # ── command helpers -------------------------------------------------
    def _send_move(self, sid, scale, vel_ent):
        try:
            tgt = int(scale.get()); v = int(float(vel_ent.get()))
        except ValueError:
            return self._log("[GUI] Move: bad number")
        self.backend.send(f"MOVE_SERVO;ID={sid};TARGET={tgt};VELOCITY={v};")

    def _send_cfg_one(self, sid, scale, vel_ent, idle_ent, intv_ent):
        try:
            tgt = int(scale.get()); v = int(float(vel_ent.get()))
            ir = int(idle_ent.get()); itv = int(intv_ent.get())
        except ValueError:
            return self._log("[GUI] Cfg: bad number")
        self.backend.send(f"SET_SERVO_CONFIG:{sid},{tgt},{v},{ir},{itv}")

    def _send_all_cfg(self):
        chunks = []
        for sid, (scale, v_ent, id_ent, in_ent) in enumerate(self.row_vars):
            try:
                chunks.append(
                    f"{sid},{int(scale.get())},{int(float(v_ent.get()))},"
                    f"{int(id_ent.get())},{int(in_ent.get())}"
                )
            except ValueError:
                return self._log("[GUI] bulk: bad number")
        self.backend.send("SET_SERVO_CONFIG:" + ";".join(chunks))

    def _send_led(self):
        try:
            r = int(self.r.get()); g = int(self.g.get()); b = int(self.b.get())
        except ValueError:
            return self._log("[GUI] LED: bad number")
        r, g, b = (max(0, min(255, v)) for v in (r, g, b))
        self.backend.send(f"SET_LED;R={r};G={g};B={b};")

    def _pick_color(self):
        col = colorchooser.askcolor(title="Pick LED colour")[0]
        if col:
            for ent, val in zip((self.r, self.g, self.b), map(int, col)):
                ent.delete(0, END); ent.insert(0, str(val))

    # ── logging & queues -----------------------------------------------
    def _log(self, msg: str):
        self.log.configure(state=NORMAL)
        self.log.insert(END, msg + "\n")
        self.log.configure(state=DISABLED)
        self.log.yview_moveto(1.0)

    def _pump_queues(self):
        while not self.backend.tx_q.empty():
            self._log("→ " + self.backend.tx_q.get_nowait())
        while not self.backend.rx_q.empty():
            self._log("← " + self.backend.rx_q.get_nowait())
        self.after(50, self._pump_queues)


# ╔════════ util: auto serial port ═══════════════════════════════════════╗
def auto_port():
    if serial is None:
        return None
    from serial.tools import list_ports
    for p in list_ports.comports():
        if "USB" in p.description or "CP210" in p.description:
            return p.device
    return None


# ╔══════════════════════════ main ═══════════════════════════════════════╗
def main():
    ap = argparse.ArgumentParser(description="Modern Tk Servo Puppet GUI")
    ap.add_argument("-p", "--port")
    ap.add_argument("-b", "--baud", type=int, default=115200)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.port is None and not args.dry_run:
        auto = auto_port()
        if auto:
            args.port = auto
            print(f"[INFO] auto-detected {auto}")
        else:
            print("[WARN] no port found – dry-run")
            args.dry_run = True

    backend = SerialBackend(args.port, args.baud, args.dry_run)
    if not args.dry_run and not backend.open():
        sys.exit(1)

    ui = PuppetGUI(backend)
    if not args.dry_run:
        backend.send("GET_SERVO_CONFIG")
    ui.mainloop()
    backend.close()


if __name__ == "__main__":
    main()
