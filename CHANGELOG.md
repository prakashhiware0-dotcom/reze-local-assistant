# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- Working on: <next feature you're building>

## [v1.1] - 2026-06-21
### Added
- Optional web UI (`server.py` + `static/`) as an alternative to the
  terminal — same `reze.py` engine underneath, imported directly, not
  duplicated
- WebSocket-driven status states (listening / thinking / speaking) shown
  live in the browser
- Typed message input in the web UI as a fallback to voice
### Notes
- Run with two commands: `ollama serve`, then `python server.py` — see
  README for details
- Terminal mode (`python reze.py`) is unaffected and still works exactly
  as before

## [v1.0] - 2026-06-21
### Added
- Voice trigger using faster-whisper
- Local LLM responses via Ollama (llama3.1:8b)
- Text-to-speech output via Piper TTS
- Device status awareness (time, date, battery, CPU, RAM, disk space)
- Fast-path direct command handling (skips LLM for known queries)
### Notes
- Tested on Python 3.13 / Windows