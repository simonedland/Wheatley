###############################################################################
# llm_tts_stream_live_table.py  —  concurrent-workers edition
###############################################################################
import asyncio
import io
import logging
import random
import re
import sys
import threading
import time
import textwrap
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

import openai
import requests
import yaml
from pydub import AudioSegment
from pydub.playback import play

# ───────── USER SETTINGS ────────────────────────────────────────────────────
VOICE_ID = "4Jtuv4wBvd95o1hzNloV"
MODEL_ID = "eleven_flash_v2_5"
OUTPUT_FORMAT = "mp3_22050_32"

MAX_TTS_WORKERS = 2
QUEUE_MAXSIZE = 100
TOKEN_FLUSH_MS = 200
MAX_ATTEMPTS = 6

PUNCT_RE = re.compile(r'[.!?]\s+')
ABBREVS = {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st"}

# ───────── OPTIONAL RICH UI ────────────────────────────────────────────────
try:
    from rich.live import Live
    from rich.table import Table
    from rich.console import Console
    from rich.text import Text
    console, USE_RICH = Console(), True
except ImportError:
    USE_RICH = False
    print("Rich not installed → plain output\n")

COL = dict(
    build="red",
    tts="yellow",
    done="orange",
    retry="yellow",
    ready="green",
    play="bright_blue",
    end="magenta",
    err="bright_red"
)


def render(rows: List[Dict]):
    if not USE_RICH:
        return
    tbl = Table(show_header=True, expand=True)
    tbl.add_column("#", width=5)
    tbl.add_column("Sentence", overflow="fold")
    tbl.add_column("Status", width=18)
    for r in rows:
        tbl.add_row(
            str(r["idx"]),
            r["text"],
            Text(r["status"], style=COL[r["phase"]])
        )
    live.update(tbl, refresh=True)


for lib in ("openai", "urllib3", "httpx"):
    logging.getLogger(lib).setLevel(logging.INFO)

# ───────── KEYS / ENDPOINTS ────────────────────────────────────────────────
cfg = yaml.safe_load(open("Wheatley/config/config.yaml", encoding="utf-8"))
openai.api_key = cfg["secrets"]["openai_api_key"]
XI_KEY = cfg["secrets"]["elevenlabs_api_key"]

API_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
HEADERS = {"xi-api-key": XI_KEY, "Content-Type": "application/json"}


# ───────── LIVE-TABLE STATE ────────────────────────────────────────────────
rows: List[Dict] = []


def add_row(idx: float, txt=""):
    rows.append(dict(idx=idx, text=txt, phase="build", status="building"))
    render(rows)


def set_phase(idx: float, phase: str, txt: Optional[str] = None,
              status: Optional[str] = None):
    r = next(r for r in rows if r["idx"] == idx)
    if txt is not None:
        r["text"] = txt
    r["phase"] = phase
    r["status"] = status or dict(
        build="building",
        tts="→ TTS",
        retry="RETRY",
        done="complete",
        ready="ready",
        play="playing",
        end="played",
        err="ERROR"
    )[phase]
    render(rows)


# ───────── BLOCKING HELPERS ────────────────────────────────────────────────
def http_tts(text, prev, nxt, idx):
    """ElevenLabs POST with previous/next text and retry/back-off."""
    def _post() -> requests.Response:
        return requests.post(
            API_URL,
            headers=HEADERS,
            params={"output_format": OUTPUT_FORMAT},
            json={
                "text": text,
                "model_id": MODEL_ID,
                "previous_text": prev or None,
                "next_text": nxt or None
            },
            timeout=60
        )

    attempt = 1
    backoff = 1
    while attempt <= MAX_ATTEMPTS:
        phase = "retry" if attempt > 1 else "tts"
        set_phase(
            idx,
            phase,
            status=f"{'RETRY' if attempt > 1 else '→ TTS'} ({attempt}/{MAX_ATTEMPTS})"
        )
        try:
            resp = _post()
            resp.raise_for_status()
            set_phase(idx, "ready")
            return resp.content
        except Exception as e:
            code = getattr(e.response, "status_code", None)
            if hasattr(e, "response"):
                body = getattr(e.response, "text", "")[:160]
            else:
                body = str(e)
            print(textwrap.fill(
                f"[TTS ERROR] idx {idx} | attempt {attempt}/{MAX_ATTEMPTS} "
                f"| {'HTTP ' + str(code) if code else e.__class__.__name__}\n→ {body}",
                100
            ))
            if attempt == MAX_ATTEMPTS:
                set_phase(
                    idx,
                    "err",
                    status=f"ERR {code or ''} ({MAX_ATTEMPTS}×)".strip()
                )
                return None
            time.sleep(backoff + random.uniform(0, 0.5))
            backoff = min(backoff * 2, 32)
            attempt += 1


def play_mp3(data: bytes | None, idx: float):
    if data is None:
        return
    set_phase(idx, "play")
    seg = AudioSegment.from_file(io.BytesIO(data), format="mp3")
    play(seg)
    set_phase(idx, "end")


# ───────── 1) GPT TOKEN PRODUCER THREAD ────────────────────────────────────
def gpt_thread(prompt: str, q: asyncio.Queue, loop):
    buf = ""
    tmp = ""
    last = time.time()
    idx = 0.0
    scan = 0
    stream = openai.chat.completions.create(
        model="gpt-4o", stream=True,
        messages=[{"role": "user", "content": prompt}]
    )
    for ch in stream:
        tok = getattr(ch.choices[0].delta, "content", "") or ""
        if not tok:
            continue
        buf += tok
        tmp += tok
        if not USE_RICH and time.time() - last > TOKEN_FLUSH_MS / 1000:
            print(tmp, end="", flush=True)
            tmp = ""
            last = time.time()
        while True:
            m = PUNCT_RE.search(buf, scan)
            if not m:
                break
            word = re.findall(r'\b\w+\b', buf[:m.start() + 1])[-1].lower()
            if word in ABBREVS or re.fullmatch(r'\d+', word):
                scan = m.end()
                continue
            sent = buf[:m.end()].strip()
            buf = buf[m.end():].lstrip()
            scan = 0
            add_row(idx, sent)
            asyncio.run_coroutine_threadsafe(q.put((idx, sent)), loop)
            set_phase(idx, "done")
            idx += 1.0
    if buf.strip():
        add_row(idx, buf.strip())
        asyncio.run_coroutine_threadsafe(q.put((idx, buf.strip())), loop)
        set_phase(idx, "done")
    asyncio.run_coroutine_threadsafe(q.put(None), loop)


# ───────── 2) CONCURRENT TTS DISPATCHER (LIMITED BY SEMAPHORE) ─────────────
async def tts_dispatch(sq: asyncio.Queue, aq: asyncio.Queue, pool):
    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(MAX_TTS_WORKERS)
    prev_text = ""
    pending: List[asyncio.Task] = []

    async def handle(idx: float, cur: str, nxt: str, prev: str):
        async with sem:
            data = await asyncio.wrap_future(
                loop.run_in_executor(pool, http_tts, cur, prev, nxt, idx)
            )
            await aq.put((idx, data))

    item = await sq.get()  # first sentence tuple
    while item:
        idx, cur = item
        nxt_item = await sq.get()
        nxt_txt = "" if nxt_item is None else nxt_item[1]
        pending.append(asyncio.create_task(handle(idx, cur, nxt_txt, prev_text)))
        prev_text = cur
        item = nxt_item

    await asyncio.gather(*pending)  # wait all workers
    await aq.put((-1, b""))


# ───────── 3) PLAYBACK SEQUENCER ───────────────────────────────────────────
async def sequencer(aq: asyncio.Queue):
    loop = asyncio.get_running_loop()
    heap = {}
    expect = 0.0
    while True:
        idx, clip = await aq.get()
        if idx == -1:
            break
        heap[idx] = clip
        while expect in heap:
            await loop.run_in_executor(None, play_mp3, heap.pop(expect), expect)
            expect += 1.0


# ───────── ORCHESTRATOR ────────────────────────────────────────────────────
async def chat(prompt: str):
    q_sent = asyncio.Queue(QUEUE_MAXSIZE)
    q_audio = asyncio.Queue(QUEUE_MAXSIZE)
    threading.Thread(
        target=gpt_thread,
        args=(prompt, q_sent, asyncio.get_running_loop()),
        daemon=True
    ).start()
    with ThreadPoolExecutor(MAX_TTS_WORKERS) as pool:
        await asyncio.gather(
            tts_dispatch(q_sent, q_audio, pool),
            sequencer(q_audio)
        )


# ───────── CLI ENTRY ───────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        if USE_RICH:
            prompt = console.input("[bold green]Prompt » [/bold green]")
            console.print(f"[bold]You:[/bold] {prompt}\n")
            live = Live(
                console=console,
                refresh_per_second=10,
                vertical_overflow="visible"
            )
            with live:
                asyncio.run(chat(prompt))
        else:
            asyncio.run(chat(input("Prompt » ")))
    except KeyboardInterrupt:
        sys.exit()
