# Document to Audio (Kokoro-TTS)

Convert complex academic Markdown (`.md`), Plain Text (`.txt`), and research paper PDF (`.pdf`) files containing LaTeX formulas, physics notation, tables, and markup into natural, fluent plain-English audio using [Kokoro-TTS](https://github.com/hexgrad/kokoro).

Supports **Local Hardware (Default)** as well as **Google Colab Cloud GPU acceleration (`--colab`)** via [Google Colab CLI](https://github.com/googlecolab/google-colab-cli).

---

## 🚀 Features

- **Local Hardware by Default:**
  - Runs speech synthesis directly on your machine using PyTorch and Kokoro-TTS.
- **One-Flag Google Colab GPU Acceleration (`--colab`):**
  - Run with `--colab` to execute heavy neural TTS on Google Colab's cloud GPUs (NVIDIA Tesla T4).
  - **Zero-touch cleanup:** Google Colab VM is automatically shut down as soon as synthesis completes so you never burn compute units.
- **Interactive Scratchpad in Nano (`--temp`):**
  - Run `make-audio --temp` (or `make-audio --temp temp.txt` / `make-audio -t temp.md`) to open a scratchpad directly in `nano`.
  - Paste any amount of multi-line text, formulas, or markdown notes without terminal quoting or escaping issues.
  - Save (`Ctrl+O`, `Enter`) and exit (`Ctrl+X`). It immediately synthesizes and begins terminal playback in `mpv`.
  - **Zero file residue:** As soon as playback completes, you quit (`q` / `Esc`), or you interrupt (`Ctrl+C`), **both the temporary text file and audio file are automatically deleted**.
- **Direct Text-to-Speech & Interactive Terminal Playback (`-t` / `--text`):**
  - Run `make-audio -t "Any text you want to hear"` to synthesize and play directly in the terminal without creating persistent files.
  - Interactive controls directly from keyboard: pause/resume (`Space`), speed control (`[` and `]`), seek (`←`/`→` and `↓`/`↑`), volume (`9`/`0`), and stop (`q` or `Esc`).
  - **Zero file residue:** Temporary audio files are automatically purged from disk as soon as playback finishes or is interrupted. Pass `-o output.wav` if you wish to persist the audio.
- **Immediate Playback for Files (`--play`):**
  - Run `make-audio notes.md --play` to listen to documents directly in your terminal.
  - **Zero file residue:** Unless `-o` is explicitly provided, `--play` uses a temporary file and automatically purges it when you quit (`q` / `Esc`), finish playback, or interrupt (`Ctrl+C`). To save the file permanently while listening, pass `-o filename.wav`.
- **Supports Multiple Formats:**
  - Markdown (`.md`), plain text (`.txt`), and PDF (`.pdf`) files.
  - Page selection (`--pages 1-3`) for PDFs.
  - De-hyphenates line breaks from two-column PDF layouts (`substruc-\nture` $\to$ *substructure*).
  - Automatically strips journal/arXiv stamps, isolated page numbers, and bibliography/references sections.
- **Automated LaTeX & Math Cleaning:**
  - Converts mathematical symbols and units (`$\sim 100\text{ GeV}$`, `$\rho \propto r^{-1}$`, `$\Lambda\text{CDM}$`, `$\text{GeV}/c^2$`, `10^{-22}\text{ eV}`) into natural spoken English.
  - Omits disruptive raw display math blocks (`$$...$$`) or speaks them in plain English.
  - Expands physics quantities (e.g., $E_T^{\text{miss}} \to$ *missing transverse energy*).
- **Markdown & Paper Cleanup for Natural Speech:**
  - Converts markdown tables (`| col1 | col2 |`) into conversational presenter statements.
  - Strips citations like `[1–5]`, `(e.g. [6])`, `[7]` so speech flows uninterrupted.
  - Removes ASCII art/diagrams in code fences that cause noise in speech synthesis.
  - Strips formatting markers (`*`, `**`, `#`, `>`, `---`, `` ` ``) and emojis.
  - Automatically paces paragraphs with subtle natural pauses.
- **Kokoro-TTS Engine:**
  - Default voice: `af_heart` (American English female, high quality).
  - Supported formats: `.wav` (24kHz 16-bit PCM) or `.mp3` (via ffmpeg).

---

## ⚡ Installation

### 🤖 For AI Agents (1-Click Prompt Setup)
If you are using an AI coding assistant (such as **Antigravity**, **Cursor**, **Claude Code**, **Cline**, or **Copilot**), copy and paste the prompt in [**`INSTALL.md`**](INSTALL.md#🤖-ai-agent-setup-prompt-copy--paste-to-your-ai) into your chat. Your AI agent will automatically install all system packages, configure `uv`, install dependencies, and run verification tests.

### 👤 Quick Manual Setup (2 Steps)

1. **Install system dependencies:**
   ```bash
   # Debian / Ubuntu / Linux Mint:
   sudo apt update && sudo apt install -y mpv nano ffmpeg espeak-ng

   # Arch Linux / Manjaro:
   sudo pacman -S --needed mpv nano ffmpeg espeak-ng

   # Fedora / RHEL:
   sudo dnf install -y mpv nano ffmpeg espeak-ng

   # macOS:
   brew install mpv nano ffmpeg espeak-ng uv
   ```

2. **Install project dependencies with [`uv`](https://github.com/astral-sh/uv):**
   ```bash
   uv sync
   source .venv/bin/activate
   ```

*For comprehensive instructions, AI agent prompts, and troubleshooting, see [**`INSTALL.md`**](INSTALL.md).*

---

## 🛠️ Usage

### Interactive Nano Scratchpad (`--temp`)

For multi-line text, articles, or notes containing special characters, math formulas, or quotes that are hard to pass directly on the command line, use `--temp` to open a scratchpad in `nano`:

```bash
# 1. Open scratchpad in nano (default: temp.md), paste your text, save & exit:
make-audio --temp

# 2. Or specify a custom temporary scratchpad name:
make-audio --temp temp.txt
# (or simply: make-audio -t temp.md)

# 3. Use with custom voice, speed, or Colab GPU:
make-audio --temp -v af_sarah -s 1.2
make-audio --temp --colab
```

**Workflow:**
1. Nano opens with `temp.md` (or your chosen name).
2. Paste any amount of multi-line text (`Ctrl+Shift+V` or mouse paste).
3. Save with `Ctrl+O` and `Enter`, then exit with `Ctrl+X`.
4. `make-audio` converts the text into `temp.wav` and immediately plays it in `mpv`.
5. When you finish, press `q` / `Esc`, or press `Ctrl+C`: **both `temp.md` and `temp.wav` are automatically deleted**. Zero files left behind!

---

### Direct Text-to-Speech & Terminal Playback (`-t`)

Synthesize a single text phrase and play it immediately in your terminal with real-time controls (no audio files left on disk):

```bash
# Speak text and play in terminal with interactive controls:
make-audio -t "Artificial intelligence is advancing rapidly."

# Speak with different voice and speed:
make-audio -t "Attention is all you need." -v af_sarah -s 1.1

# Save to file while playing:
make-audio -t "Save and play this sentence." -o speech.wav

# Preview cleaned spoken English without playing:
make-audio -t "Let $\rho = 10^{-22}\text{ eV}$." --preview
```

#### ⌨️ Interactive Playback Controls

When audio plays in the terminal, you have full interactive keyboard control via `mpv`:
- `[Space]` : Pause / Resume
- `[← / →]` : Seek backward / forward 5 seconds
- `[↓ / ↑]` : Seek backward / forward 1 minute
- `[[ / ]]` : Decrease / Increase speed by 10%
- `[{ / }]` : Halve / Double speed
- `[Backspace]` : Reset speed to 1.0x
- `[9 / 0]` : Decrease / Increase volume
- `[q / Esc]` : Stop & Quit (Session stays open after playback ends so you can seek back and replay; cleans up temp files)

---

### Convert Every File in Current Directory (`.`)

To convert all Markdown, text, and PDF files in your current directory:

```bash
# Convert all files using your local machine (default):
make_audio .

# Convert all files using Google Colab GPU (auto-stops Colab when done):
make_audio . --colab
```

### Convert Individual Files

```bash
# 1. Convert a Markdown file locally:
make_audio notes.md

# 2. Convert and immediately play in terminal (cleans up temp audio on exit):
make_audio notes.md --play

# 3. Convert a plain text file locally:
make_audio summary.txt

# 4. Convert a PDF document locally:
make_audio paper.pdf --pages 1-3

# 5. Convert using Google Colab GPU (automatically stops when finished):
make_audio notes.md --colab
```

---

### CLI Options

```text
usage: make-audio [-h] [-t TEXT] [--temp [TEMP]] [--play] [--no-play]
                  [-o OUTPUT] [-v VOICE] [-s SPEED] [-p PAGES] [-d {cuda,cpu}]
                  [--colab] [--engine {local,colab}]
                  [--colab-session COLAB_SESSION] [--colab-gpu COLAB_GPU]
                  [--colab-timeout COLAB_TIMEOUT] [--keep-colab]
                  [--stop-colab] [--fallback-local] [--keep-display-math]
                  [--keep-references] [--save-cleaned-text] [--preview]
                  [--verbose]
                  [input ...]

options:
  -h, --help            Show help message and exit
  -t, --text TEXT       Input text string directly to synthesize and play in terminal
  --temp [TEMP]         Open scratchpad in nano (default: temp.md), convert, play, and auto-delete all files on exit
  --play                Play audio interactively in the terminal (cleans up temp file if -o is omitted)
  --no-play             Do not automatically play audio when using -t/--text
  -o, --output OUTPUT   Output audio filepath (.wav or .mp3) for a single file, or destination folder for batch conversion
  -v, --voice VOICE     Kokoro voice pack (default: af_heart)
  -s, --speed SPEED     Speaking speed multiplier (default: 1.0)
  -p, --pages PAGES     For PDF: page range (e.g. '1', '1-3', '1,3,5')
  -d, --device DEVICE   For local engine: 'cuda' or 'cpu' (default: auto)
  --colab               Run TTS remotely on Google Colab GPU (automatically stops VM when done)
  --engine {local,colab}
                        TTS engine: 'local' (default) or 'colab'
  --colab-session NAME  Colab session name (default: make-audio)
  --colab-gpu GPU       Colab GPU variant: 'T4' (default), 'L4', 'A100', 'none'
  --colab-timeout SECS  Timeout in seconds for Colab synthesis (default: 600.0)
  --keep-colab          Keep the Colab VM running after synthesis instead of automatically stopping it
  --stop-colab          Stop the active Colab VM immediately and exit
  --fallback-local      Automatically fallback to local machine if Colab fails
  --keep-display-math   Spoken display math instead of omitting
  --keep-references     Keep bibliography/references section in PDFs
  --save-cleaned-text   Save cleaned plain-English text (.txt)
  --preview             Display cleaned text preview without generating audio
  --verbose             Show detailed synthesis progress and specifications
```

---

## 🧹 Markdown Cleaner CLI (`clean_md`)

`clean_md` cleans Markdown documents containing complex LaTeX equations, flowcharts, Mermaid diagrams, code blocks, tables, and markup into clean, readable Markdown files (`<file_name>_cleaned.md`) optimized for Text-to-Speech narration or clean reading.

```bash
# Clean an English or Bengali markdown file (auto-detects language):
clean_md notes.md

# Force Bengali cleaning mode:
clean_md bengali_notes.md --bengali

# Strip all formulas completely without converting them:
clean_md bengali_notes.md --strip-math

# Specify custom output path:
clean_md notes.md -o output.md

# Preview cleaned text in the terminal without creating any files:
clean_md notes.md --preview

# Stream cleaned markdown directly to standard output (for piping):
clean_md notes.md --stdout

# Keep and convert display LaTeX equations ($$...$$) into spoken English (English files):
clean_md notes.md --keep-display-math

# Omit diagrams and code blocks without leaving placeholder text:
clean_md notes.md --no-placeholders

# Overwrite file in-place:
clean_md notes.md --in-place

# Batch clean all markdown files in a directory:
clean_md docs/
```

### `clean_md` CLI Options

```text
usage: clean_md [-h] [-o OUTPUT] [-i] [--stdout] [--preview]
                [--keep-display-math] [--strip-inline-math] [--drop-code]
                [--drop-diagrams] [--no-placeholders]
                [--code-placeholder CODE_PLACEHOLDER]
                [--diagram-placeholder DIAGRAM_PLACEHOLDER]
                [--lang {auto,en,bn}] [--bengali] [--strip-math] [-v]
                input [input ...]

options:
  -h, --help            Show help message and exit
  -o, --output OUTPUT   Output filepath (.md) for single file, or folder for batch cleaning
  -i, --in-place        Overwrite input file(s) in place instead of creating a new cleaned file
  --stdout              Print cleaned markdown to standard output instead of writing to a file
  --preview             Display preview of cleaned text in terminal without modifying files
  --keep-display-math   Convert display LaTeX equations ($$...$$) into spoken English instead of omitting
  --strip-inline-math   Strip inline LaTeX equations instead of converting them to spoken English
  --drop-code           Completely omit code blocks instead of inserting a placeholder description
  --drop-diagrams       Completely omit diagrams and flowcharts instead of inserting a placeholder
  --no-placeholders     Completely omit both code blocks and diagrams without inserting any placeholders
  --code-placeholder    Custom placeholder text for code blocks
  --diagram-placeholder Custom placeholder text for diagrams and flowcharts
  --lang {auto,en,bn}   Language mode: 'auto' (detect automatically), 'en' (English), 'bn' (Bengali)
  --bengali, --bn       Force Bengali markdown cleaning mode
  --strip-math          Completely omit all LaTeX formulas
  -v, --verbose         Show detailed processing progress and statistics
```

---

## 🇧🇩 Dedicated Bengali Markdown Cleaner (`bengali_clean`)

`bengali_clean` is specifically designed for cleaning Bengali Markdown files containing LaTeX equations, formulas, diagrams, and formatting into clean Markdown (`<file_name>_cleaned.md`) ready for Bengali TTS or reading:

```bash
# Clean a Bengali markdown file (generates <file_name>_cleaned.md):
bengali_clean notes.md

# Preview cleaned Bengali text in terminal:
bengali_clean notes.md --preview

# Completely strip all math formulas:
bengali_clean notes.md --strip-math

# Save to custom output:
bengali_clean notes.md -o cleaned_notes.md
```

### Key Bengali Features
- **No English Spoken Math Strings**: Eliminates English math expansions (`the integral from...`, `is approximately`, `equals`, `minus`, `alpha hat equals...`) from Bengali narration.
- **Clean Scientific Notation**: Unwraps variables, units, and constants (`Phi`, `n`, `b = R_sun`, `2.95 km`, `2/b`, `R_S`, `Δt`) into clean readable symbols.
- **Bengali Dari (`।`) Normalization**: Automatically normalizes sentences, table rows, and headers to end with proper Bengali Dari (`।`) without glitchy `।.` sequences.
- **Pacing**: Chunks long paragraphs at Bengali Dari boundaries without breaking numbered lists (`১.`, `1.`).

---

## ⏪ Reverting / Rollback to Pristine Local Baseline

A permanent Git baseline was saved before making any Colab changes. If you ever decide you prefer the original 100% local project state, you can revert completely with:

```bash
# Switch to the untouched original baseline branch:
git checkout backup-local

# Or reset main branch to the pristine baseline tag:
git reset --hard v0.1.0-local-baseline
```

---

## 📂 Project Structure

- [`INSTALL.md`](INSTALL.md): Comprehensive installation guide and copy-paste prompt for AI agents.
- [`clean_md.py`](file:///home/omega496/make_audio/clean_md.py): Root CLI launcher script for markdown cleaning.
- [`bengali_clean.py`](file:///home/omega496/make_audio/bengali_clean.py): Root CLI launcher script for Bengali markdown cleaning.
- [`md_to_audio.py`](file:///home/omega496/make_audio/md_to_audio.py): Root CLI launcher script for audio synthesis.
- [`src/pdf/clean_md.py`](file:///home/omega496/make_audio/src/pdf/clean_md.py): Markdown cleaner CLI tool and batch processor.
- [`src/pdf/bengali_clean.py`](file:///home/omega496/make_audio/src/pdf/bengali_clean.py): Dedicated Bengali markdown cleaner CLI tool.
- [`src/pdf/cleaner.py`](file:///home/omega496/make_audio/src/pdf/cleaner.py): Markdown, LaTeX, and formula cleaning engine (English and Bengali).
- [`src/pdf/md_to_audio.py`](file:///home/omega496/make_audio/src/pdf/md_to_audio.py): Main CLI entry point, batch file collector, and engine dispatcher.
- [`src/pdf/colab_tts.py`](file:///home/omega496/make_audio/src/pdf/colab_tts.py): Google Colab CLI orchestrator (VM provisioning, payload transfer, remote execution, download, and auto-stop).
- [`src/pdf/colab_worker.py`](file:///home/omega496/make_audio/src/pdf/colab_worker.py): Remote GPU worker script executed on the Colab VM.
- [`src/pdf/tts.py`](file:///home/omega496/make_audio/src/pdf/tts.py): Original local Kokoro-TTS engine wrapper (fully preserved).
- [`src/pdf/player.py`](file:///home/omega496/make_audio/src/pdf/player.py): Terminal interactive audio player with real-time speed, seek, volume, and pause controls (via `mpv`).
- [`src/pdf/pdf_extractor.py`](file:///home/omega496/make_audio/src/pdf/pdf_extractor.py): PDF text extraction and layout unwrapping.
