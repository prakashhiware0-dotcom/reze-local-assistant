"""
Reze - Web UI Server
=====================
Imports every function directly from reze.py (unchanged) and wraps it in
a FastAPI WebSocket server so a browser page can drive it instead of the
terminal. reze.py is never modified by this file.

Run via run_reze.bat (recommended — it also starts Ollama for you), or
directly:
    python server.py
Then open http://localhost:8765 in your browser.

Terminal mode still works exactly as before:
    python reze.py

IMPORTANT startup behavior:
The browser opens immediately, BEFORE the Whisper model finishes loading.
Model loading (first run especially — it may download ~1.5GB) happens in
a background thread, and the page shows a "Warming up..." state until
it's ready. This means a slow or failed model load no longer prevents the
browser from opening, and any error is visible on the page instead of
silently killing the process.
"""

import os
import sys
import json
import asyncio
import base64
import traceback
import webbrowser
import threading
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

HOST = os.environ.get("REZE_HOST", "127.0.0.1")
PORT = int(os.environ.get("REZE_PORT", "8765"))


# ══════════════════════════════════════════════════════════════════════════
#  Boot state — tracked so the frontend can poll/display real status
#  instead of the page just sitting there with no explanation.
# ══════════════════════════════════════════════════════════════════════════
boot_state = {
    "stage": "starting",   # starting -> loading_models -> ready -> error
    "detail": "Starting server…",
    "error": None,
}

reze = None  # populated once import succeeds, in the background thread


def load_reze_module():
    """Runs reze.py's module-level code (which loads Whisper) in a
    background thread so it can never block the web server or the
    browser from opening."""
    global reze
    try:
        boot_state["stage"] = "loading_models"
        boot_state["detail"] = "Loading fine-tuned speech model (first run may take a few minutes to download)…"
        import reze as _reze
        _reze.warm_models()
        reze = _reze
        boot_state["stage"] = "ready"
        boot_state["detail"] = "Ready"
    except Exception as e:
        boot_state["stage"] = "error"
        boot_state["detail"] = str(e)
        boot_state["error"] = traceback.format_exc()
        print("\n❌ Failed to load reze.py:\n" + boot_state["error"])


threading.Thread(target=load_reze_module, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════
#  FASTAPI APP — created immediately, independent of model loading above
# ══════════════════════════════════════════════════════════════════════════
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse, JSONResponse
except ImportError:
    print("\n❌ fastapi/uvicorn not installed. Run run_reze.bat again, or:")
    print("   pip install -r requirements.txt\n")
    sys.exit(1)

app = FastAPI(title="Reze Voice Assistant")


@app.middleware("http")
async def no_cache_static(request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.get("/")
async def index():
    return FileResponse(str(BASE_DIR / "static" / "index.html"))


@app.get("/api/boot-status")
async def boot_status():
    return JSONResponse(boot_state)


def synthesize_speech(text: str):
    """Return Piper WAV bytes for the browser to play."""
    if reze is None:
        return None

    try:
        wav_bytes = reze.synthesize_wav_bytes(text)
        if not wav_bytes:
            return None
        return base64.b64encode(wav_bytes).decode("ascii")
    except Exception as e:
        print(f"⚠️  TTS error: {e}")
        return None


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    history: list = []
    loop = asyncio.get_event_loop()

    async def send(event: str, **payload):
        await ws.send_text(json.dumps({"event": event, **payload}))

    async def speak_to_browser(text: str):
        await send("speaking", text=text, message_id=f"assistant-{uuid.uuid4().hex}")
        audio_b64 = await loop.run_in_executor(None, synthesize_speech, text)
        await send("audio", audio=audio_b64, text=text)

    # Wait for models to finish loading before greeting, so the first
    # interaction doesn't race ahead of Whisper being ready.
    while boot_state["stage"] not in ("ready", "error"):
        await send("booting", detail=boot_state["detail"])
        await asyncio.sleep(0.5)

    if boot_state["stage"] == "error":
        await send("boot_error", detail=boot_state["detail"])
        await send("idle")
    else:
        await speak_to_browser("Hey, I am Reze. How can I help you?")
        await send("idle")

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if reze is None:
                await send("boot_error", detail=boot_state["detail"])
                continue

            if msg_type == "listen":
                client_id = msg.get("client_id") or f"voice-{uuid.uuid4().hex}"
                seconds = int(msg.get("seconds", reze.RECORD_SECONDS))
                await send("listening", seconds=seconds)

                audio = await loop.run_in_executor(None, reze.record_audio, seconds, reze.SAMPLE_RATE, reze.stop_speaking)
                user_text = await loop.run_in_executor(None, reze.transcribe, audio)

                if not user_text:
                    await send("user_text", text="", message_id=client_id)
                    await speak_to_browser("I didn't hear anything. Please try again.")
                    await send("idle")
                    continue

                await send("user_text", text=user_text, message_id=client_id)

                direct_answer = await loop.run_in_executor(None, reze.check_direct_commands, user_text)
                if direct_answer:
                    reply = direct_answer
                elif any(kw in user_text.lower() for kw in ["exit", "quit", "bye", "stop"]):
                    reply = "Okay, bye! Talk to you later."
                else:
                    await send("thinking")
                    reply = await loop.run_in_executor(None, reze.ask_ollama, user_text, history)
                    history.append({"role": "user", "content": user_text})
                    history.append({"role": "assistant", "content": reply})

                await speak_to_browser(reply)
                await send("idle")

            elif msg_type == "text":
                client_id = msg.get("client_id") or f"text-{uuid.uuid4().hex}"
                user_text = (msg.get("text") or "").strip()
                if not user_text:
                    continue

                await send("user_text", text=user_text, message_id=client_id)

                direct_answer = await loop.run_in_executor(None, reze.check_direct_commands, user_text)
                if direct_answer:
                    reply = direct_answer
                else:
                    await send("thinking")
                    reply = await loop.run_in_executor(None, reze.ask_ollama, user_text, history)
                    history.append({"role": "user", "content": user_text})
                    history.append({"role": "assistant", "content": reply})

                await speak_to_browser(reply)
                await send("idle")

            elif msg_type == "status":
                status = await loop.run_in_executor(None, reze.get_device_status)
                await send("device_status", status=status)

    except WebSocketDisconnect:
        pass


app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


if __name__ == "__main__":
    import uvicorn

    url = f"http://{HOST}:{PORT}"

    def open_browser():
        webbrowser.open(url)

    # Open the browser almost immediately — the page itself shows a
    # "warming up" state and polls /api/boot-status until models are ready.
    threading.Timer(1.0, open_browser).start()

    print("\n" + "═" * 55)
    print("  🎙️  Reze Voice Assistant — Web UI")
    print(f"  Open  : {url}")
    print("  Opening your browser now — the page will show progress")
    print("  while the speech model finishes loading.")
    print("═" * 55 + "\n")

    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
