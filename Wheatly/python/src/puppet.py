#!/usr/bin/env python3
"""
servo_puppet.py – GUI for OpenRB-150 / Core-2
rev 11 · 2025-06-04
• dark theme, animation presets, LED picker
• NEW: green idle-range bar under every slider
"""

import argparse, json, os, queue, shutil, sys, tempfile, threading, time
import tkinter as tk
from functools import partial
from tkinter import (
    BOTH, DISABLED, END, HORIZONTAL, NORMAL, Y,
    Tk, PanedWindow, colorchooser, simpledialog, TclError
)
from tkinter import ttk

# ───────────────── optional serial ─────────────────────────────────────
try:
    import serial
except ImportError:
    serial = None

# ───────────────── constants ───────────────────────────────────────────
SERVO_NAMES = ("lens","eyelid1","eyelid2","eyeX","eyeY","handle1","handle2")
DEFAULT_MIN = [-720,30,30,45,40,0,0]
DEFAULT_MAX = [720,60,60,135,140,170,170]
ACCENT      = "#00c3ff"
BAR_COLOR   = "#00c851"     # green idle band
PX          = 6

COL_NAME, COL_SCALE, COL_VEL, COL_VEL_LBL, COL_IDLE, COL_IDLE_LBL, \
COL_INTV, COL_INTV_LBL, COL_MOVE, COL_CFG = range(10)


# ╔════════════ Serial backend ════════════╗
class SerialBackend:
    def __init__(self, port, baud, dry):
        self.port, self.baud, self.dry = port, baud, dry
        self.ser = None
        self.rx_q = queue.Queue(); self.tx_q = queue.Queue()
        self._stop = threading.Event()

    def open(self):
        if self.dry: return True
        if serial is None: return False
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
        except serial.SerialException as e:
            print(e); return False
        threading.Thread(target=self._reader, daemon=True).start(); return True

    def _reader(self):
        while not self._stop.is_set():
            if self.ser and self.ser.in_waiting:
                try:
                    self.rx_q.put(self.ser.readline().decode(errors="ignore").strip())
                except serial.SerialException: break
            time.sleep(0.02)

    def send(self, txt):
        if not txt.endswith("\n"): txt += "\n"
        self.tx_q.put(txt.rstrip())
        if not self.dry and self.ser and self.ser.is_open:
            self.ser.write(txt.encode())

    def close(self):
        self._stop.set();  self.ser and self.ser.close()


# ╔════════════ GUI class ═════════════════╗
class PuppetGUI(Tk):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.title("Servo Puppet"); self.geometry("1280x860")

        self.anim_file = "animations.json"
        self.animations = self._load_json()

        # row tuple: (scale, velEnt, idleEnt, intvEnt, barCanvas)
        self.row_vars = []
        self._theme(); self._layout()
        self.after(50, self._pump)

    # ── theme -----------------------------------------------------------
    def _theme(self):
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except TclError: pass
        base="#1e1e1e"
        style.configure(".", background=base, foreground="#e8e8e8",
                        font=("Segoe UI",10))
        style.configure("TFrame", background=base)
        style.configure("TLabel", background=base)
        style.configure("TEntry", fieldbackground="#2d2d2d",
                        foreground="#e8e8e8", borderwidth=0)
        style.configure("Horizontal.TScale", troughcolor="#2d2d2d",
                        sliderthickness=18, background=ACCENT)
        style.map("TButton",
                  foreground=[("!disabled","#fff")],
                  background=[("active",ACCENT),("pressed","#0094c2")])
        style.configure("TScrollbar", troughcolor="#2d2d2d", arrowcolor="#888")
        self.configure(background=base)

    # ── JSON helpers ----------------------------------------------------
    def _load_json(self):
        if os.path.isfile(self.anim_file):
            try: return json.load(open(self.anim_file,"r",encoding="utf-8"))
            except Exception: pass
        return {}

    def _save_json(self): json.dump(self.animations,
                                    open(self.anim_file,"w",encoding="utf-8"),
                                    indent=2)

    # ── layout ----------------------------------------------------------
    def _layout(self):
        pan=PanedWindow(self,orient="horizontal",sashrelief="raised",bg="#1e1e1e")
        pan.pack(fill=BOTH,expand=True,padx=10,pady=10)
        left,right=ttk.Frame(pan),ttk.Frame(pan)
        pan.add(left,minsize=720); pan.add(right,minsize=520)

        grid=ttk.Frame(left); grid.pack(fill=BOTH,expand=True)
        for r,(sid,name) in enumerate(zip(range(7),SERVO_NAMES)):
            self._servo_row(grid,r,sid,name)

        self._led_row(left); self._preset_bar(left)
        ttk.Button(left,text="Send ALL Config",style="Accent.TButton",
                   command=self._send_all).pack(pady=12)
        self._log_area(right)

    # ── servo row -------------------------------------------------------
    def _servo_row(self,parent,r,sid,name):
        for c in range(10): parent.grid_columnconfigure(c,weight=0)
        parent.grid_columnconfigure(COL_SCALE,weight=1)
        ttk.Label(parent,text=f"{sid}:{name}").grid(row=r,column=COL_NAME,
                                                    sticky="w",padx=(0,PX))

        idx=len(self.row_vars)

        # frame: slider on top, green bar below
        holder=ttk.Frame(parent); holder.grid(row=r,column=COL_SCALE,
                                              sticky="ew",padx=PX)
        holder.grid_columnconfigure(0,weight=1)

        scale=ttk.Scale(holder,from_=DEFAULT_MIN[sid],to=DEFAULT_MAX[sid],
                        orient=HORIZONTAL)
        scale.grid(row=0,column=0,sticky="ew")
        bar=tk.Canvas(holder,height=4,background="#2d2d2d",highlightthickness=0)
        bar.grid(row=1,column=0,sticky="ew")

        # numeric helper
        def e(defv,w):
            ent=ttk.Entry(parent,width=w,justify="center")
            ent.insert(0,defv); return ent
        vel=e("5",4); vel.grid(row=r,column=COL_VEL,padx=(PX,2))
        ttk.Label(parent,text="vel").grid(row=r,column=COL_VEL_LBL,padx=(0,PX))
        idle=e("10",4); idle.grid(row=r,column=COL_IDLE,padx=(0,2))
        ttk.Label(parent,text="idle").grid(row=r,column=COL_IDLE_LBL,padx=(0,PX))
        intv=e("2000",6); intv.grid(row=r,column=COL_INTV,padx=(0,2))
        ttk.Label(parent,text="ms").grid(row=r,column=COL_INTV_LBL,padx=(0,PX))

        ttk.Button(parent,text="Move",
                   command=partial(self._send_move,sid,scale,vel)
                  ).grid(row=r,column=COL_MOVE,padx=4)
        ttk.Button(parent,text="Cfg",
                   command=partial(self._send_cfg_one,sid,scale,vel,idle,intv)
                  ).grid(row=r,column=COL_CFG)

        self.row_vars.append((scale,vel,idle,intv,bar))
        idle.bind("<FocusOut>",lambda e,row=idx:self._draw_band(row))
        scale.configure(command=lambda _=None,row=idx:self._draw_band(row))
        bar.bind("<Configure>",lambda e,row=idx:self._draw_band(row))

    # draw green idle band ----------------------------------------------
    def _draw_band(self,row):
        if row>=len(self.row_vars): return
        sc,_v,idle,_i,cvs=self.row_vars[row]
        try: ir=int(idle.get())
        except ValueError: ir=0
        cur=float(sc.get()); mn,mx=DEFAULT_MIN[row],DEFAULT_MAX[row]
        lo=max(mn,cur-ir); hi=min(mx,cur+ir)
        w=cvs.winfo_width(); cvs.delete("band")
        if w<2 or mx==mn: return
        x0=int((lo-mn)/(mx-mn)*w); x1=int((hi-mn)/(mx-mn)*w)
        cvs.create_rectangle(x0,0,x1,4,fill=BAR_COLOR,width=0,tags="band")

    # LED row ------------------------------------------------------------
    def _led_row(self,parent):
        fr=ttk.Frame(parent,padding=(0,10)); fr.pack(fill="x")
        ttk.Label(fr,text="LED RGB").pack(side="left",padx=(0,12))
        self.r=self._rgb(fr,"255"); self.g=self._rgb(fr,"255"); self.b=self._rgb(fr,"255")
        ttk.Button(fr,text="Pick",command=self._pick).pack(side="left",padx=(10,6))
        ttk.Button(fr,text="Send LED",command=self._send_led).pack(side="left")

    def _rgb(self,parent,defv):
        ent=ttk.Entry(parent,width=5,justify="center")
        ent.insert(0,defv); ent.pack(side="left",padx=2); return ent

    # preset bar ---------------------------------------------------------
    def _preset_bar(self,parent):
        fr=ttk.Frame(parent,padding=(0,10)); fr.pack(fill="x")
        ttk.Label(fr,text="Preset").pack(side="left",padx=(0,8))
        self.cb=ttk.Combobox(fr,state="readonly",width=22,
                             values=list(self.animations.keys()))
        self.cb.pack(side="left")
        ttk.Button(fr,text="Apply",command=self._apply).pack(side="left",padx=6)
        ttk.Button(fr,text="Save…",style="Accent.TButton",
                   command=self._save).pack(side="left")

    # log ---------------------------------------------------------------
    def _log_area(self,parent):
        self.log=tk.Text(parent,wrap="word",background="#121212",
                         foreground="#dcdcdc",borderwidth=0,font=("Consolas",10))
        sb=ttk.Scrollbar(parent,command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left",fill=BOTH,expand=True); sb.pack(side="right",fill=Y)

    # preset save/load ---------------------------------------------------
    def _save(self):
        name=simpledialog.askstring("Save animation","Preset name:",parent=self)
        if not name: return
        v,t,idr,itv=[],[],[],[]
        for sid,(sc,vel,idle,intv,_b) in enumerate(self.row_vars):
            try:
                a=int(sc.get()); v.append(int(float(vel.get())))
                idr.append(int(idle.get())); itv.append(int(intv.get()))
            except ValueError: return self._msg("bad number")
            mn,mx=DEFAULT_MIN[sid],DEFAULT_MAX[sid]
            t.append(round((a-mn)/(mx-mn) if mx!=mn else 0,3))
        try: r,g,b=(int(self.r.get()),int(self.g.get()),int(self.b.get()))
        except ValueError: return self._msg("bad LED")
        self.animations[name]={"velocities":v,"target_factors":t,
                               "idle_ranges":idr,"intervals":itv,"color":[r,g,b]}
        self._save_json(); self.cb["values"]=list(self.animations.keys()); self.cb.set(name)
        self._msg(f"preset '{name}' saved")

    def _apply(self):
        name=self.cb.get(); d=self.animations.get(name)
        if not d: return
        for sid,(sc,vel,idle,intv,_b) in enumerate(self.row_vars):
            vel.delete(0,END); vel.insert(0,str(d["velocities"][sid]))
            idle.delete(0,END); idle.insert(0,str(d["idle_ranges"][sid]))
            intv.delete(0,END); intv.insert(0,str(d["intervals"][sid]))
            mn,mx=DEFAULT_MIN[sid],DEFAULT_MAX[sid]
            sc.set(mn+d["target_factors"][sid]*(mx-mn)); self._draw_band(sid)
        r,g,b=d["color"]
        for ent,val in zip((self.r,self.g,self.b),(r,g,b)):
            ent.delete(0,END); ent.insert(0,str(val))
        self._msg(f"preset '{name}' loaded")
        self._send_all(); self._send_led()

    # commands -----------------------------------------------------------
    def _send_move(self,sid,sc,vel_ent):
        try: self.backend.send(f"MOVE_SERVO;ID={sid};TARGET={int(sc.get())};VELOCITY={int(float(vel_ent.get()))};")
        except ValueError: self._msg("bad move")

    def _send_cfg_one(self,sid,sc,vel,idle,intv):
        try:
            self.backend.send(f"SET_SERVO_CONFIG:{sid},{int(sc.get())},{int(float(vel.get()))},{int(idle.get())},{int(intv.get())}")
        except ValueError: self._msg("bad cfg")

    def _send_all(self):
        chunks=[]
        for sid,(sc,vel,idle,intv,_b) in enumerate(self.row_vars):
            try:
                chunks.append(f"{sid},{int(sc.get())},{int(float(vel.get()))},{int(idle.get())},{int(intv.get())}")
            except ValueError: return self._msg("bad bulk")
        self.backend.send("SET_SERVO_CONFIG:"+ ";".join(chunks))
        self._send_led()

    def _send_led(self):
        try: r,g,b=(int(self.r.get()),int(self.g.get()),int(self.b.get()))
        except ValueError: return self._msg("bad LED")
        r,g,b=(max(0,min(255,v)) for v in (r,g,b))
        self.backend.send(f"SET_LED;R={r};G={g};B={b};")

    # utilities ----------------------------------------------------------
    def _pick(self):
        col=colorchooser.askcolor()[0]
        if col:
            for e,val in zip((self.r,self.g,self.b),map(int,col)):
                e.delete(0,END); e.insert(0,str(val))

    def _msg(self,m): self.log.configure(state=NORMAL); self.log.insert(END,m+"\n")
    def _pump(self):
        while not self.backend.tx_q.empty(): self._msg("→ "+self.backend.tx_q.get_nowait())
        while not self.backend.rx_q.empty(): self._msg("← "+self.backend.rx_q.get_nowait())
        self.after(50,self._pump)


# ── auto port -----------------------------------------------------------
def auto_port():
    if serial is None: return None
    from serial.tools import list_ports
    for p in list_ports.comports():
        if "USB" in p.description or "CP210" in p.description: return p.device

# ── main ----------------------------------------------------------------
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("-p","--port"); ap.add_argument("-b","--baud",type=int,default=115200)
    ap.add_argument("--dry-run",action="store_true"); args=ap.parse_args()

    if args.port is None and not args.dry_run:
        args.port=auto_port()
        if args.port: print("auto port:",args.port)
        else: args.dry_run=True

    backend=SerialBackend(args.port,args.baud,args.dry_run)
    if not args.dry_run and not backend.open(): sys.exit(1)

    gui=PuppetGUI(backend)
    if not args.dry_run: backend.send("GET_SERVO_CONFIG")
    gui.mainloop(); backend.close()

if __name__=="__main__":
    main()
