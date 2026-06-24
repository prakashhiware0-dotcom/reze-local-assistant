import asyncio
import re
import threading
import time

from audio import record_audio
from asr import load_asr, transcribe
from config import COMPUTE_TYPE, DEVICE, OLLAMA_MODEL, SAMPLE_RATE, SENSEVOICE_MODEL
from llm import ask_ollama, check_direct_commands, stream_ollama
from tts import speak, stop_speaking, warm_tts


def warm_models() -> None:
    print(f"\nDevice: {DEVICE.upper()} | compute target: {COMPUTE_TYPE}")
    load_asr()
    warm_tts()


async def run_terminal() -> None:
    warm_models()
    print("\n" + "=" * 55)
    print("  Reze Voice Assistant | say 'exit' to quit")
    print(f"  STT: {SENSEVOICE_MODEL}")
    print(f"  NLP: {OLLAMA_MODEL} via streamed Ollama")
    print("=" * 55)

    await asyncio.to_thread(speak, "Hey, I am Reze. How can I help you?")
    history: list[dict[str, str]] = []

    while True:
        try:
            audio = await asyncio.to_thread(record_audio, None, SAMPLE_RATE, stop_speaking)
            turn_start = time.perf_counter()
            user_text = await asyncio.to_thread(transcribe, audio)

            if not user_text:
                await asyncio.to_thread(speak, "I didn't hear anything. Please try again.")
                continue

            if any(kw in user_text.lower() for kw in ("exit", "quit", "bye", "stop")):
                await asyncio.to_thread(speak, "Okay, bye. Talk to you later.")
                break

            direct_answer = await asyncio.to_thread(check_direct_commands, user_text)
            if direct_answer:
                await asyncio.to_thread(speak, direct_answer)
                continue

            reply = await stream_reply_and_speak(user_text, history)
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": reply})
            print(f"Turn latency after speech end: {time.perf_counter() - turn_start:.2f}s\n")

        except KeyboardInterrupt:
            print("\nInterrupted. Bye.")
            await asyncio.to_thread(speak, "Goodbye.")
            break
        except Exception as exc:
            print(f"\nUnexpected error: {exc}")
            await asyncio.to_thread(speak, "Something went wrong. Please try again.")


async def stream_reply_and_speak(user_text: str, history: list) -> str:
    print("Thinking...", end=" ", flush=True)
    reply_parts: list[str] = []
    speak_buffer = ""
    speaking_task = None

    async for chunk in _async_stream(user_text, history):
        print(chunk, end="", flush=True)
        reply_parts.append(chunk)
        speak_buffer += chunk

        if _ready_to_speak(speak_buffer):
            phrase = speak_buffer.strip()
            speak_buffer = ""
            if speaking_task:
                await speaking_task
            speaking_task = asyncio.create_task(asyncio.to_thread(speak, phrase))

    if speak_buffer.strip():
        if speaking_task:
            await speaking_task
        speaking_task = asyncio.create_task(asyncio.to_thread(speak, speak_buffer.strip()))

    if speaking_task:
        await speaking_task

    print()
    reply = "".join(reply_parts).strip()
    if "<think>" in reply:
        reply = reply.split("</think>")[-1].strip()
    return reply or "Sorry, I didn't catch that. Can you repeat?"


async def _async_stream(user_text: str, history: list):
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def produce():
        try:
            for chunk in stream_ollama(user_text, history):
                loop.call_soon_threadsafe(queue.put_nowait, chunk)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    threading.Thread(target=produce, daemon=True).start()

    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        yield chunk


def _ready_to_speak(text: str) -> bool:
    stripped = text.strip()
    return len(stripped) >= 80 or bool(re.search(r"[.!?]\s*$", stripped))


def run() -> None:
    asyncio.run(run_terminal())


__all__ = [
    "ask_ollama",
    "check_direct_commands",
    "record_audio",
    "run",
    "speak",
    "stop_speaking",
    "transcribe",
    "warm_models",
]
