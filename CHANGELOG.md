# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- Working on: <next feature you're building>

## [v1.0] - 2026-06-21
### Added
- Voice trigger using faster-whisper
- Local LLM responses via Ollama (llama3.1:8b)
- Text-to-speech output via Piper TTS
- Device status awareness (time, date, battery, CPU, RAM, disk space)
- Fast-path direct command handling (skips LLM for known queries)
### Notes
- Tested on Python 3.13 / Windows