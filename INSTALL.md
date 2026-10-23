# 📦 Installation Guide

This guide covers setting up **make-audio** on your local machine.

You can either:
1. **🤖 Use an AI Agent (Recommended & Automated):** Copy-paste the AI Prompt below to your AI assistant (Antigravity, Claude Code, Cursor, Cline, Copilot, Aider, etc.) to set up everything automatically.
2. **👤 Manual Setup:** Follow the step-by-step commands for your operating system.

---

## 🤖 AI Agent Setup Prompt (Copy & Paste to your AI)

If you are using an AI coding agent, copy and paste the prompt below into the chat:

```markdown
Please set up and verify this project on my system:

1. **System Dependencies:**
   - Detect my operating system (Debian/Ubuntu, Arch, Fedora, or macOS).
   - Verify or install the required system tools:
     - `mpv` (primary terminal audio player with speed/seek controls)
     - `nano` (terminal editor for the --temp scratchpad feature)
     - `ffmpeg` (audio decoding/conversion support)
     - `espeak-ng` (phonemization support for Kokoro-TTS)
   - Use the appropriate package manager (e.g., `sudo apt update && sudo apt install -y mpv nano ffmpeg espeak-ng` on Ubuntu/Debian, or `brew install mpv nano ffmpeg espeak-ng` on macOS).

2. **Python Environment & Dependencies:**
   - Ensure Python >= 3.12 is available.
   - Install `uv` if not already installed (`curl -LsSf https://astral.sh/uv/install.sh | sh` or via package manager).
   - Run `uv sync` to create the virtual environment and install all dependencies (Kokoro-TTS, PyTorch, pypdf, soundfile, spaCy models).

3. **Verification:**
   - Run the test suite: `uv run python tests/test_text_player.py`.
   - Verify the CLI works by generating a short test clip:
     `uv run make-audio -t "System verified and ready." --no-play`.
   - Clean up any temporary test output files.

4. **Summary:**
   - Confirm that the environment is fully activated and list quick commands for me:
     - `make-audio --temp` (interactive scratchpad)
     - `make-audio notes.md --play` (document playback)
     - `make-audio -t "Hello world"` (direct speech)
```

---

## 👤 Manual Installation Guide

### Step 1: Clone the Repository

```bash
git clone https://github.com/Omega496/make_audio.git
cd make_audio
```

---

### Step 2: Install System Dependencies

`make-audio` uses `mpv` for interactive playback in your terminal and `nano` for the `--temp` scratchpad.

#### Ubuntu / Debian / Linux Mint:
```bash
sudo apt update
sudo apt install -y mpv nano ffmpeg espeak-ng
```

#### Arch Linux / Manjaro:
```bash
sudo pacman -S --needed mpv nano ffmpeg espeak-ng
```

#### Fedora / RHEL:
```bash
sudo dnf install -y mpv nano ffmpeg espeak-ng
```

#### macOS (Homebrew):
```bash
brew install mpv nano ffmpeg espeak-ng uv
```

---

### Step 3: Install `uv` (Fastest Python Package Manager)

We recommend [`uv`](https://github.com/astral-sh/uv) for instant, deterministic dependency installation:

```bash
# Install uv (Linux/macOS):
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart terminal or reload shell:
source ~/.bashrc   # or source ~/.zshrc
```

---

### Step 4: Install Project Dependencies

Run `uv sync` in the repository root. This automatically creates a Python virtual environment (`.venv`) and installs all required neural TTS dependencies (Kokoro-TTS, PyTorch, soundfile, pypdf, and spaCy models):

```bash
uv sync
```

To activate the virtual environment so `make-audio` is available directly in your shell:

```bash
source .venv/bin/activate
```

*(Alternatively, you can run any command without activating via `uv run make-audio ...`)*

---

### Step 5: Verify the Installation

Run the automated test suite to confirm everything is working properly:

```bash
# If virtualenv is activated:
python tests/test_text_player.py

# Or via uv:
uv run python tests/test_text_player.py
```

You should see:
```text
✓ test_text_temporary_cleanup passed
✓ test_text_temporary_cleanup_on_interrupt passed
✓ test_text_explicit_output_preserved passed
✓ test_file_with_play_temporary_cleanup passed
✓ test_file_with_play_cleanup_on_interrupt passed
✓ test_file_with_play_explicit_output_preserved passed
✓ test_temp_scratchpad_success passed
✓ test_temp_scratchpad_interrupt passed
✓ test_temp_scratchpad_empty passed
✓ test_t_flag_routes_to_scratchpad passed
✓ test_mutually_exclusive_args passed

All playback, scratchpad & cleanup tests passed successfully!
```

---

### Step 6: Test Playback

Run a quick test to hear Kokoro-TTS in your terminal:

```bash
make-audio -t "Congratulations! Make-audio is successfully installed and ready to use."
```

Or open the interactive multi-line scratchpad:
```bash
make-audio --temp
```

---

## ☁️ Optional: Google Colab Acceleration Setup

If you wish to offload speech synthesis to Google Colab's cloud GPUs (NVIDIA Tesla T4) using the `--colab` flag:

1. Install the Google Colab CLI:
   ```bash
   pip install google-colab-cli
   ```
2. Authorize Colab CLI with your Google account:
   ```bash
   colab-cli auth login
   ```
3. Use `--colab` anytime with `make-audio`:
   ```bash
   make-audio notes.md --colab
   make-audio --temp --colab
   ```
   *(The remote Colab VM will automatically start and shut down when synthesis finishes, consuming zero idle compute units.)*
