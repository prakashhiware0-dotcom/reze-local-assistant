"""
Reze - Real-time local voice assistant.

Compatibility entry point for the terminal app and web server. The runtime is
split into audio, VAD, ASR, LLM, TTS, and assistant modules so each slow stage
can be optimized independently.
"""

from assistant import run, warm_models
from audio import record_audio
from asr import transcribe
from config import (
    COMPUTE_TYPE,
    DEVICE,
    OLLAMA_MODEL,
    OLLAMA_URL,
    PIPER_EXE,
    PIPER_MODEL,
    RECORD_SECONDS,
    SAMPLE_RATE,
    SENSEVOICE_MODEL,
    SYSTEM_PROMPT,
)
from llm import ask_ollama, check_direct_commands, get_device_status, stream_ollama
from tts import speak, stop_speaking, synthesize_wav_bytes

WHISPER_MODEL = SENSEVOICE_MODEL


def main():
    run()


if __name__ == "__main__":
    main()
