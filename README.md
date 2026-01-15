# arch-whisper

Push-to-talk voice transcription for Linux. Hold a hotkey, speak, release — your words appear wherever your cursor is.

Uses local Whisper for transcription and Claude for cleaning up filler words (um, uh, like, you know).

## Requirements

- Ubuntu 22.04+ (or similar Linux with X11)
- Python 3.10+
- Claude Code CLI installed and authenticated (for filler word cleanup)

## Installation

### 1. Install system dependencies

```bash
sudo apt update
sudo apt install -y \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    gir1.2-notify-0.7 \
    gir1.2-ayatanaappindicator3-0.1 \
    libportaudio2 \
    portaudio19-dev \
    xclip \
    xdotool
```

### 2. Clone and install

```bash
git clone https://github.com/quantfiction/arch_whisper.git
cd arch_whisper

# Create virtual environment with system packages (needed for GTK)
python3 -m venv .venv --system-site-packages
source .venv/bin/activate

# Install with uv (recommended) or pip
pip install uv
uv sync

# Or with pip
pip install -e .
```

### 3. Install Claude Code (for filler word cleanup)

The app uses Claude to clean up transcriptions. Install Claude Code:

```bash
npm install -g @anthropic-ai/claude-code
claude login
```

Without Claude Code, the app still works but won't remove filler words.

## Usage

### Starting the app

```bash
# If venv is activated
arch-whisper

# Or directly
/path/to/arch-whisper/.venv/bin/arch-whisper
```

A system tray icon will appear. The app runs in the background.

### Recording

1. **Hold `Ctrl+Space`** — recording starts (you'll hear a ding)
2. **Speak** — say what you want to type
3. **Release `Ctrl+Space`** — transcription happens, text is pasted

The text appears wherever your cursor is focused (chat apps, text editors, terminals, etc.).

### Stopping the app

- **From terminal:** `Ctrl+C`
- **If running in background:** `pkill arch-whisper`
- **From system tray:** Right-click the icon → Quit

## Auto-start on login

To start arch-whisper automatically when you log in:

```bash
mkdir -p ~/.config/autostart

cat > ~/.config/autostart/arch-whisper.desktop << EOF
[Desktop Entry]
Type=Application
Name=Arch Whisper
Comment=Push-to-talk voice transcription
Exec=$(pwd)/.venv/bin/arch-whisper
Icon=audio-input-microphone
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
```

To disable autostart, delete the file:
```bash
rm ~/.config/autostart/arch-whisper.desktop
```

## Configuration

Create `~/.config/arch-whisper/config.toml` to customize:

```toml
# Hotkey (default: ctrl+space)
hotkey = "ctrl+space"

# Whisper model: tiny, base, small, medium, large-v3
# Larger = more accurate but slower
whisper_model = "base"

# Number of CPU threads for Whisper
whisper_threads = 4

# Enable/disable Claude cleanup
claude_enabled = true

# Enable/disable the ding sound
ding_enabled = true
```

## Troubleshooting

### "No speech detected"
- Speak louder or closer to the microphone
- Check your default audio input device

### Paste doesn't work
- **In terminals:** The app auto-detects terminals and uses `Ctrl+Shift+V`
- **If still not working:** Ensure `xdotool` and `xclip` are installed

### Claude cleanup not working
- Run `claude --version` to verify Claude Code is installed
- Run `claude login` if not authenticated
- Check logs: the app prints `Feature claude_cli: available` on startup

### App won't start
- Check for missing dependencies: `arch-whisper` will log what's missing
- Ensure PyGObject is available: `python3 -c "import gi; print('OK')"`

### Hotkey not detected
- On X11: Should work out of the box
- On Wayland: Hotkey detection requires `/dev/input` access (add user to `input` group)

## How it works

1. **Hotkey detection** — listens for `Ctrl+Space` via pynput (X11) or evdev (Wayland)
2. **Audio recording** — captures from default mic at 16kHz mono
3. **Transcription** — local Whisper model (runs on CPU)
4. **Cleanup** — Claude removes filler words via Claude Code CLI
5. **Paste** — copies to clipboard and simulates `Ctrl+V` (or `Ctrl+Shift+V` for terminals)

## Running tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## License

MIT
