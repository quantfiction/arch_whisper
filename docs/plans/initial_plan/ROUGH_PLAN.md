# Arch Whisper - Wispr Flow Alternative for Ubuntu

## Overview

A Python-based voice transcription tool with:
- **Hold-to-record** via global Ctrl+Space hotkey
- **faster-whisper** transcription (CPU int8, no CUDA)
- **Claude post-processing** for light cleanup (Claude Max OAuth auth)
- **Paste anywhere** via clipboard + simulated Ctrl+V
- **System tray** with color indicator + audible ding on record start

## Architecture

```
Hotkey Manager → Audio Recorder → Whisper Transcriber → Claude Post-Processor → Paste Manager
      ↓                                                                              ↓
System Tray ←←←←←←←←←←←←←←←← State Machine (App Controller) ←←←←←←←←←←←←←←←←←←←←←←←←
```

## Project Structure

```
arch_whisper/
├── pyproject.toml
├── assets/
│   ├── icon_idle.png, icon_recording.png, icon_processing.png
│   └── ding.wav
└── src/arch_whisper/
    ├── __main__.py          # Entry point
    ├── app.py               # Main controller (state machine)
    ├── config.py            # Configuration
    ├── hotkey/
    │   ├── x11.py           # pynput backend
    │   ├── wayland.py       # evdev backend
    │   └── manager.py       # Auto-detect X11/Wayland
    ├── audio/
    │   ├── recorder.py      # sounddevice recording
    │   └── player.py        # Ding sound playback
    ├── transcription/
    │   └── whisper.py       # faster-whisper CPU int8
    ├── postprocess/
    │   └── claude.py        # Claude API cleanup
    ├── paste/
    │   ├── x11.py           # xdotool backend
    │   ├── wayland.py       # wtype/ydotool backend
    │   └── manager.py       # Auto-detect
    ├── tray/
    │   └── indicator.py     # AppIndicator3 tray
    └── auth/
        └── claude_max.py    # OAuth token from ~/.claude/.credentials.json
```

## Key Dependencies

```toml
dependencies = [
    "sounddevice>=0.5.0",      # Audio recording
    "numpy>=1.24.0",
    "faster-whisper>=1.0.0",   # Transcription (CPU)
    "anthropic>=0.40.0",       # Claude API
    "PyGObject>=3.42.0",       # GTK/AppIndicator
    "pynput>=1.7.6",           # X11 hotkey
    "evdev>=1.6.0",            # Wayland hotkey
    "pyperclip>=1.8.2",        # Clipboard
]
```

**System packages (apt):**
```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 \
    libportaudio2 libsndfile1 xdotool wtype wl-clipboard
```

## Implementation Steps

### Phase 1: Project Setup
1. Create pyproject.toml with dependencies
2. Set up directory structure
3. Create placeholder assets (icons, ding sound)

### Phase 2: Core Infrastructure
4. Implement `config.py` - configuration management
5. Implement `tray/indicator.py` - AppIndicator3 system tray
6. Implement `__main__.py` - entry point

### Phase 3: Audio Pipeline
7. Implement `audio/recorder.py` - sounddevice recording
8. Implement `audio/player.py` - ding sound playback

### Phase 4: Transcription
9. Implement `transcription/whisper.py` - faster-whisper with CPU int8

### Phase 5: Hotkey System
10. Implement `hotkey/x11.py` - pynput backend
11. Implement `hotkey/wayland.py` - evdev backend
12. Implement `hotkey/manager.py` - auto-detection

### Phase 6: Paste Mechanism
13. Implement `paste/x11.py` - xdotool (clipboard + Ctrl+V)
14. Implement `paste/wayland.py` - wl-copy + wtype/ydotool
15. Implement `paste/manager.py` - auto-detection

### Phase 7: Claude Integration
16. Implement `auth/claude_max.py` - read OAuth from ~/.claude/.credentials.json
17. Implement `postprocess/claude.py` - Claude API for text cleanup

### Phase 8: Main Controller
18. Implement `app.py` - state machine orchestrating all components

### Phase 9: Polish
19. Add error handling and desktop notifications
20. Test end-to-end flow

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python | Best faster-whisper bindings, GTK/PyGObject for tray |
| Whisper model | `base` (74MB) | Good speed/accuracy balance for CPU |
| Compute type | `int8` | Fastest CPU inference |
| X11 hotkey | pynput | Well-tested, no elevated permissions |
| Wayland hotkey | evdev | Only option that works (requires `input` group) |
| Paste method | Clipboard + Ctrl+V | Most reliable across apps |
| Claude model | claude-sonnet-4-20250514 | Fast, good for light cleanup |

## Wayland Permissions

For Wayland hotkey support, user must be in `input` group:
```bash
sudo usermod -aG input $USER
# Then logout/login
```

## Verification

1. Run `arch-whisper` from terminal
2. Verify tray icon appears (gray = idle)
3. Hold Ctrl+Space - should hear ding, icon turns red
4. Speak a sentence
5. Release Ctrl+Space - icon turns yellow (processing)
6. Text should paste at cursor, icon returns to gray

## Fallback Behavior

- If Claude API fails → paste raw transcription
- If paste fails → copy to clipboard + show notification
- If Wayland tools missing → show clear error with install instructions
