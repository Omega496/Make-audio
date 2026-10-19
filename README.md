# Document to Audio (Kokoro-TTS with Google Colab Acceleration)

Convert complex academic Markdown (`.md`) and research paper PDF (`.pdf`) files containing LaTeX formulas, physics notation, tables, and markup into natural, fluent plain-English audio using [Kokoro-TTS](https://github.com/hexgrad/kokoro).

Supports **Google Colab Cloud GPU acceleration** (default) via [Google Colab CLI](https://github.com/googlecolab/google-colab-cli), as well as local hardware synthesis.

---

## 🚀 Features

- **Google Colab Cloud GPU Acceleration (Default):**
  - Runs heavy Kokoro neural TTS synthesis remotely on Google Colab's cloud GPUs (e.g. NVIDIA T4).
  - Offloads compute and RAM from your local computer.
  - Keeps sessions warm for lightning-fast consecutive document synthesis without re-provisioning.
  - Easy session teardown anytime with `make_audio --stop-colab`.
- **Dual-Engine & Automatic Fallback:**
  - `--engine colab`: (default) GPU-accelerated cloud synthesis on Colab.
  - `--engine local`: run directly on your machine's local hardware (PyTorch + Kokoro).
  - `--fallback-local`: automatically falls back to your local hardware if Google Colab is offline or reaches quota.
- **Supports Both `.md` and `.pdf` Files:**
  - Directly process Markdown files or academic research PDF papers.
  - Page selection (`--pages 1`, `--pages 1-3`, etc.) so you can synthesize specific sections or entire papers.
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

### Quick Start (Colab Cloud GPU by default)

Run `make_audio` (or `make-audio`) from any folder in your terminal:

```bash
# Convert a Markdown file using Google Colab GPU:
make_audio notes.md

# Convert a PDF file:
make_audio paper.pdf

# Convert specific pages of a PDF:
make_audio paper.pdf --pages 1-3
```

### Stop / Teardown Colab Session

When you are done converting your documents, stop the Colab VM runtime to release compute units:

```bash
make_audio --stop-colab
```

Or pass `--stop-session` to automatically shut down the VM right after finishing:

```bash
make_audio notes.md --stop-session
```

---

### Switching to Local Hardware

If you ever want to run TTS locally on your own machine instead of Google Colab:

```bash
# Run on local hardware for a single command:
make_audio notes.md --engine local

# Or automatically fall back to local hardware if Colab fails or is offline:
make_audio notes.md --fallback-local

# Or set local engine as your default in your shell:
export MAKE_AUDIO_ENGINE=local
```

---

### CLI Options

```text
usage: make-audio [-h] [-o OUTPUT] [-v VOICE] [-s SPEED] [-p PAGES]
                  [-d {cuda,cpu}] [--engine {colab,local}]
                  [--colab-session COLAB_SESSION] [--colab-gpu COLAB_GPU]
                  [--colab-timeout COLAB_TIMEOUT] [--stop-session]
                  [--stop-colab] [--fallback-local] [--keep-display-math]
                  [--keep-references] [--save-cleaned-text] [--preview]
                  [--verbose]
                  [input]

positional arguments:
  input                 Path to the .md or .pdf file to convert

options:
  -h, --help            Show help message and exit
  -o, --output OUTPUT   Output audio filepath (.wav or .mp3)
  -v, --voice VOICE     Kokoro voice pack (default: af_heart)
  -s, --speed SPEED     Speaking speed multiplier (default: 1.0)
  -p, --pages PAGES     For PDF: page range (e.g. '1', '1-3', '1,3,5')
  -d, --device DEVICE   For local engine: 'cuda' or 'cpu' (default: auto)
  --engine {colab,local}
                        TTS engine: 'colab' (default) or 'local'
  --colab-session NAME  Colab session name (default: make-audio)
  --colab-gpu GPU       Colab GPU variant: 'T4' (default), 'L4', 'A100', 'none'
  --colab-timeout SECS  Timeout in seconds for Colab synthesis (default: 600.0)
  --stop-session        Stop Colab VM after finishing this audio file
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
- [`src/pdf/md_to_audio.py`](file:///home/omega496/make_audio/src/pdf/md_to_audio.py): Main CLI entry point and engine dispatcher.
- [`src/pdf/colab_tts.py`](file:///home/omega496/make_audio/src/pdf/colab_tts.py): Google Colab CLI orchestrator (VM provisioning, payload transfer, remote execution, and download).
- [`src/pdf/colab_worker.py`](file:///home/omega496/make_audio/src/pdf/colab_worker.py): Remote GPU worker script executed on the Colab VM.
- [`src/pdf/tts.py`](file:///home/omega496/make_audio/src/pdf/tts.py): Original local Kokoro-TTS engine wrapper (fully preserved).
- [`src/pdf/cleaner.py`](file:///home/omega496/make_audio/src/pdf/cleaner.py): Markdown, LaTeX, and formula cleaning engine.
- [`src/pdf/pdf_extractor.py`](file:///home/omega496/make_audio/src/pdf/pdf_extractor.py): PDF text extraction and layout unwrapping.
