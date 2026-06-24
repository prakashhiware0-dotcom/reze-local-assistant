import os
import json

import torch


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _abs_path(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(BASE_DIR, path)

OLLAMA_URL = os.environ.get("REZE_OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.environ.get("REZE_OLLAMA_MODEL", "huihui_ai/llama3.2-abliterate:latest")

SENSEVOICE_MODEL = os.environ.get("REZE_SENSEVOICE_MODEL", "iic/SenseVoiceSmall")
SAMPLE_RATE = int(os.environ.get("REZE_SAMPLE_RATE", "16000"))
MAX_RECORD_SECONDS = float(os.environ.get("REZE_MAX_RECORD_SECONDS", "12"))
VAD_SILENCE_MS = int(os.environ.get("REZE_VAD_SILENCE_MS", "300"))
VAD_MIN_SPEECH_MS = int(os.environ.get("REZE_VAD_MIN_SPEECH_MS", "120"))
VAD_START_THRESHOLD = float(os.environ.get("REZE_VAD_START_THRESHOLD", "0.50"))
VAD_END_THRESHOLD = float(os.environ.get("REZE_VAD_END_THRESHOLD", "0.35"))

PIPER_EXE = _abs_path(os.environ.get("REZE_PIPER_EXE", os.path.join("piper", "piper.exe")))
PIPER_MODEL = _abs_path(os.environ.get("REZE_PIPER_MODEL", "en_US-lessac-high.onnx"))
PIPER_CONFIG = _abs_path(os.environ.get("REZE_PIPER_CONFIG", PIPER_MODEL + ".json"))
PIPER_ESPEAK_DATA = _abs_path(os.environ.get("REZE_PIPER_ESPEAK_DATA", os.path.join("piper", "espeak-ng-data")))
PIPER_SAMPLE_RATE = int(os.environ.get("REZE_PIPER_SAMPLE_RATE", "0") or "0")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
SENSEVOICE_DEVICE = "cuda:0" if DEVICE == "cuda" else "cpu"
COMPUTE_TYPE = "int8_float16" if DEVICE == "cuda" else "int8"

SYSTEM_PROMPT = (
    "You are Reze, a fast local voice assistant. Reply in natural spoken English. "
    "Keep answers to one or two short sentences. No markdown, bullets, filler, or stage directions."
)

RECORD_SECONDS = int(MAX_RECORD_SECONDS)

if not PIPER_SAMPLE_RATE:
    try:
        with open(PIPER_CONFIG, "r", encoding="utf-8") as f:
            PIPER_SAMPLE_RATE = int(json.load(f)["audio"]["sample_rate"])
    except Exception:
        PIPER_SAMPLE_RATE = 22050
