// ════════════════════════════════════════════════════════════════════
// Reze — frontend controller (chat-window layout)
// ════════════════════════════════════════════════════════════════════

const WS_URL = `ws://${location.host}/ws`;
const BAR_COUNT = 9;

const avatar      = document.getElementById("avatar");
const avatarZone   = document.getElementById("listeningRow").parentElement; // .avatar-zone
const barsEl      = document.getElementById("bars");
const statusText  = document.getElementById("statusText");
const thread      = document.getElementById("thread");
const micBtn      = document.getElementById("micBtn");
const textInput   = document.getElementById("textInput");
const sendBtn     = document.getElementById("sendBtn");
const connStatus  = document.getElementById("connStatus");
const ttsAudio    = document.getElementById("ttsAudio");

let ws = null;
let bootBanner = null;

// ── Build the bar row ──────────────────────────────────────────────
for (let i = 0; i < BAR_COUNT; i++) {
  const bar = document.createElement("span");
  bar.className = "bar";
  barsEl.appendChild(bar);
}

function setState(state, label) {
  avatar.dataset.state = state;
  avatarZone.dataset.state = state;
  if (label !== undefined) statusText.textContent = label;
}

function addMessage(role, text) {
  if (!text) return;
  const div = document.createElement("div");
  div.className = `msg msg--${role}`;
  div.textContent = text;
  thread.appendChild(div);
  thread.scrollTop = thread.scrollHeight;
}

function showBootBanner(text, kind) {
  if (!bootBanner) {
    bootBanner = document.createElement("div");
    bootBanner.className = "boot-banner";
    thread.parentElement.insertBefore(bootBanner, thread);
  }
  bootBanner.hidden = false;
  bootBanner.dataset.kind = kind || "info";
  bootBanner.textContent = text;
}

function hideBootBanner() {
  if (bootBanner) bootBanner.hidden = true;
}

// ── WebSocket ──────────────────────────────────────────────────────
function connect() {
  connStatus.dataset.state = "connecting";
  ws = new WebSocket(WS_URL);

  ws.addEventListener("open", () => {
    connStatus.dataset.state = "connected";
  });

  ws.addEventListener("close", () => {
    connStatus.dataset.state = "disconnected";
    setState("idle", "Disconnected");
    setTimeout(connect, 2000);
  });

  ws.addEventListener("error", () => {
    connStatus.dataset.state = "disconnected";
  });

  ws.addEventListener("message", (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }
    handleServerEvent(msg);
  });
}

function handleServerEvent(msg) {
  switch (msg.event) {
    case "booting":
      setState("thinking", "Warming up…");
      showBootBanner(msg.detail || "Warming up…", "info");
      break;

    case "boot_error":
      setState("idle", "Setup needed");
      showBootBanner(
        "Reze couldn't start its speech engine: " + (msg.detail || "unknown error") +
        ". You can still type messages below.",
        "error"
      );
      break;

    case "listening":
      hideBootBanner();
      setState("listening", "Listening…");
      micBtn.dataset.active = "true";
      break;

    case "user_text":
      hideBootBanner();
      if (msg.text) addMessage("user", msg.text);
      break;

    case "thinking":
      setState("thinking", "Thinking…");
      break;

    case "speaking":
      setState("speaking", "Speaking…");
      if (msg.text) addMessage("reze", msg.text);
      break;

    case "audio":
      if (msg.audio) {
        ttsAudio.src = `data:audio/wav;base64,${msg.audio}`;
        ttsAudio.play().catch(() => {});
      }
      break;

    case "idle":
      setState("idle", "Tap to speak");
      micBtn.dataset.active = "false";
      break;

    case "device_status":
      break;
  }
}

// ── Interactions ───────────────────────────────────────────────────
micBtn.addEventListener("click", () => {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ type: "listen", seconds: 5 }));
});

function sendTypedMessage() {
  const text = textInput.value.trim();
  if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
  addMessage("user", text);
  ws.send(JSON.stringify({ type: "text", text }));
  textInput.value = "";
}

sendBtn.addEventListener("click", sendTypedMessage);
textInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendTypedMessage();
});

// ── Init ───────────────────────────────────────────────────────────
setState("idle", "Tap to speak");
connect();
