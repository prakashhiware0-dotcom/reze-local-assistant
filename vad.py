from dataclasses import dataclass

import numpy as np
import torch

from config import (
    SAMPLE_RATE,
    VAD_END_THRESHOLD,
    VAD_MIN_SPEECH_MS,
    VAD_SILENCE_MS,
    VAD_START_THRESHOLD,
)


@dataclass
class VADEvent:
    is_speech: bool
    is_done: bool = False


class SpeechVAD:
    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.in_speech = False
        self.speech_ms = 0.0
        self.silence_ms = 0.0
        self.model = None
        self._load_silero()

    def _load_silero(self) -> None:
        try:
            from silero_vad import load_silero_vad

            self.model = load_silero_vad()
        except Exception as exc:
            print(f"Silero VAD unavailable, using energy VAD fallback: {exc}")
            self.model = None

    def accept(self, chunk: np.ndarray) -> VADEvent:
        chunk_ms = len(chunk) * 1000.0 / self.sample_rate
        probability = self._speech_probability(chunk)

        if not self.in_speech:
            if probability >= VAD_START_THRESHOLD:
                self.speech_ms += chunk_ms
                if self.speech_ms >= VAD_MIN_SPEECH_MS:
                    self.in_speech = True
                    self.silence_ms = 0.0
                    return VADEvent(is_speech=True)
            else:
                self.speech_ms = 0.0
            return VADEvent(is_speech=False)

        if probability >= VAD_END_THRESHOLD:
            self.silence_ms = 0.0
            return VADEvent(is_speech=True)

        self.silence_ms += chunk_ms
        return VADEvent(is_speech=False, is_done=self.silence_ms >= VAD_SILENCE_MS)

    def _speech_probability(self, chunk: np.ndarray) -> float:
        if self.model is None:
            rms = float(np.sqrt(np.mean(np.square(chunk)) + 1e-9))
            return min(1.0, rms / 0.035)

        with torch.no_grad():
            tensor = torch.from_numpy(chunk.astype(np.float32))
            return float(self.model(tensor, self.sample_rate).item())
