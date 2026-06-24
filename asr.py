import re
import time

import numpy as np

from config import SAMPLE_RATE, SENSEVOICE_DEVICE, SENSEVOICE_MODEL


_model = None


def load_asr():
    global _model
    if _model is None:
        from funasr import AutoModel

        print(f"Loading SenseVoiceSmall ({SENSEVOICE_MODEL}) on {SENSEVOICE_DEVICE}...", end=" ", flush=True)
        _model = AutoModel(
            model=SENSEVOICE_MODEL,
            trust_remote_code=True,
            device=SENSEVOICE_DEVICE,
            disable_update=True,
        )
        print("ready")
    return _model


def transcribe(audio: np.ndarray) -> str:
    if audio.size == 0:
        return ""

    model = load_asr()
    t0 = time.perf_counter()
    result = model.generate(
        input=audio,
        fs=SAMPLE_RATE,
        language="en",
        use_itn=True,
        batch_size_s=10,
    )
    text = _extract_text(result)
    elapsed = time.perf_counter() - t0
    print(f"You said: {text!r}")
    print(f"ASR: {elapsed:.2f}s")
    return text


def _extract_text(result) -> str:
    if isinstance(result, list) and result:
        value = result[0].get("text", "") if isinstance(result[0], dict) else str(result[0])
    elif isinstance(result, dict):
        value = result.get("text", "")
    else:
        value = str(result or "")

    value = re.sub(r"<\|.*?\|>", "", value)
    return " ".join(value.split()).strip()
