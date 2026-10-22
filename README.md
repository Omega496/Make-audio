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

## 🛠️ Usage

### Direct Text-to-Speech & Terminal Playback (`-t`)

Synthesize any text and play it immediately in your terminal with real-time controls (no audio files left on disk):

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
- `[q / Esc]` : Stop & Quit immediately (cleans up any temp files)

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

# 2. Convert and immediately play in terminal:
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
usage: make-audio [-h] [-t TEXT] [--play] [--no-play] [-o OUTPUT] [-v VOICE]
                  [-s SPEED] [-p PAGES] [-d {cuda,cpu}] [--colab]
                  [--engine {local,colab}] [--colab-session COLAB_SESSION]
                  [--colab-gpu COLAB_GPU] [--colab-timeout COLAB_TIMEOUT]
                  [--keep-colab] [--stop-colab] [--fallback-local]
                  [--keep-display-math] [--keep-references]
                  [--save-cleaned-text] [--preview] [--verbose]
                  [input ...]

options:
  -h, --help            Show help message and exit
  -t, --text TEXT       Input text string directly to synthesize and play in terminal
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

- [`md_to_audio.py`](file:///home/omega496/make_audio/md_to_audio.py): Root CLI launcher script.
- [`src/pdf/md_to_audio.py`](file:///home/omega496/make_audio/src/pdf/md_to_audio.py): Main CLI entry point, batch file collector, and engine dispatcher.
- [`src/pdf/colab_tts.py`](file:///home/omega496/make_audio/src/pdf/colab_tts.py): Google Colab CLI orchestrator (VM provisioning, payload transfer, remote execution, download, and auto-stop).
- [`src/pdf/colab_worker.py`](file:///home/omega496/make_audio/src/pdf/colab_worker.py): Remote GPU worker script executed on the Colab VM.
- [`src/pdf/tts.py`](file:///home/omega496/make_audio/src/pdf/tts.py): Original local Kokoro-TTS engine wrapper (fully preserved).
- [`src/pdf/player.py`](file:///home/omega496/make_audio/src/pdf/player.py): Terminal interactive audio player with real-time speed, seek, volume, and pause controls (via `mpv`).
- [`src/pdf/cleaner.py`](file:///home/omega496/make_audio/src/pdf/cleaner.py): Markdown, LaTeX, and formula cleaning engine.
- [`src/pdf/pdf_extractor.py`](file:///home/omega496/make_audio/src/pdf/pdf_extractor.py): PDF text extraction and layout unwrapping.
