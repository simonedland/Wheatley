###############################################################################
# llm_tts_stream_live_table.py
# ---------------------------------------------------------------------------
# GPT-4o → ElevenLabs with one-row-per-sentence status table
# ─ Fix: user prompt is printed once and never cleared.
###############################################################################
import asyncio, io, logging, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

import openai, requests, yaml
from pydub import AudioSegment
from pydub.playback import play

# ───────── SETTINGS ─────────────────────────────────────────────────────────
VOICE_ID, MODEL_ID, OUTPUT_FORMAT = "4Jtuv4wBvd95o1hzNloV", "eleven_flash_v2_5", "mp3_22050_32"
MAX_TTS_WORKERS, QUEUE_MAXSIZE = 4, 100
SENTENCE_RE   = re.compile(r'(?<=[.!?])\s+(?=[A-Za-z])')  # splits but skips “1.”
TOKEN_FLUSH_MS = 200

# ───────── OPTIONAL RICH UI ────────────────────────────────────────────────
try:
    from rich.live import Live
    from rich.table import Table
    from rich.console import Console
    from rich.text import Text
    console = Console()
    USE_RICH = True
except ImportError:
    USE_RICH = False
    print("Rich not installed → plain output\n")

COLORS = dict(build="red", done="orange", tts="yellow",
              ready="green", play="bright_blue", end="magenta")

def make_table(rows: List[Dict]) -> "Table":
    t = Table(show_header=True, expand=True)
    t.add_column("#", width=3)
    t.add_column("Sentence", overflow="fold")
    t.add_column("Status", width=10)
    for r in rows:
        t.add_row(str(r["idx"]),
                  r["text"],
                  Text(r["status"], style=COLORS[r["phase"]]))
    return t

def update_table():
    if USE_RICH:
        live.update(make_table(rows), refresh=True)

# ───────── LOGGER (quiet 3rd-party) ─────────────────────────────────────────
for lib in ("openai", "urllib3", "httpx"):  # silence debug noise
    logging.getLogger(lib).setLevel(logging.INFO)

# ───────── API KEYS ─────────────────────────────────────────────────────────
cfg = yaml.safe_load(open("Wheatley/config/config.yaml", encoding="utf-8"))
openai.api_key = cfg["secrets"]["openai_api_key"]
XI             = cfg["secrets"]["elevenlabs_api_key"]
API            = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
HEAD           = {"xi-api-key": XI, "Content-Type": "application/json"}

# ───────── GLOBAL SENTENCE STATE ───────────────────────────────────────────
rows: List[Dict] = []               # one dict per sentence row

def add_row(idx, text=""):
    rows.append(dict(idx=idx, text=text, phase="build", status="building"))
    update_table()

def set_phase(idx, phase, text=None):
    r = rows[idx]
    if text:  r["text"] = text
    r["phase"] = phase
    r["status"] = dict(build="building", done="complete", tts="→ TTS",
                       ready="ready", play="playing", end="played")[phase]
    update_table()

# ───────── BLOCKING HELPERS (thread pool) ───────────────────────────────────
def http_tts(txt, prev, nxt, idx):
    set_phase(idx, "tts")
    r = requests.post(API, params={"output_format":OUTPUT_FORMAT,"optimize_streaming_latency":3},
                      headers=HEAD,
                      json={"text":txt,"model_id":MODEL_ID,
                            "previous_text":prev or None,
                            "next_text":nxt or None},
                      timeout=60)
    r.raise_for_status()
    set_phase(idx, "ready")
    return r.content

def play_mp3(data, idx):
    set_phase(idx, "play")
    seg = AudioSegment.from_file(io.BytesIO(data), format="mp3")
    play(seg)
    set_phase(idx, "end")

# ───────── 1) GPT TOKEN THREAD ──────────────────────────────────────────────
def gpt_thread(prompt, q, loop):
    buf, tok_buf, last = "", "", time.time()
    i = 0
    for ch in openai.chat.completions.create(model="gpt-4o", stream=True,
            messages=[{"role":"user","content":prompt}]):
        tok = getattr(ch.choices[0].delta, "content", "")
        if not tok: continue
        buf += tok; tok_buf += tok

        if not USE_RICH and time.time()-last > TOKEN_FLUSH_MS/1000:
            print(tok_buf, end="", flush=True); tok_buf=""; last=time.time()

        while (m:=SENTENCE_RE.search(buf)):
            sent, buf = buf[:m.end()].strip(), buf[m.end():]
            if re.fullmatch(r'\d+\.', sent):   # glue numeric bullet
                buf = f"{sent} {buf}"; break
            add_row(i, sent)
            asyncio.run_coroutine_threadsafe(q.put(sent), loop)
            set_phase(i, "done")
            i += 1

    if buf.strip():
        add_row(i, buf.strip())
        asyncio.run_coroutine_threadsafe(q.put(buf.strip()), loop)
        set_phase(i, "done")
    asyncio.run_coroutine_threadsafe(q.put(None), loop)

# ───────── 2) SENTENCE → TTS DISPATCH ───────────────────────────────────────
async def tts_dispatch(sq, aq, pool):
    loop = asyncio.get_running_loop()
    idx, prev = 0, ""
    curr = await sq.get(); nxt = await sq.get()

    async def launch(i, cur, prv, nx):
        fut = loop.run_in_executor(pool, http_tts, cur, prv, nx, i)
        await aq.put((i, await asyncio.wrap_future(fut)))

    tasks=[]
    while True:
        tasks.append(asyncio.create_task(
            launch(idx, curr, prev, "" if nxt is None else nxt)))
        if nxt is None: break
        prev, curr, idx, nxt = curr, nxt, idx+1, await sq.get()
    await asyncio.gather(*tasks)
    await aq.put((-1,b""))

# ───────── 3) PLAYBACK SEQUENCER ────────────────────────────────────────────
async def sequencer(aq):
    loop, heap, expect = asyncio.get_running_loop(), {}, 0
    while True:
        idx, clip = await aq.get()
        if idx == -1: break
        heap[idx] = clip
        while expect in heap:
            await loop.run_in_executor(None, play_mp3, heap.pop(expect), expect)
            expect += 1

# ───────── ORCHESTRATOR ─────────────────────────────────────────────────────
async def chat(prompt):
    sq, aq = asyncio.Queue(QUEUE_MAXSIZE), asyncio.Queue(QUEUE_MAXSIZE)
    threading.Thread(target=gpt_thread,
                     args=(prompt, sq, asyncio.get_running_loop()),
                     daemon=True).start()
    with ThreadPoolExecutor(MAX_TTS_WORKERS) as pool:
        await asyncio.gather(tts_dispatch(sq, aq, pool), sequencer(aq))

# ───────── CLI ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        if USE_RICH:
            prompt = console.input("[bold green]Prompt » [/bold green]")
            console.print(f"[bold]You:[/bold] {prompt}\n")     # stays above table
            live = Live(console=console, refresh_per_second=10, vertical_overflow="visible")
            with live:
                asyncio.run(chat(prompt))
        else:
            asyncio.run(chat(input("Prompt » ")))
    except KeyboardInterrupt:
        sys.exit()
