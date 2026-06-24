import json
from datetime import datetime
from typing import Iterable

import psutil
import requests

from config import OLLAMA_MODEL, OLLAMA_URL, SYSTEM_PROMPT


def _fallback_model_name(model: str) -> str | None:
    if ":" in model and not model.endswith(":latest"):
        return model.rsplit(":", 1)[0] + ":latest"
    return None


def get_device_status():
    battery = psutil.sensors_battery()
    battery_str = (
        f"{battery.percent}% ({'charging' if battery.power_plugged else 'on battery'})"
        if battery
        else "No battery (desktop)"
    )
    return {
        "time": datetime.now().strftime("%I:%M %p, %A, %d %B %Y"),
        "battery": battery_str,
        "cpu_usage": f"{psutil.cpu_percent(interval=None)}%",
        "ram_usage": f"{psutil.virtual_memory().percent}%",
        "disk_free_gb": round(psutil.disk_usage("C:\\").free / (1024**3), 1),
    }


def check_direct_commands(user_input: str):
    text = user_input.lower()
    status = get_device_status()

    if "time" in text and "date" in text:
        return f"It's {status['time']}"
    if "time" in text:
        return f"It's {status['time'].split(',')[0]}"
    if "date" in text or "day is it" in text:
        return f"Today is {status['time'].split(', ', 1)[1]}"
    if "battery" in text:
        return f"Your battery is at {status['battery']}"
    if "cpu" in text or "processor" in text:
        return f"CPU usage is at {status['cpu_usage']}"
    if "ram" in text or "memory" in text:
        return f"RAM usage is at {status['ram_usage']}"
    if "disk" in text or "storage" in text:
        return f"You have {status['disk_free_gb']} GB free"

    return None


def stream_ollama(user_text: str, history: list) -> Iterable[str]:
    status_hint = ""
    lowered = user_text.lower()
    if any(word in lowered for word in ("time", "date", "battery", "cpu", "ram", "memory", "disk", "storage")):
        status = get_device_status()
        status_hint = (
            f"\nDevice info: time={status['time']}; battery={status['battery']}; "
            f"cpu={status['cpu_usage']}; ram={status['ram_usage']}; disk_free={status['disk_free_gb']} GB."
        )

    messages = [{"role": "system", "content": SYSTEM_PROMPT + status_hint}]
    messages.extend(history[-2:])
    messages.append({"role": "user", "content": user_text})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": True,
        "options": {"temperature": 0.5, "top_p": 0.9, "num_predict": 40},
    }

    yield from _post_ollama_stream(payload)


def _post_ollama_stream(payload: dict) -> Iterable[str]:
    try:
        with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=30) as resp:
            if resp.status_code == 404:
                fallback = _fallback_model_name(payload["model"])
                if fallback:
                    payload = {**payload, "model": fallback}
                    with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=30) as retry:
                        retry.raise_for_status()
                        yield from _read_ollama_lines(retry)
                    return
            resp.raise_for_status()
            yield from _read_ollama_lines(resp)
    except requests.exceptions.ConnectionError:
        yield f"Ollama is not running. Please run: ollama run {OLLAMA_MODEL}"
    except requests.exceptions.HTTPError as exc:
        body = exc.response.text.strip() if exc.response is not None else ""
        yield f"Ollama error: {exc}. {body}"
    except Exception as exc:
        yield f"Error: {exc}"


def _read_ollama_lines(resp) -> Iterable[str]:
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        data = json.loads(line)
        chunk = data.get("message", {}).get("content", "")
        if chunk:
            yield chunk
        if data.get("done"):
            break


def ask_ollama(user_text: str, history: list) -> str:
    reply = "".join(stream_ollama(user_text, history)).strip()
    if "<think>" in reply:
        reply = reply.split("</think>")[-1].strip()
    return reply or "Sorry, I didn't catch that. Can you repeat?"
