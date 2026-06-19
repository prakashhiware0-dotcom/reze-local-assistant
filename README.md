# 🎙️ Reze — Local Voice Assistant

A fully **offline-first** voice assistant that listens, understands, thinks, and talks back — no cloud APIs, no subscriptions, no data leaving your machine (except optional model downloads on first run).

Reze understands **Hindi, English, and Hinglish** speech input, but always replies in natural spoken English using a local neural TTS engine.

---

## ✨ Features

- 🎤 **Speech Recognition** — [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (auto-detects Hindi / English / Hinglish)
- 🧠 **Local LLM Brain** — powered by [Ollama](https://ollama.com) (default: `llama3.1:8b`)
- 🔊 **Natural Offline TTS** — [Piper TTS](https://github.com/rhasspy/piper) (`en_US-lessac-high` voice — human-like, not robotic)
- 🌐 **Fully Offline** — no internet required after initial model downloads
- ⚡ **GPU Accelerated** — automatically uses CUDA if available, falls back to CPU
- 🗣️ **Multilingual Input** — speak in Hindi, English, or mixed Hinglish; Reze understands all three

---

## 🧱 Tech Stack

| Component | Technology |
|---|---|
| Speech-to-Text | faster-whisper (`medium` model) |
| Language Model | Ollama + Llama 3.1 8B |
| Text-to-Speech | Piper TTS (`en_US-lessac-high`) |
| Audio I/O | sounddevice, soundfile |
| Language Detection | langdetect |

---

## 📦 Prerequisites

- **Python 3.13+**
- **[Ollama](https://ollama.com/download)** installed and running
- A working microphone and speakers
- ~3 GB free disk space (for Whisper + Piper models)

---

## 🚀 Setup

### 1. Clone the repo
```bash
git clone https://github.com/prakashhiware0-dotcom/reze-local-assistant.git
cd reze-local-assistant
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Pull the Ollama model
```bash
ollama pull llama3.1:8b
ollama run llama3.1:8b
```
Keep this running in a separate terminal (or let Ollama run as a background service).

### 4. Set up Piper TTS

1. Download the Piper binary for your OS from the [Piper releases page](https://github.com/rhasspy/piper/releases/latest)
2. Extract it into a `piper/` folder inside this project, so you have:
   ```
   reze-local-assistant/
   └── piper/
       └── piper.exe   (or piper on Linux/Mac)
   ```
3. Download the voice model files from [Piper Voices — en_US lessac (high)](https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/lessac/high):
   - `en_US-lessac-high.onnx`
   - `en_US-lessac-high.onnx.json`
4. Place both files in the project root (same folder as `reze.py`)

### 5. Run Reze
```bash
python reze.py
```

The first run will also auto-download the Whisper `medium` model (~1.5 GB) from Hugging Face — this only happens once.

---

## ⚙️ Configuration

All settings can be overridden via environment variables — no code editing required:

| Variable | Default | Description |
|---|---|---|
| `REZE_OLLAMA_MODEL` | `llama3.1:8b` | Ollama model name |
| `REZE_OLLAMA_URL` | `http://localhost:11434/api/chat` | Ollama API endpoint |
| `REZE_WHISPER_MODEL` | `medium` | Whisper model size (`tiny`/`base`/`small`/`medium`/`large`) |
| `REZE_RECORD_SECONDS` | `8` | Recording window length per turn |
| `REZE_PIPER_EXE` | `piper/piper.exe` | Path to Piper binary |
| `REZE_PIPER_MODEL` | `en_US-lessac-high.onnx` | Piper voice model file |

Example (Linux/Mac):
```bash
REZE_WHISPER_MODEL=small REZE_OLLAMA_MODEL=qwen3:4b python reze.py
```

Example (Windows PowerShell):
```powershell
$env:REZE_WHISPER_MODEL="small"; python reze.py
```

---

## 🗣️ Usage

Once running, Reze will greet you and start listening in turns:

```
🎙️  Reze Voice Assistant  |  say 'exit' to quit
STT: Whisper Medium  |  TTS: Piper (offline)
NLP: llama3.1:8b via Ollama

🎤 Listening for 8s … (speak now)
📝 You said : 'What is the capital of India?'  [lang≈en]
🤖 Thinking … done
🔊 Reze: The capital of India is New Delhi.
```

Say **"exit"**, **"quit"**, **"bye"**, or **"stop"** at any time to end the session.

---

## 🛠️ Troubleshooting

**Ollama returns empty replies**
Make sure you're using `/api/chat` (not `/api/generate`) and that the model is pulled (`ollama pull llama3.1:8b`).

**Piper not found / TTS silent**
Check that `piper.exe` exists at the path set in `REZE_PIPER_EXE`, and that the `.onnx` + `.onnx.json` files are both present in the project root.

**Whisper download is slow / rate-limited**
Set a free Hugging Face token to speed up downloads:
```bash
huggingface-cli login
```

**Speech recognition struggles with Hinglish**
Try the `large-v3` Whisper model (more accurate, slower) via `REZE_WHISPER_MODEL=large-v3`.

---

## 🗺️ Roadmap

- [ ] Wake-word detection ("Hey Reze") instead of fixed recording windows
- [ ] Voice cloning support (Coqui XTTS / on Python ≤3.11)
- [ ] Conversation memory persistence across sessions
- [ ] Optional internet search tool integration
- [ ] GPU benchmark mode

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

## 🙏 Acknowledgements

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [Ollama](https://ollama.com)
- [Piper TTS](https://github.com/rhasspy/piper)
