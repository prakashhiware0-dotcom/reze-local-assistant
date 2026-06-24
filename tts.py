import io
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import sounddevice as sd
import soundfile as sf

from config import PIPER_CONFIG, PIPER_ESPEAK_DATA, PIPER_EXE, PIPER_MODEL


def warm_tts() -> None:
    if _piper_ready():
        print("Piper TTS ready")
    else:
        print("Piper is not fully configured; using text-only mode")


def _piper_ready() -> bool:
    return all(
        os.path.exists(path)
        for path in (PIPER_EXE, PIPER_MODEL, PIPER_CONFIG, PIPER_ESPEAK_DATA)
    )


def synthesize_wav_bytes(text: str) -> Optional[bytes]:
    """Use Piper's normal WAV-file path for correctness.

    The previous low-latency stdout/raw path was faster, but it could produce
    badly framed audio on Windows. This path lets Piper write a real WAV file,
    validates that Python can decode it, then returns those exact bytes.
    """
    clean = " ".join(text.split())
    if not clean:
        return None
    if not _piper_ready():
        print(
            "Piper missing file. Check PIPER_EXE, PIPER_MODEL, "
            "PIPER_CONFIG, and PIPER_ESPEAK_DATA."
        )
        return None

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="reze-piper-", suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        cmd = [
            PIPER_EXE,
            "--model",
            PIPER_MODEL,
            "--config",
            PIPER_CONFIG,
            "--espeak_data",
            PIPER_ESPEAK_DATA,
            "--output_file",
            str(tmp_path),
            "--sentence_silence",
            "0.15",
            "--quiet",
        ]
        result = subprocess.run(
            cmd,
            input=clean.encode("utf-8"),
            capture_output=True,
            cwd=str(Path(PIPER_EXE).parent),
            timeout=45,
        )
        if result.returncode != 0:
            print(f"Piper error: {result.stderr.decode(errors='ignore')}")
            return None

        wav_bytes = tmp_path.read_bytes()
        if not wav_bytes.startswith(b"RIFF"):
            print("Piper did not create a valid WAV file; skipping playback.")
            return None

        info = sf.info(io.BytesIO(wav_bytes))
        if info.frames <= 0 or info.samplerate <= 0:
            print("Piper created an empty WAV file; skipping playback.")
            return None
        return wav_bytes
    except Exception as exc:
        print(f"Piper synthesis error: {exc}")
        return None
    finally:
        if tmp_path:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass


def speak(text: str) -> None:
    print(f"Reze: {text}")
    wav_bytes = synthesize_wav_bytes(text)
    if not wav_bytes:
        return

    try:
        data, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
        if data.size == 0:
            print("TTS playback skipped because decoded audio is empty.")
            return
        sd.stop()
        sd.play(data, sr)
        sd.wait()
    except Exception as exc:
        print(f"TTS playback error: {exc}")


def stop_speaking() -> None:
    sd.stop()


if __name__ == "__main__":
    sample = "Hello, I am Reze. This is a clean Piper voice test."
    output = Path("piper_test.wav").resolve()
    wav = synthesize_wav_bytes(sample)
    if not wav:
        raise SystemExit("Piper test failed: no WAV generated.")
    output.write_bytes(wav)
    info = sf.info(io.BytesIO(wav))
    print(f"Wrote {output}")
    print(f"Sample rate: {info.samplerate} Hz | Channels: {info.channels} | Duration: {info.duration:.2f}s")
