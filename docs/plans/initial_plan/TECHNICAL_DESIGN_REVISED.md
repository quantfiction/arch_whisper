# Technical Design Document (TDD): Arch Whisper (Ubuntu Wispr Flow Alternative)

**Version:** 2.1  
**Date:** 2026-01-14  
**Status:** Implementation-Ready (Beadable)  
**Inputs:** `docs/plans/initial_plan/ROUGH_PLAN.md`, `docs/plans/initial_plan/TECHNICAL_DESIGN.md` (v1.0)

---

## 1. Executive Summary

Arch Whisper is a lightweight Ubuntu desktop utility that transcribes speech to text via a **hold-to-record global hotkey** (`Ctrl+Space`), runs **local Whisper transcription** (CPU `int8`, no CUDA), optionally performs **Claude cleanup** using a Claude Max OAuth token, then **pastes the result into the currently-focused app** via clipboard + simulated `Ctrl+V`. It runs as a **system tray** process and supports both **X11 and Wayland**.

Primary UX loop:
- Hold `Ctrl+Space` → start recording + audible ding + tray turns red
- Release `Ctrl+Space` → transcribe (+ optional cleanup) + paste + tray turns gray

---

## 2. Goals, Non-Goals, Assumptions

### 2.1 Goals
- G-1: Global hold-to-record hotkey: press/hold starts recording; any release ends it.
- G-2: Local transcription using `faster-whisper` on CPU with good latency.
- G-3: Optional cleanup via Anthropic Messages API using Claude Max OAuth bearer token.
- G-4: Paste into any app reliably (best-effort under Wayland).
- G-5: Minimal UI: tray status indicator and actionable notifications.

### 2.2 Non-Goals
- NG-1: No full GUI settings panel (config file only).
- NG-2: No always-on dictation / wake word.
- NG-3: No multi-user daemon service.
- NG-4: No token refresh implementation (user re-authenticates via `claude` CLI).
- NG-5: No macOS/Windows support.

### 2.3 Assumptions
- A-1: Target OS: Ubuntu Desktop 22.04+ / 24.04+.
- A-2: Python 3.10+ available.
- A-3: User can install apt packages.
- A-4: Claude Max credentials file exists at `~/.claude/.credentials.json`.
- A-5: On Wayland, global hotkeys require `/dev/input` access (typically `input` group).

---

## 3. Requirements Specification

### 3.1 Functional Requirements
- FR-1 (Must): Hold `Ctrl+Space` to record mic audio.
- FR-2 (Must): Release hotkey to stop recording and start processing.
- FR-3 (Must): Tray icon shows Idle / Recording / Processing.
- FR-4 (Must): Play an audible ding at start of recording.
- FR-5 (Must): Run local transcription via `faster-whisper` CPU.
- FR-6 (Must): If Claude cleanup enabled and succeeds, paste cleaned text.
- FR-7 (Must): If Claude fails, paste raw transcription.
- FR-8 (Must): If simulated paste fails, still copy text to clipboard and notify.
- FR-9 (Must): X11 and Wayland support.
- FR-10 (Should): Provide preflight notifications for missing dependencies.
- FR-11 (Could): Whisper model/threads configurable.

### 3.2 Non-Functional Requirements
- NFR-1: Startup < 3s (lazy-load Whisper model).
- NFR-2: Idle CPU < 1%.
- NFR-3: Keep GTK UI responsive (no heavy work on GTK thread).
- NFR-4: Never log OAuth tokens.

### 3.3 Constraints
- C-1: CPU-only inference.
- C-2: Wayland hotkey requires evdev access.
- C-3: Wayland paste requires external tool (`wtype` preferred; `ydotool` fallback).
- C-4: Claude Max auth: read from local credential file; do not store elsewhere.

---

## 4. Architecture Overview

### 4.1 High-Level Pipeline
`Hotkey → AudioRecorder → WhisperTranscriber → (ClaudePostProcessor) → PasteBackend`

### 4.2 Modules
- `arch_whisper/app.py`: orchestrator + state machine
- `arch_whisper/config.py`: config load/save
- `arch_whisper/tray/indicator.py`: AppIndicator tray (GTK)
- `arch_whisper/notifications.py`: desktop notifications (libnotify)
- `arch_whisper/hotkey/{x11,wayland,manager}.py`
- `arch_whisper/audio/{recorder,player}.py`
- `arch_whisper/transcription/whisper.py`
- `arch_whisper/auth/claude_max.py`
- `arch_whisper/postprocess/claude.py`
- `arch_whisper/paste/{x11,wayland,manager}.py`
- `arch_whisper/__main__.py`: CLI entrypoint

### 4.3 State Machine
States:
- `IDLE` → `RECORDING` → `PROCESSING` (sub-steps: transcribe → cleanup → paste) → `IDLE`

Implementation detail:
- Keep public app state coarse (`IDLE/RECORDING/PROCESSING`) for tray UI.
- Internally track sub-step for debugging/notifications (optional).

---

## 5. Dependency Manifest

> Note: This repo currently contains plans only; the implementation will introduce the manifest below.

### 5.1 Python Dependencies (pyproject.toml target)
- Audio: `sounddevice>=0.5.0`, `numpy>=1.24.0`, `soundfile>=0.12.0`
- Transcription: `faster-whisper>=1.0.0`
- Claude: `anthropic>=0.40.0`
- Hotkey: `pynput>=1.7.6` (X11), `evdev>=1.6.0` (Wayland)
- Clipboard: `pyperclip>=1.8.2`

Dev:
- `pytest>=7`, `ruff>=0.1`, `mypy>=1`

### 5.2 System Dependencies (Ubuntu apt)
- GTK / indicator / notifications:
  - `python3-gi`, `python3-gi-cairo`, `gir1.2-gtk-3.0`, `gir1.2-ayatanaappindicator3-0.1`, `gir1.2-notify-0.7`
- Audio libs:
  - `libportaudio2`, `libsndfile1`
- X11 paste:
  - `xdotool`, `xclip` (or `xsel`)
- Wayland paste:
  - `wl-clipboard` (for `wl-copy`)
  - `wtype` (preferred)
  - Optional fallback: `ydotool`

### 5.3 Compatibility / Operational Notes
- GNOME tray requires extension “AppIndicator and KStatusNotifierItem Support”.
- `ydotool` may require `ydotoold` daemon and/or uinput permissions; treat as best-effort fallback and document explicitly.

---

## 6. External APIs / SDK Surface Verification

### 6.1 Anthropic Python SDK (Messages API)
- Use OAuth bearer token via `Anthropic(auth_token=token)`.
- Call:
  - `client.messages.create(model=..., max_tokens=..., messages=[...])`
- Read response text:
  - `response.content[0].text` (first text block)

Auth specifics:
- The Anthropic Python SDK supports `auth_token` which sends `Authorization: Bearer ...`.
- Environment variable fallback supported by SDK: `ANTHROPIC_AUTH_TOKEN`.

### 6.2 faster-whisper
- `WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=N)`
- `model.transcribe(audio, vad_filter=True, language=config.whisper_language)`

### 6.3 Wayland tooling
- Clipboard: `wl-copy` with stdin
- Keystroke injection: `wtype` preferred
- Fallback: `ydotool` (document requirements; do not assume it works without setup)

---

## 7. Data Flow

### 7.1 Recording → Text → Paste
1. User holds `Ctrl+Space`.
2. App transitions to RECORDING and starts audio capture.
3. User releases hotkey.
4. App stops capture, starts background worker:
   - Transcribe to raw
   - (Optional) Claude cleanup
   - Paste
5. App returns to IDLE.

### 7.2 Threading
- GTK main loop stays on main thread.
- Hotkey backends run in their own threads.
- Processing pipeline runs in a background thread.
- UI updates scheduled via `GLib.idle_add()`.

---

## 8. Edge Cases & Failure Modes

### 8.1 Hotkey edge cases
- Releasing Ctrl before Space (and vice versa) must stop recording exactly once.
- Key repeat events must not re-trigger recording.
- Wayland multiple keyboards: choose first device that advertises `KEY_SPACE`; document limitation.

### 8.2 Audio edge cases
- Very short recordings: transcribe anyway.
- Silence-only audio: Whisper VAD returns empty text; skip paste.
- Mic unplugged mid-recording: stop gracefully; transcribe what exists.

### 8.3 Paste edge cases
- App doesn’t support Ctrl+V: copy-only fallback.
- Clipboard race: add small delay between copy and paste.
- Wayland paste tool missing: notify; copy-only fallback.

### 8.4 Claude edge cases
- Missing credentials file: notify once per session; fallback to raw.
- Expired credentials: notify; fallback to raw.
- Rate limits/timeouts: fallback to raw.
- Empty or non-text response blocks: fallback to raw.

---

## 9. Security & Privacy

- Never log or display OAuth tokens.
- Treat evdev access as sensitive: only process relevant keycodes; do not store arbitrary keystrokes.
- Network access only to Anthropic endpoints when cleanup enabled.

---

## 10. Integration Points (OS + Desktop)

### 10.1 Session detection
- Use `XDG_SESSION_TYPE`:
  - `"x11"` → pynput/xdotool path
  - `"wayland"` → evdev/wl-copy/wtype path

### 10.2 Preflight checks (run at startup)
- Verify presence of required external binaries based on selected backend.
- If missing:
  - Show notification with install hint
  - Keep running in tray (so user can install and restart)

### 10.3 Asset loading
Decision (to make implementation deterministic):
- Use `importlib.resources` to load icons/sounds packaged with the Python distribution.
- Provide `assets_dir` override for dev mode and power users.

---

## 11. Testing Strategy

### 11.1 Unit tests
- `auth/claude_max.py`: parse/expiry
- `hotkey`: event sequencing, repeat filtering
- `paste`: tool detection + subprocess args
- `transcription`: empty input returns empty string

### 11.2 Manual testing checklist
- Verify tray appears.
- Hold/release hotkey triggers recording.
- Transcription pastes into a text box.
- Wayland permission guidance: `sudo usermod -aG input $USER` (logout/login).
- Claude cleanup works when credentials present.

---

## 12. Deployment & Packaging

### 12.1 Python packaging (uv)
- Use `uv` for environment management and reproducible installs.
- Commit both `pyproject.toml` and `uv.lock`.
- Install/sync deps with `uv sync --dev`.
- Run commands via `uv run ...`.
- Define console entry point: `arch-whisper`.
- Include assets in wheel.

### 12.2 Operating instructions (documented, not enforced)
- X11: install `xdotool` and clipboard tool.
- Wayland: install `wl-clipboard` + `wtype`; add user to `input` group.

---

## 13. Implementation Plan (Bead Mapping)

This section is intentionally written to be directly convertible into “beads” (file-scoped, independently executable tasks).

Bead 01 — Project scaffold
- Create `pyproject.toml`, package layout under `src/arch_whisper/`, console script.

Bead 02 — Config
- Implement `arch_whisper/config.py` with defaults, `load()`, optional `save()`.

Bead 03 — Tray + notifications
- Implement `arch_whisper/tray/indicator.py` and `arch_whisper/notifications.py`.

Bead 04 — Audio capture + ding
- Implement `arch_whisper/audio/recorder.py` and `arch_whisper/audio/player.py`.

Bead 05 — Whisper transcription
- Implement `arch_whisper/transcription/whisper.py` with lazy model initialization.

Bead 06 — Hotkey backends
- Implement `arch_whisper/hotkey/x11.py`, `arch_whisper/hotkey/wayland.py`, `arch_whisper/hotkey/manager.py`.

Bead 07 — Paste backends
- Implement `arch_whisper/paste/x11.py`, `arch_whisper/paste/wayland.py`, `arch_whisper/paste/manager.py`.

Bead 08 — Claude auth + postprocess
- Implement `arch_whisper/auth/claude_max.py`, `arch_whisper/postprocess/claude.py`.

Bead 09 — App orchestrator
- Implement `arch_whisper/app.py` state machine and threading.

Bead 10 — Entrypoint + preflight
- Implement `arch_whisper/__main__.py` startup, dependency checks, and graceful error notifications.

Bead 11 — Tests
- Add unit tests using pytest according to Section 11.
- Run with `uv run pytest`.

---

## 14. Verification Procedure

### 14.1 Preflight checks (manual)
- Sync Python deps (recommended): `uv sync --dev`
- Verify installed tools:
  - X11: `which xdotool xclip`
  - Wayland: `which wl-copy wtype`
- Verify Claude credentials (optional): `jq '.claudeAiOauth.subscriptionType' ~/.claude/.credentials.json`. 

### 14.2 Functional validation
1. Start `uv run arch-whisper`.
2. Confirm tray icon appears.
3. Focus a text editor.
4. Hold `Ctrl+Space`: ding + tray recording.
5. Speak a sentence.
6. Release: tray processing then idle.
7. Confirm text appears.

### 14.3 Failure-mode validation
- Disable network → still pastes raw transcription.
- Remove `wtype` on Wayland → copies to clipboard + notification.
- Expire Claude token / remove credentials → raw transcription + notification.

---

## Appendix: Explicit Open Questions (Non-blocking)

These are safe to defer until after initial beads are written; they do not block implementation.
- Should we support language auto-detect by default (`language=None`) vs forcing `"en"`?
- Do we want a CLI flag `--no-claude` to override config?
- Should we implement a single-threaded worker queue to avoid parallel processing if user triggers hotkey rapidly?
