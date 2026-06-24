const WS_URL = `ws://${location.host}/ws`;
const BAR_COUNT = 9;

const avatar = document.getElementById("avatar");
const avatarZone = document.getElementById("listeningRow");
const barsEl = document.getElementById("bars");
const statusText = document.getElementById("statusText");
const thread = document.getElementById("thread");
const micBtn = document.getElementById("micBtn");
const textInput = document.getElementById("textInput");
const sendBtn = document.getElementById("sendBtn");
const messageForm = document.getElementById("messageForm");
const clearBtn = document.getElementById("clearBtn");
const connStatus = document.getElementById("connStatus");
const ttsAudio = document.getElementById("ttsAudio");

let ws = null;
let bootBanner = null;
let busy = false;
let audioUrl = null;
const renderedMessages = new Set();

for (let i = 0; i < BAR_COUNT; i += 1) {
  const bar = document.createElement("span");
  bar.className = "bar";
  barsEl.appendChild(bar);
}

function newMessageId(prefix) {
  if (crypto.randomUUID) return `${prefix}-${crypto.randomUUID()}`;
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function setState(state, label) {
  avatar.dataset.state = state;
  avatarZone.dataset.state = state;
  if (label !== undefined) statusText.textContent = label;
}

function setBusy(value) {
  busy = value;
  sendBtn.disabled = value;
  micBtn.disabled = value;
}

function addMessage(role, text, id) {
  if (!text) return;
  const messageId = id || `${role}-${text}`;
  if (renderedMessages.has(messageId)) return;
  renderedMessages.add(messageId);

  const row = document.createElement("div");
  row.className = `msg-row msg-row--${role}`;

  const bubble = document.createElement("div");
  bubble.className = `msg msg--${role}`;
  bubble.textContent = text;

  row.appendChild(bubble);
  thread.appendChild(row);
  thread.scrollTop = thread.scrollHeight;
}

function showBootBanner(text, kind) {
  if (!bootBanner) {
    bootBanner = document.createElement("div");
    bootBanner.className = "boot-banner";
    thread.appendChild(bootBanner);
  }
  bootBanner.hidden = false;
  bootBanner.dataset.kind = kind || "info";
  bootBanner.textContent = text;
  thread.scrollTop = thread.scrollHeight;
}

function hideBootBanner() {
  if (bootBanner) bootBanner.hidden = true;
}

function playAudio(base64Audio) {
  if (!base64Audio) return;
  ttsAudio.pause();
  ttsAudio.currentTime = 0;
  if (audioUrl) URL.revokeObjectURL(audioUrl);

  const bytes = Uint8Array.from(atob(base64Audio), (char) => char.charCodeAt(0));
  const blob = new Blob([bytes], { type: "audio/wav" });
  audioUrl = URL.createObjectURL(blob);
  ttsAudio.src = audioUrl;
  ttsAudio.play().catch(() => {});
}

function connect() {
  connStatus.dataset.state = "connecting";
  ws = new WebSocket(WS_URL);

  ws.addEventListener("open", () => {
    connStatus.dataset.state = "connected";
  });

  ws.addEventListener("close", () => {
    connStatus.dataset.state = "disconnected";
    setState("idle", "Disconnected");
    setBusy(false);
    setTimeout(connect, 2000);
  });

  ws.addEventListener("error", () => {
    connStatus.dataset.state = "disconnected";
  });

  ws.addEventListener("message", (ev) => {
    let msg;
    try {
      msg = JSON.parse(ev.data);
    } catch {
      return;
    }
    handleServerEvent(msg);
  });
}

function handleServerEvent(msg) {
  switch (msg.event) {
    case "booting":
      setState("thinking", "Warming up");
      showBootBanner(msg.detail || "Warming up", "info");
      break;

    case "boot_error":
      setState("idle", "Setup needed");
      showBootBanner(`Startup error: ${msg.detail || "unknown error"}`, "error");
      setBusy(false);
      break;

    case "listening":
      hideBootBanner();
      setState("listening", "Listening");
      micBtn.dataset.active = "true";
      setBusy(true);
      break;

    case "user_text":
      hideBootBanner();
      addMessage("user", msg.text, msg.message_id);
      break;

    case "thinking":
      setState("thinking", "Thinking");
      setBusy(true);
      break;

    case "speaking":
      setState("speaking", "Speaking");
      addMessage("reze", msg.text, msg.message_id);
      break;

    case "audio":
      playAudio(msg.audio);
      break;

    case "idle":
      setState("idle", "Ready");
      micBtn.dataset.active = "false";
      setBusy(false);
      textInput.focus();
      break;

    case "device_status":
      break;
  }
}

micBtn.addEventListener("click", () => {
  if (busy || !ws || ws.readyState !== WebSocket.OPEN) return;
  setBusy(true);
  ws.send(JSON.stringify({ type: "listen", client_id: newMessageId("voice") }));
});

messageForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = textInput.value.trim();
  if (busy || !text || !ws || ws.readyState !== WebSocket.OPEN) return;

  const clientId = newMessageId("text");
  setBusy(true);
  textInput.value = "";
  addMessage("user", text, clientId);
  ws.send(JSON.stringify({ type: "text", text, client_id: clientId }));
});

clearBtn.addEventListener("click", () => {
  thread.innerHTML = "";
  renderedMessages.clear();
  bootBanner = null;
});

setState("idle", "Ready");
connect();
