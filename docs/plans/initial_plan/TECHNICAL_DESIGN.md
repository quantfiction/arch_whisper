# Technical Design Document: Arch Whisper

**Version:** 1.0
**Date:** 2025-01-14
**Status:** Implementation-Ready

---

## 1. Executive Summary

Arch Whisper is a Wispr Flow alternative for Ubuntu Desktop providing voice-to-text transcription with a hold-to-record hotkey (Ctrl+Space), local Whisper transcription, Claude-powered post-processing, and seamless paste-anywhere functionality.

**Key Capabilities:**
- Global Ctrl+Space hold-to-record hotkey (X11 and Wayland)
- Local faster-whisper transcription (CPU int8, no CUDA required)
- Claude API post-processing for text cleanup (Claude Max OAuth auth)
- System tray with visual state indicator + audible recording feedback
- Paste to any application via clipboard + simulated Ctrl+V

---

## 2. Requirements Specification

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Hold Ctrl+Space to record audio | Must |
| FR-2 | Release to transcribe and paste at cursor | Must |
| FR-3 | System tray icon shows idle/recording/processing states | Must |
| FR-4 | Audible "ding" when recording starts | Must |
| FR-5 | Post-process transcription via Claude for cleanup | Must |
| FR-6 | Work on both X11 and Wayland | Must |
| FR-7 | Fall back to raw transcription if Claude fails | Should |
| FR-8 | Configurable Whisper model size | Could |

### 2.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Transcription latency | < 5s for 30s audio |
| NFR-2 | Memory footprint | < 500MB (base model) |
| NFR-3 | Startup time | < 3s (model lazy-loaded) |
| NFR-4 | CPU usage during idle | < 1% |

### 2.3 Constraints

- **No CUDA:** AMD GPUs only; must use CPU inference
- **Ubuntu Desktop:** Primary target (22.04+, 24.04+)
- **Claude Max Auth:** Uses OAuth tokens from `~/.claude/.credentials.json`
- **Wayland permissions:** Requires user in `input` group for evdev access

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Application Layer                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ __main__.py │→ │   app.py    │→ │  config.py  │  │   tray/     │    │
│  │ Entry Point │  │ Controller  │  │   Config    │  │ indicator   │    │
│  └─────────────┘  └──────┬──────┘  └─────────────┘  └─────────────┘    │
│                          │                                              │
├──────────────────────────┼──────────────────────────────────────────────┤
│                    Component Layer                                       │
│  ┌─────────────┐  ┌──────┴──────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   hotkey/   │  │   audio/    │  │transcription│  │ postprocess/│    │
│  │  manager    │  │  recorder   │  │   whisper   │  │   claude    │    │
│  └──────┬──────┘  └─────────────┘  └─────────────┘  └──────┬──────┘    │
│         │                                                   │           │
│  ┌──────┴──────┐                                    ┌──────┴──────┐    │
│  │ x11 │wayland│                                    │    auth/    │    │
│  └─────────────┘                                    │ claude_max  │    │
│                                                     └─────────────┘    │
│  ┌─────────────┐                                                       │
│  │   paste/    │                                                       │
│  │  manager    │                                                       │
│  └──────┬──────┘                                                       │
│  ┌──────┴──────┐                                                       │
│  │ x11 │wayland│                                                       │
│  └─────────────┘                                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                     External Dependencies                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │ pynput   │ │  evdev   │ │sounddevice│ │faster-   │ │anthropic │     │
│  │ (X11)    │ │(Wayland) │ │          │ │whisper   │ │  SDK     │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.1 State Machine

```
     ┌──────────────────────────────────────────────────────────────┐
     │                                                              │
     ▼                                                              │
  ┌──────┐  key_down   ┌───────────┐  key_up   ┌─────────────┐     │
  │ IDLE │───────────→ │ RECORDING │─────────→ │ TRANSCRIBING│     │
  └──────┘             └───────────┘           └──────┬──────┘     │
     ▲                                                │            │
     │                                                ▼            │
     │                 ┌───────────┐            ┌──────────────┐   │
     │                 │  PASTING  │←───────────│POSTPROCESSING│   │
     │                 └─────┬─────┘            └──────────────┘   │
     │                       │                                     │
     │                       │ done                                │
     └───────────────────────┴─────────────────────────────────────┘
                             │
                          [error at any stage → return to IDLE]
```

---

## 4. Dependency Manifest

### 4.1 Python Dependencies (pyproject.toml)

```toml
[project]
name = "arch-whisper"
version = "0.1.0"
description = "Voice transcription with hold-to-record hotkey for Ubuntu"
requires-python = ">=3.10"
dependencies = [
    # Audio recording
    "sounddevice>=0.5.0",
    "numpy>=1.24.0",
    "soundfile>=0.12.0",          # For WAV playback

    # Transcription
    "faster-whisper>=1.0.0",

    # Claude API
    "anthropic>=0.40.0",

    # Hotkey detection
    "pynput>=1.7.6",              # X11 backend
    "evdev>=1.6.0",               # Wayland backend

    # Clipboard
    "pyperclip>=1.8.2",           # X11 clipboard abstraction
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]

[project.scripts]
arch-whisper = "arch_whisper.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/arch_whisper"]
```

### 4.2 System Dependencies (apt)

```bash
# GTK and AppIndicator (system Python bindings)
sudo apt install python3-gi python3-gi-cairo \
    gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 \
    gir1.2-notify-0.7

# Audio libraries
sudo apt install libportaudio2 libsndfile1

# X11 paste tool
sudo apt install xdotool xclip

# Wayland paste tools
sudo apt install wl-clipboard wtype
# OR as fallback: sudo apt install ydotool
```

### 4.3 Verified Dependency Versions

| Package | Min Version | Verified API | Notes |
|---------|-------------|--------------|-------|
| faster-whisper | 1.0.0 | `WhisperModel`, `transcribe()` | int8 on CPU confirmed |
| anthropic | 0.40.0 | `auth_token` param | OAuth token auth confirmed |
| pynput | 1.7.6 | `keyboard.Listener`, `HotKey` | X11 confirmed |
| evdev | 1.6.0 | `InputDevice`, `read_loop()` | Wayland/evdev confirmed |
| sounddevice | 0.5.0 | `InputStream`, callback | float32 @ 16kHz confirmed |
| PyGObject | 3.42.0 | `AyatanaAppIndicator3` | Ubuntu system package |

---

## 5. Component Specifications

### 5.1 Auth Module (`auth/claude_max.py`)

**Purpose:** Read Claude Max OAuth credentials from Claude Code's credential store.

**Interface:**
```python
@dataclass
class ClaudeCredentials:
    access_token: str
    refresh_token: str
    expires_at: int  # milliseconds since epoch

    @property
    def is_expired(self) -> bool: ...

def load_claude_credentials() -> ClaudeCredentials | None:
    """Load credentials from ~/.claude/.credentials.json"""
```

**Credential File Structure:**
```json
{
  "claudeAiOauth": {
    "accessToken": "sk-ant-oat01-...",
    "refreshToken": "sk-ant-ort01-...",
    "expiresAt": 1768435176304,
    "scopes": ["user:inference", "user:profile", "user:sessions:claude_code"],
    "subscriptionType": "max",
    "rateLimitTier": "default_claude_max_20x"
  }
}
```

**Error Handling:**
- File not found → return None
- Invalid JSON → return None
- Missing `claudeAiOauth` key → return None
- Caller must handle None and prompt user to authenticate with `claude` CLI

---

### 5.2 Audio Recorder (`audio/recorder.py`)

**Purpose:** Record audio from microphone while hotkey is held.

**Interface:**
```python
class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, channels: int = 1): ...
    def start(self) -> None: ...
    def stop(self) -> np.ndarray: ...  # Returns float32 array
```

**Implementation Details:**
```python
def __init__(self, sample_rate: int = 16000, channels: int = 1):
    self.sample_rate = sample_rate
    self.channels = channels
    self._buffer: list[np.ndarray] = []
    self._lock = threading.Lock()
    self._stream: sd.InputStream | None = None

def _audio_callback(self, indata: np.ndarray, frames: int,
                    time: Any, status: sd.CallbackFlags) -> None:
    """Called by sounddevice for each audio block."""
    if status:
        print(f"Audio status: {status}")
    with self._lock:
        self._buffer.append(indata.copy())

def start(self) -> None:
    with self._lock:
        self._buffer = []
    self._stream = sd.InputStream(
        samplerate=self.sample_rate,
        channels=self.channels,
        dtype='float32',
        callback=self._audio_callback
    )
    self._stream.start()

def stop(self) -> np.ndarray:
    if self._stream:
        self._stream.stop()
        self._stream.close()
        self._stream = None
    with self._lock:
        if not self._buffer:
            return np.array([], dtype='float32')
        audio = np.concatenate(self._buffer, axis=0)
        self._buffer = []
    return audio.flatten()  # Return 1D mono array
```

**Audio Format:**
- Sample rate: 16000 Hz (required by Whisper)
- Channels: 1 (mono)
- Dtype: float32, normalized [-1.0, 1.0]

---

### 5.3 Audio Player (`audio/player.py`)

**Purpose:** Play audible feedback sound when recording starts.

**Interface:**
```python
class SoundPlayer:
    def __init__(self, assets_dir: Path): ...
    def play_ding(self) -> None: ...  # Non-blocking
```

**Implementation:**
```python
import sounddevice as sd
import soundfile as sf

class SoundPlayer:
    def __init__(self, assets_dir: Path):
        ding_path = assets_dir / "ding.wav"
        if ding_path.exists():
            self._ding_data, self._ding_sr = sf.read(ding_path)
        else:
            self._ding_data = None
            self._ding_sr = None

    def play_ding(self) -> None:
        if self._ding_data is not None:
            sd.play(self._ding_data, self._ding_sr)
            # Non-blocking - returns immediately
```

---

### 5.4 Whisper Transcriber (`transcription/whisper.py`)

**Purpose:** Transcribe audio to text using faster-whisper.

**Interface:**
```python
class WhisperTranscriber:
    def __init__(self, model_size: str = "base",
                 compute_type: str = "int8",
                 cpu_threads: int = 4): ...
    def transcribe(self, audio: np.ndarray) -> str: ...
```

**Implementation:**
```python
from faster_whisper import WhisperModel
import os

class WhisperTranscriber:
    def __init__(self, model_size: str = "base",
                 compute_type: str = "int8",
                 cpu_threads: int = 4):
        self.model_size = model_size
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads
        self._model: WhisperModel | None = None
        os.environ["OMP_NUM_THREADS"] = str(cpu_threads)

    def _ensure_model(self) -> WhisperModel:
        if self._model is None:
            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads
            )
        return self._model

    def transcribe(self, audio: np.ndarray) -> str:
        if len(audio) == 0:
            return ""

        model = self._ensure_model()

        # Ensure float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        segments, info = model.transcribe(
            audio,
            beam_size=5,
            language="en",
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": 500,
                "threshold": 0.5
            }
        )

        # Collect segments (generator must be consumed)
        text_parts = [segment.text.strip() for segment in segments]
        return " ".join(text_parts)
```

**Model Sizes:**
| Model | Size | CPU Speed | Recommended Use |
|-------|------|-----------|-----------------|
| tiny | 39MB | ~1x realtime | Quick tests |
| base | 74MB | ~2x realtime | **Default choice** |
| small | 244MB | ~4x realtime | Better accuracy |
| medium | 769MB | ~8x realtime | High accuracy |

---

### 5.5 Claude Post-Processor (`postprocess/claude.py`)

**Purpose:** Clean up transcription using Claude API.

**Interface:**
```python
class ClaudePostProcessor:
    def __init__(self): ...
    def process(self, raw_text: str) -> str: ...
```

**Implementation:**
```python
from anthropic import Anthropic
from ..auth.claude_max import load_claude_credentials

CLEANUP_PROMPT = """Clean up this transcription:
1. Fix obvious transcription errors
2. Add proper punctuation and capitalization
3. Remove excessive filler words (um, uh, like)
4. Do NOT change meaning or add content
5. Keep the speaker's voice and style

Transcription: {text}

Return only the cleaned text."""

class ClaudePostProcessor:
    def __init__(self):
        self._client: Anthropic | None = None

    def _get_client(self) -> Anthropic:
        if self._client is None:
            creds = load_claude_credentials()
            if creds is None:
                raise RuntimeError(
                    "Claude credentials not found. Run 'claude' to authenticate."
                )
            if creds.is_expired:
                raise RuntimeError(
                    "Claude token expired. Run 'claude' to re-authenticate."
                )
            # Use auth_token parameter for OAuth Bearer authentication
            self._client = Anthropic(auth_token=creds.access_token)
        return self._client

    def process(self, raw_text: str) -> str:
        if not raw_text.strip():
            return ""

        client = self._get_client()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": CLEANUP_PROMPT.format(text=raw_text)
            }]
        )
        return response.content[0].text
```

**API Authentication:**
- Uses `auth_token` parameter (not `api_key`)
- Token format: `sk-ant-oat01-...` (OAuth access token)
- Sends as `Authorization: Bearer {token}` header

---

### 5.6 Hotkey Manager (`hotkey/manager.py`)

**Purpose:** Detect global Ctrl+Space hold/release events.

**Interface:**
```python
class HotkeyBackend(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...

def create_hotkey_backend(
    on_press: Callable[[], None],
    on_release: Callable[[], None]
) -> HotkeyBackend: ...
```

**X11 Backend (`hotkey/x11.py`):**
```python
from pynput import keyboard

class X11HotkeyBackend:
    def __init__(self, on_press: Callable, on_release: Callable):
        self.on_press = on_press
        self.on_release = on_release
        self._listener: keyboard.Listener | None = None
        self._ctrl_pressed = False
        self._space_pressed = False
        self._recording = False

    def start(self) -> None:
        self._listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _on_key_press(self, key):
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self._ctrl_pressed = True
        elif key == keyboard.Key.space and self._ctrl_pressed:
            if not self._recording:
                self._recording = True
                self.on_press()

    def _on_key_release(self, key):
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self._ctrl_pressed = False
            if self._recording:
                self._recording = False
                self.on_release()
        elif key == keyboard.Key.space:
            if self._recording:
                self._recording = False
                self.on_release()
```

**Wayland Backend (`hotkey/wayland.py`):**
```python
import evdev
from evdev import ecodes
import threading

class WaylandHotkeyBackend:
    # Key codes
    KEY_LEFTCTRL = ecodes.KEY_LEFTCTRL    # 29
    KEY_RIGHTCTRL = ecodes.KEY_RIGHTCTRL  # 97
    KEY_SPACE = ecodes.KEY_SPACE          # 57

    def __init__(self, on_press: Callable, on_release: Callable):
        self.on_press = on_press
        self.on_release = on_release
        self._running = False
        self._thread: threading.Thread | None = None
        self._ctrl_pressed = False
        self._recording = False

    def _find_keyboard(self) -> evdev.InputDevice | None:
        for path in evdev.list_devices():
            device = evdev.InputDevice(path)
            caps = device.capabilities()
            if ecodes.EV_KEY in caps:
                keys = caps[ecodes.EV_KEY]
                if ecodes.KEY_SPACE in keys:
                    return device
        return None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _listen_loop(self) -> None:
        device = self._find_keyboard()
        if not device:
            raise RuntimeError("No keyboard found. Ensure user is in 'input' group.")

        for event in device.read_loop():
            if not self._running:
                break

            if event.type != ecodes.EV_KEY:
                continue

            # event.value: 1=press, 0=release, 2=repeat
            if event.code in (self.KEY_LEFTCTRL, self.KEY_RIGHTCTRL):
                self._ctrl_pressed = (event.value == 1)
                if event.value == 0 and self._recording:
                    self._recording = False
                    self.on_release()

            elif event.code == self.KEY_SPACE and self._ctrl_pressed:
                if event.value == 1 and not self._recording:
                    self._recording = True
                    self.on_press()
                elif event.value == 0 and self._recording:
                    self._recording = False
                    self.on_release()
```

**Manager (`hotkey/manager.py`):**
```python
import os

def create_hotkey_backend(on_press, on_release):
    session_type = os.environ.get('XDG_SESSION_TYPE', 'x11')

    if session_type == 'wayland':
        from .wayland import WaylandHotkeyBackend
        return WaylandHotkeyBackend(on_press, on_release)
    else:
        from .x11 import X11HotkeyBackend
        return X11HotkeyBackend(on_press, on_release)
```

---

### 5.7 Paste Manager (`paste/manager.py`)

**Purpose:** Paste text at cursor position in any application.

**Interface:**
```python
class PasteBackend(Protocol):
    def paste_text(self, text: str) -> None: ...

def create_paste_backend() -> PasteBackend: ...
```

**X11 Backend (`paste/x11.py`):**
```python
import subprocess
import pyperclip
import time

class X11PasteBackend:
    def paste_text(self, text: str) -> None:
        # Copy to clipboard
        pyperclip.copy(text)
        time.sleep(0.05)  # Allow clipboard to settle

        # Simulate Ctrl+V
        subprocess.run(
            ['xdotool', 'key', '--clearmodifiers', 'ctrl+v'],
            check=True,
            capture_output=True
        )
```

**Wayland Backend (`paste/wayland.py`):**
```python
import subprocess
import shutil
import time

class WaylandPasteBackend:
    def __init__(self):
        self._wl_copy = shutil.which('wl-copy')
        self._wtype = shutil.which('wtype')
        self._ydotool = shutil.which('ydotool')

        if not self._wl_copy:
            raise RuntimeError("wl-copy not found. Install: sudo apt install wl-clipboard")
        if not self._wtype and not self._ydotool:
            raise RuntimeError("Neither wtype nor ydotool found. Install one.")

    def paste_text(self, text: str) -> None:
        # Copy to Wayland clipboard
        proc = subprocess.Popen(['wl-copy'], stdin=subprocess.PIPE, text=True)
        proc.communicate(input=text)

        time.sleep(0.05)

        # Simulate Ctrl+V
        if self._wtype:
            # wtype: -M ctrl = press ctrl, -k v = tap v, -m ctrl = release ctrl
            subprocess.run(
                ['wtype', '-M', 'ctrl', '-k', 'v', '-m', 'ctrl'],
                check=True,
                capture_output=True
            )
        elif self._ydotool:
            # ydotool: 29=KEY_LEFTCTRL, 47=KEY_V
            # Format: keycode:state (1=press, 0=release)
            subprocess.run(
                ['ydotool', 'key', '29:1', '47:1', '47:0', '29:0'],
                check=True,
                capture_output=True
            )
```

---

### 5.8 System Tray (`tray/indicator.py`)

**Purpose:** Show application status in system tray.

**Interface:**
```python
class TrayState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"

class SystemTrayIndicator:
    def __init__(self, assets_dir: Path, on_quit: Callable): ...
    def set_state(self, state: TrayState) -> None: ...
    def run(self) -> None: ...  # Blocking - runs GTK main loop
    def quit(self) -> None: ...
```

**Implementation:**
```python
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, AyatanaAppIndicator3, GLib

class SystemTrayIndicator:
    def __init__(self, assets_dir: Path, on_quit: Callable):
        self.assets_dir = assets_dir
        self.on_quit = on_quit

        self.indicator = AyatanaAppIndicator3.Indicator.new(
            "arch-whisper",
            str(assets_dir / "icon_idle.png"),
            AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self._build_menu())

    def _build_menu(self) -> Gtk.Menu:
        menu = Gtk.Menu()

        self.status_item = Gtk.MenuItem(label="Ready")
        self.status_item.set_sensitive(False)
        menu.append(self.status_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _: self.on_quit())
        menu.append(quit_item)

        menu.show_all()
        return menu

    def set_state(self, state: TrayState) -> None:
        """Thread-safe state update."""
        def update():
            icon_map = {
                TrayState.IDLE: ("icon_idle.png", "Ready"),
                TrayState.RECORDING: ("icon_recording.png", "Recording..."),
                TrayState.PROCESSING: ("icon_processing.png", "Processing..."),
            }
            icon_file, status_text = icon_map[state]
            self.indicator.set_icon_full(
                str(self.assets_dir / icon_file),
                status_text
            )
            self.status_item.set_label(status_text)
            return False  # Don't repeat

        GLib.idle_add(update)

    def run(self) -> None:
        Gtk.main()

    def quit(self) -> None:
        GLib.idle_add(Gtk.main_quit)
```

**Threading:** GTK is not thread-safe. All UI updates from background threads must use `GLib.idle_add()`.

---

### 5.9 Main Controller (`app.py`)

**Purpose:** Orchestrate all components via state machine.

```python
import threading
from enum import Enum, auto
from pathlib import Path

class AppState(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()
    POSTPROCESSING = auto()
    PASTING = auto()

class ArchWhisperApp:
    def __init__(self, assets_dir: Path):
        self.assets_dir = assets_dir
        self.state = AppState.IDLE
        self._lock = threading.Lock()

        # Initialize components
        self.hotkey = create_hotkey_backend(
            on_press=self._on_record_start,
            on_release=self._on_record_stop
        )
        self.recorder = AudioRecorder()
        self.sound_player = SoundPlayer(assets_dir)
        self.transcriber = WhisperTranscriber()
        self.postprocessor = ClaudePostProcessor()
        self.paste = create_paste_backend()
        self.tray = SystemTrayIndicator(
            assets_dir=assets_dir,
            on_quit=self._on_quit
        )
        self._running = False

    def run(self) -> None:
        self._running = True
        self.hotkey.start()
        self.tray.run()  # Blocking

    def _on_record_start(self) -> None:
        with self._lock:
            if self.state != AppState.IDLE:
                return
            self.state = AppState.RECORDING

        self.tray.set_state(TrayState.RECORDING)
        self.sound_player.play_ding()
        self.recorder.start()

    def _on_record_stop(self) -> None:
        with self._lock:
            if self.state != AppState.RECORDING:
                return
            self.state = AppState.TRANSCRIBING

        self.tray.set_state(TrayState.PROCESSING)
        audio = self.recorder.stop()

        # Process in background
        threading.Thread(
            target=self._process_audio,
            args=(audio,),
            daemon=True
        ).start()

    def _process_audio(self, audio: np.ndarray) -> None:
        try:
            # Transcribe
            raw_text = self.transcriber.transcribe(audio)

            if not raw_text.strip():
                self._finish()
                return

            # Post-process
            with self._lock:
                self.state = AppState.POSTPROCESSING

            try:
                cleaned_text = self.postprocessor.process(raw_text)
            except Exception:
                # Fallback to raw transcription
                cleaned_text = raw_text

            # Paste
            with self._lock:
                self.state = AppState.PASTING

            self.paste.paste_text(cleaned_text)

        except Exception as e:
            print(f"Error: {e}")
        finally:
            self._finish()

    def _finish(self) -> None:
        with self._lock:
            self.state = AppState.IDLE
        self.tray.set_state(TrayState.IDLE)

    def _on_quit(self) -> None:
        self._running = False
        self.hotkey.stop()
        self.tray.quit()
```

---

## 6. Data Flow

```
┌────────────┐   Ctrl+Space held    ┌────────────┐   audio chunks    ┌────────────┐
│   User     │ ─────────────────────▶│  Hotkey    │ ─────────────────▶│  Audio     │
│ (keyboard) │                       │  Backend   │                   │  Recorder  │
└────────────┘                       └────────────┘                   └─────┬──────┘
                                                                            │
                                                                            │ np.ndarray
                                                                            │ float32 16kHz
                                                                            ▼
┌────────────┐   cleaned text       ┌────────────┐   raw text        ┌────────────┐
│   Paste    │ ◀─────────────────────│  Claude    │ ◀─────────────────│  Whisper   │
│  Backend   │                       │  Postproc  │                   │ Transcriber│
└─────┬──────┘                       └────────────┘                   └────────────┘
      │
      │ clipboard + Ctrl+V
      ▼
┌────────────┐
│  Target    │
│Application │
└────────────┘
```

---

## 7. Error Handling Strategy

### 7.1 Error Categories

| Category | Examples | Recovery |
|----------|----------|----------|
| **Config Errors** | Missing credentials, missing tools | Show error dialog, exit |
| **Runtime Errors** | API timeout, paste failure | Fallback, notify user |
| **Fatal Errors** | No audio device, GTK init failure | Log, exit |

### 7.2 Fallback Behaviors

| Failure Point | Fallback Action |
|---------------|-----------------|
| Claude API timeout/error | Use raw transcription |
| Claude token expired | Show notification, use raw text |
| Paste tool fails | Copy to clipboard, show notification |
| Empty transcription | Return to idle silently |
| No keyboard device (Wayland) | Show error about `input` group |

### 7.3 Desktop Notifications

```python
import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify

class NotificationManager:
    def __init__(self):
        Notify.init("arch-whisper")

    def show_error(self, title: str, message: str) -> None:
        notification = Notify.Notification.new(title, message, "dialog-error")
        notification.show()

    def show_info(self, title: str, message: str) -> None:
        notification = Notify.Notification.new(title, message, "dialog-information")
        notification.show()
```

---

## 8. Edge Cases

### 8.1 Hotkey Edge Cases

| Edge Case | Handling |
|-----------|----------|
| User releases Space before Ctrl | Trigger release callback |
| User releases Ctrl before Space | Trigger release callback |
| Rapid key repeat events | Filter: only first press, only final release |
| Multiple keyboards connected | Use first device with KEY_SPACE capability |
| Hotkey held for very long time | No timeout; record until release |
| Application not focused | Works (global hotkey) |

### 8.2 Audio Edge Cases

| Edge Case | Handling |
|-----------|----------|
| No audio device | Raise error on init with helpful message |
| Very short recording (<0.5s) | Transcribe anyway; Whisper handles it |
| Very long recording (>5min) | No limit; memory is primary constraint |
| Microphone unplugged mid-recording | Stop cleanly, return buffered audio |
| Silence only | VAD filters it; return empty string |

### 8.3 Clipboard Edge Cases

| Edge Case | Handling |
|-----------|----------|
| Target app doesn't support Ctrl+V | User must paste manually |
| Clipboard manager interference | 50ms delay between copy and paste |
| Very long text (>100KB) | No special handling; OS clipboard limits apply |
| Special characters / Unicode | Handled transparently by clipboard |

### 8.4 Claude API Edge Cases

| Edge Case | Handling |
|-----------|----------|
| Token expired | Catch error, fallback to raw text, notify user |
| Rate limited | Retry once after 1s, then fallback |
| API timeout (>30s) | Use raw transcription |
| Empty response | Use raw transcription |
| Malformed response | Use raw transcription |

---

## 9. Security Considerations

### 9.1 Credential Handling

- OAuth tokens read from `~/.claude/.credentials.json` (mode 0600)
- Never log or display tokens
- Tokens transmitted only to Anthropic API endpoints
- No token caching beyond credential file

### 9.2 Input Validation

- Audio: Accept only float32 numpy arrays
- Transcription: Sanitize before sending to Claude (limit length)
- Paste: No shell injection risk (tools invoked with explicit args)

### 9.3 Permissions

- Wayland evdev requires `input` group membership
- No root/sudo required at runtime
- No network access except Anthropic API

---

## 10. Testing Strategy

### 10.1 Unit Tests

| Component | Test Focus |
|-----------|------------|
| `auth/claude_max.py` | Credential parsing, expiry detection |
| `audio/recorder.py` | Buffer management, thread safety |
| `transcription/whisper.py` | Model loading, empty input handling |
| `hotkey/*.py` | State machine transitions |
| `paste/*.py` | Tool detection, error handling |

### 10.2 Integration Tests

```python
# tests/test_integration.py

def test_audio_to_transcription():
    """Record 3s test audio, verify transcription."""
    recorder = AudioRecorder()
    recorder.start()
    time.sleep(3)
    audio = recorder.stop()

    transcriber = WhisperTranscriber(model_size="tiny")
    text = transcriber.transcribe(audio)

    assert len(text) > 0

def test_x11_backend_detection():
    """Verify correct backend selected on X11."""
    os.environ['XDG_SESSION_TYPE'] = 'x11'
    backend = create_hotkey_backend(lambda: None, lambda: None)
    assert isinstance(backend, X11HotkeyBackend)
```

### 10.3 Manual Testing Checklist

1. [ ] Start app, verify tray icon appears (gray)
2. [ ] Hold Ctrl+Space, verify ding + red icon
3. [ ] Speak clearly for 5 seconds
4. [ ] Release, verify yellow icon during processing
5. [ ] Verify text pastes at cursor
6. [ ] Verify icon returns to gray
7. [ ] Test in: terminal, browser text field, VS Code
8. [ ] Test with Claude API disabled (fallback)
9. [ ] Test on Wayland session
10. [ ] Test quit from tray menu

---

## 11. Project Structure

```
arch_whisper/
├── pyproject.toml
├── README.md
├── docs/
│   └── plans/
│       ├── initial_plan/
│       │   └── ROUGH_PLAN.md
│       └── technical_design/
│           └── TDD.md              # This document
├── assets/
│   ├── icon_idle.png               # Gray microphone icon
│   ├── icon_recording.png          # Red microphone icon
│   ├── icon_processing.png         # Yellow microphone icon
│   └── ding.wav                    # Recording start sound
├── src/
│   └── arch_whisper/
│       ├── __init__.py
│       ├── __main__.py             # Entry point
│       ├── app.py                  # Main controller
│       ├── config.py               # Configuration
│       ├── notifications.py        # Desktop notifications
│       ├── auth/
│       │   ├── __init__.py
│       │   └── claude_max.py       # OAuth credential reader
│       ├── audio/
│       │   ├── __init__.py
│       │   ├── recorder.py         # Microphone recording
│       │   └── player.py           # Sound effects
│       ├── transcription/
│       │   ├── __init__.py
│       │   └── whisper.py          # faster-whisper integration
│       ├── postprocess/
│       │   ├── __init__.py
│       │   └── claude.py           # Claude API cleanup
│       ├── hotkey/
│       │   ├── __init__.py
│       │   ├── base.py             # Protocol definition
│       │   ├── x11.py              # pynput backend
│       │   ├── wayland.py          # evdev backend
│       │   └── manager.py          # Backend factory
│       ├── paste/
│       │   ├── __init__.py
│       │   ├── base.py             # Protocol definition
│       │   ├── x11.py              # xdotool backend
│       │   ├── wayland.py          # wtype/ydotool backend
│       │   └── manager.py          # Backend factory
│       └── tray/
│           ├── __init__.py
│           └── indicator.py        # AppIndicator3 tray
└── tests/
    ├── __init__.py
    ├── test_auth.py
    ├── test_audio.py
    ├── test_transcription.py
    ├── test_hotkey.py
    ├── test_paste.py
    └── test_integration.py
```

---

## 12. Implementation Sequence

### Phase 1: Foundation (Day 1)
1. Create pyproject.toml and directory structure
2. Implement `config.py`
3. Implement `auth/claude_max.py`
4. Create placeholder assets (icons, sound)

### Phase 2: Core Pipeline (Day 1-2)
5. Implement `audio/recorder.py`
6. Implement `audio/player.py`
7. Implement `transcription/whisper.py`
8. Test audio → transcription flow

### Phase 3: Platform Integration (Day 2)
9. Implement `hotkey/x11.py`
10. Implement `hotkey/wayland.py`
11. Implement `hotkey/manager.py`
12. Implement `paste/x11.py`
13. Implement `paste/wayland.py`
14. Implement `paste/manager.py`

### Phase 4: UI and Integration (Day 2-3)
15. Implement `tray/indicator.py`
16. Implement `postprocess/claude.py`
17. Implement `app.py` (main controller)
18. Implement `__main__.py`

### Phase 5: Polish (Day 3)
19. Implement `notifications.py`
20. Add error handling throughout
21. Create icons and sound assets
22. Test on X11 and Wayland
23. Write README.md

---

## 13. Configuration Schema

```python
# config.py
from dataclasses import dataclass, field
from pathlib import Path
import json

@dataclass
class Config:
    # Whisper settings
    whisper_model: str = "base"
    whisper_compute_type: str = "int8"
    whisper_threads: int = 4
    whisper_language: str = "en"

    # Audio settings
    sample_rate: int = 16000

    # Claude settings
    claude_model: str = "claude-sonnet-4-20250514"
    claude_enabled: bool = True

    # Paths
    assets_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "assets")

    @classmethod
    def load(cls) -> "Config":
        config_path = Path.home() / ".config" / "arch-whisper" / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                data = json.load(f)
            # Convert assets_dir string to Path
            if "assets_dir" in data:
                data["assets_dir"] = Path(data["assets_dir"])
            return cls(**data)
        return cls()

    def save(self) -> None:
        config_path = Path.home() / ".config" / "arch-whisper" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: str(v) if isinstance(v, Path) else v
                for k, v in self.__dict__.items()}
        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)
```

---

## 14. Verification Procedure

### 14.1 Pre-Flight Checks

```bash
# 1. Verify system dependencies
dpkg -l | grep -E "python3-gi|gir1.2-gtk-3.0|gir1.2-ayatanaappindicator3"
dpkg -l | grep -E "libportaudio2|libsndfile1"
which xdotool wl-copy wtype

# 2. Verify Python environment
python3 --version  # >= 3.10
pip show faster-whisper anthropic sounddevice pynput evdev

# 3. Verify Claude credentials
cat ~/.claude/.credentials.json | jq '.claudeAiOauth.subscriptionType'
# Should output: "max"

# 4. Verify Wayland permissions (if on Wayland)
groups | grep input
# Should show 'input' group
```

### 14.2 Functional Verification

```bash
# 1. Start the application
arch-whisper

# 2. Verify tray icon
# - Should see microphone icon in system tray
# - Menu should show "Ready" status

# 3. Test recording flow
# - Open a text editor (gedit, VS Code, etc.)
# - Hold Ctrl+Space
# - Verify: ding sound, icon turns red
# - Speak: "Hello world, this is a test"
# - Release Ctrl+Space
# - Verify: icon turns yellow briefly
# - Verify: text appears in editor

# 4. Test Claude post-processing
# - Hold Ctrl+Space
# - Speak with filler words: "um, so like, hello there, uh, world"
# - Release
# - Verify: cleaned text without excessive fillers

# 5. Test fallback (disconnect network)
# - Disable network
# - Record and release
# - Verify: raw transcription still pastes

# 6. Test quit
# - Right-click tray icon
# - Click "Quit"
# - Verify: application exits cleanly
```

---

## Appendix A: Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| No tray icon | AppIndicator extension missing | Install GNOME extension "AppIndicator and KStatusNotifierItem Support" |
| Hotkey doesn't work (Wayland) | Not in input group | `sudo usermod -aG input $USER` then logout/login |
| "No keyboard found" | evdev permissions | Check `/dev/input/event*` permissions |
| Paste doesn't work (Wayland) | wtype not installed | `sudo apt install wtype` |
| "Claude credentials not found" | Not authenticated | Run `claude` CLI to authenticate |
| Slow transcription | Using large model | Change to `whisper_model: "base"` in config |
| High memory usage | Large model loaded | Use "tiny" or "base" model |

---

## Appendix B: API Quick Reference

### Anthropic SDK

```python
from anthropic import Anthropic

client = Anthropic(auth_token="sk-ant-oat01-...")  # OAuth token

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}]
)
text = response.content[0].text
```

### faster-whisper

```python
from faster_whisper import WhisperModel

model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe(audio_array, language="en", vad_filter=True)
text = " ".join(seg.text for seg in segments)
```

### sounddevice

```python
import sounddevice as sd

stream = sd.InputStream(samplerate=16000, channels=1, dtype='float32',
                        callback=my_callback)
stream.start()
# ... recording ...
stream.stop()
```

### pynput (X11)

```python
from pynput import keyboard

listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()
```

### evdev (Wayland)

```python
import evdev
from evdev import ecodes

device = evdev.InputDevice('/dev/input/event0')
for event in device.read_loop():
    if event.type == ecodes.EV_KEY and event.code == ecodes.KEY_SPACE:
        print("Space!", event.value)  # 1=press, 0=release
```
