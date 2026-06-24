import queue
import time
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from config import MAX_RECORD_SECONDS, SAMPLE_RATE, VAD_SILENCE_MS
from vad import SpeechVAD


def record_audio(
    seconds: Optional[float] = None,
    sr: int = SAMPLE_RATE,
    on_speech_start: Optional[Callable[[], None]] = None,
) -> np.ndarray:
    """Record one utterance using VAD instead of a fixed-size blocking window."""
    max_seconds = float(seconds or MAX_RECORD_SECONDS)
    vad = SpeechVAD(sample_rate=sr)
    chunks: list[np.ndarray] = []
    audio_queue: queue.Queue[np.ndarray] = queue.Queue()
    start_time = time.monotonic()
    speech_started = False

    block_size = 512

    def callback(indata, frames, _time_info, status):
        if status:
            print(f"Audio input warning: {status}")
        audio_queue.put(indata[:, 0].copy())

    print(f"\nListening... speak when ready. Silence > {VAD_SILENCE_MS} ms ends the turn.")

    with sd.InputStream(
        samplerate=sr,
        channels=1,
        dtype="float32",
        blocksize=block_size,
        callback=callback,
    ):
        while time.monotonic() - start_time < max_seconds:
            try:
                chunk = audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            event = vad.accept(chunk)
            if event.is_speech:
                if not speech_started:
                    speech_started = True
                    if on_speech_start:
                        on_speech_start()
                    print("Speech detected.")
                chunks.append(chunk)
            elif speech_started:
                chunks.append(chunk)
                if event.is_done:
                    break

    if not chunks:
        return np.array([], dtype=np.float32)

    audio = np.concatenate(chunks).astype(np.float32)
    return np.clip(audio, -1.0, 1.0)
