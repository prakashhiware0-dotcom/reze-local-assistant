"""
Reze - Voice Assistant
======================
Stack:
  - Speech Recognition : faster-whisper (MEDIUM model)
  - NLP                : Ollama + llama3.1:8b
  - TTS                : Piper TTS (offline, natural English)
  - Language           : English

Requirements:
  pip install faster-whisper sounddevice soundfile numpy requests langdetect torch psutil

Piper setup:
  1.For me it windows : Extract piper_windows_amd64.zip → place piper.exe at: piper\\piper.exe
  2. Download en_US-lessac-high.onnx + .onnx.json → same folder as reze.py

Ollama must be running:
  ollama run llama3.1:8b
"""

import os
import subprocess
import tempfile
import numpy as np
import sounddevice as sd
import soundfile as sf
import requests
import torch
from faster_whisper import WhisperModel
from langdetect import detect, DetectorFactory
import psutil
from datetime import datetime

DetectorFactory.seed = 0

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG  (override any of these via environment variables, no code edits needed)
# ══════════════════════════════════════════════════════════════════════════════
OLLAMA_URL     = os.environ.get("REZE_OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL   = os.environ.get("REZE_OLLAMA_MODEL", "llama3.1:8b")

WHISPER_MODEL  = os.environ.get("REZE_WHISPER_MODEL", "medium")
RECORD_SECONDS = int(os.environ.get("REZE_RECORD_SECONDS", "5"))
SAMPLE_RATE    = 16000

# Piper paths — relative to reze.py location (override with env vars if needed)
PIPER_EXE      = os.environ.get("REZE_PIPER_EXE", os.path.join("piper", "piper.exe"))
PIPER_MODEL    = os.environ.get("REZE_PIPER_MODEL", "en_US-lessac-high.onnx")

DEVICE         = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE   = "float16" if DEVICE == "cuda" else "int8"

SYSTEM_PROMPT = """You are Reze, a smart and friendly voice assistant.
Rules you MUST follow every single time:
1. ALWAYS reply in English only — even if the user speaks Hindi or Hinglish.
2. Answer in 1–3 short sentences MAX. Never write long paragraphs.
3. No bullet points, no markdown, no lists — plain spoken language only.
4. Be direct and helpful. Skip filler phrases like "Certainly!" or "Of course!".
5. If you don't know something, say so in one sentence."""

# ══════════════════════════════════════════════════════════════════════════════
#  LOAD MODELS
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n🔧 Device  : {DEVICE.upper()}")
print(f"📦 Loading Whisper ({WHISPER_MODEL}) …", end=" ", flush=True)
whisper_model = WhisperModel(WHISPER_MODEL, device=DEVICE, compute_type=COMPUTE_TYPE)
print("✅")

if not os.path.exists(PIPER_EXE):
    print(f"⚠️  Piper not found at '{PIPER_EXE}'. Check path.")
else:
    print(f"📦 Piper TTS found ✅")

# ══════════════════════════════════════════════════════════════════════════════
#  SPEECH RECOGNITION
# ══════════════════════════════════════════════════════════════════════════════
def record_audio(seconds: int = RECORD_SECONDS, sr: int = SAMPLE_RATE) -> np.ndarray:
    print(f"\n🎤 Listening for {seconds}s … (speak now)")
    audio = sd.rec(int(seconds * sr), samplerate=sr, channels=1, dtype="float32")
    sd.wait()
    return audio.flatten()


def transcribe(audio: np.ndarray) -> str:
    segments, info = whisper_model.transcribe(
        audio,
        beam_size=5,
        language=None,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    text = " ".join(seg.text.strip() for seg in segments).strip()
    print(f"📝 You said : {text!r}  [lang≈{info.language}]")
    return text

# ══════════════════════════════════════════════════════════════════════════════
#  OLLAMA NLP
# ══════════════════════════════════════════════════════════════════════════════
def ask_ollama(user_text: str, history: list) -> str:
    status = get_device_status()
    full_system_prompt = f"""{SYSTEM_PROMPT}

Current real-time device info (mention only if the user's question is actually about it):
- Time: {status['time']}
- Battery: {status['battery']}
- CPU usage: {status['cpu_usage']}
- RAM usage: {status['ram_usage']}
- Free disk space: {status['disk_free_gb']} GB"""

    messages = [{"role": "system", "content": full_system_prompt}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": user_text})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.7, "top_p": 0.9, "num_predict": 120},
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        reply = data.get("message", {}).get("content", "").strip()
        if "<think>" in reply:
            reply = reply.split("</think>")[-1].strip()
        return reply or "Sorry, I didn't catch that. Can you repeat?"
    except requests.exceptions.ConnectionError:
        return "Ollama is not running. Please run: ollama run llama3.1:8b"
    except Exception as e:
        return f"Error: {e}"

# ══════════════════════════════════════════════════════════════════════════════
#  TEXT-TO-SPEECH  (Piper — offline, natural)
# ══════════════════════════════════════════════════════════════════════════════
def speak(text: str):
    print(f"🔊 Reze: {text}")

    if not os.path.exists(PIPER_EXE):
        print(f"   (Piper not found, text-only mode)")
        return

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        cmd = [
            PIPER_EXE,
            "--model", PIPER_MODEL,
            "--output_file", tmp_path,
        ]
        result = subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=30,
        )

        if result.returncode != 0:
            print(f"⚠️  Piper error: {result.stderr.decode()}")
            return

        data, sr = sf.read(tmp_path)
        sd.play(data, sr)
        sd.wait()
        os.unlink(tmp_path)

    except Exception as e:
        print(f"⚠️  TTS error: {e}")
        print(f"   Reze: {text}")

# ══════════════════════════════════════════════════════════════════════════════
#  DEVICE STATUS
# ══════════════════════════════════════════════════════════════════════════════
def get_device_status():
    battery = psutil.sensors_battery()
    battery_str = (
        f"{battery.percent}% ({'charging' if battery.power_plugged else 'on battery'})"
        if battery else "No battery (desktop)"
    )
    return {
        "time": datetime.now().strftime("%I:%M %p, %A, %d %B %Y"),
        "battery": battery_str,
        "cpu_usage": f"{psutil.cpu_percent(interval=0.5)}%",
        "ram_usage": f"{psutil.virtual_memory().percent}%",
        "disk_free_gb": round(psutil.disk_usage('C:\\').free / (1024**3), 1)
    }


def check_direct_commands(user_input: str):
    text = user_input.lower()
    status = get_device_status()

    if "time" in text and "date" in text:
        return f"It's {status['time']}"
    elif "time" in text:
        return f"It's {status['time'].split(',')[0]}"
    elif "date" in text or "day is it" in text:
        return f"Today is {status['time'].split(', ', 1)[1]}"
    elif "battery" in text:
        return f"Your battery is at {status['battery']}"
    elif "cpu" in text or "processor" in text:
        return f"CPU usage is at {status['cpu_usage']}"
    elif "ram" in text or "memory" in text:
        return f"RAM usage is at {status['ram_usage']}"
    elif "disk" in text or "storage" in text:
        return f"You have {status['disk_free_gb']} GB free"

    return None

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("\n" + "═" * 55)
    print("  🎙️  Reze Voice Assistant  |  say 'exit' to quit")
    print("  STT: Whisper Medium  |  TTS: Piper (offline)")
    print("  NLP: llama3.1:8b via Ollama")
    print("  Made by Prakash | https://github.com/prakashhiware0-dotcom/reze-local-assistant.git")
    print("═" * 55)

    speak("Hey, I am Reze. How can I help you?")

    history = []

    while True:
        try:
            audio = record_audio()
            user_text = transcribe(audio)

            if not user_text:
                speak("I didn't hear anything. Please try again.")
                continue

            direct_answer = check_direct_commands(user_text)
            if direct_answer:
                speak(direct_answer)
                continue

            if any(kw in user_text.lower() for kw in ["exit", "quit", "bye", "stop"]):
                speak("Okay, bye! Talk to you later.")
                break

            print("🤖 Thinking …", end=" ", flush=True)
            reply = ask_ollama(user_text, history)
            print("done")

            history.append({"role": "user",     "content": user_text})
            history.append({"role": "assistant", "content": reply})

            speak(reply)

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Bye!")
            speak("Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            speak("Something went wrong. Please try again.")


if __name__ == "__main__":
    main()