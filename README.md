# Document to Audio (Kokoro-TTS)

Convert complex academic Markdown (`.md`) and research paper PDF (`.pdf`) files containing LaTeX formulas, physics notation, tables, and markup into natural, fluent plain-English audio using [Kokoro-TTS](https://github.com/hexgrad/kokoro).

---

## 🚀 Features

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
  - CUDA GPU acceleration (with automatic CPU fallback).
  - High performance: synthesizes ~15 minutes of audio in under 30 seconds on GPU.
- **Output Formats:**
  - Generates standard `.wav` (24kHz 16-bit PCM) or `.mp3` (via ffmpeg).
  - Saves the cleaned plain-English text alongside the audio for verification.

---

## 🛠️ Usage

### Global CLI Command (`make_audio`)

You can run `make_audio` from **any folder** in your terminal. The generated audio will automatically be saved into whatever folder you are currently in:

```bash
# Convert a Markdown file from your current folder:
make_audio notes.md

# Convert a PDF file from your current folder:
make_audio paper.pdf

# Convert a file from another directory (saves in your current folder):
make_audio /path/to/documents/explanation.md

# Convert specific pages of a PDF:
make_audio paper.pdf --pages 1-3
```

*(You can also use `make-audio` or `python md_to_audio.py` inside the project folder).*

---

### CLI Options

```text
usage: md-to-audio [-h] [-o OUTPUT] [-v VOICE] [-s SPEED] [-p PAGES]
                   [-d {cuda,cpu}] [--keep-display-math] [--keep-references]
                   [--save-cleaned-text] [--no-save-cleaned-text] [--preview]
                   [input]

positional arguments:
  input                 Path to .md or .pdf file (default: explanation.md)

options:
  -h, --help            Show help message and exit
  -o, --output OUTPUT   Output audio filepath (.wav or .mp3)
  -v, --voice VOICE     Kokoro voice pack (default: af_heart)
  -s, --speed SPEED     Speaking speed multiplier (default: 1.0)
  -p, --pages PAGES     For PDF: page range (e.g. '1', '1-3', '1,3,5')
  -d, --device DEVICE   Device: 'cuda' or 'cpu' (default: auto)
  --keep-display-math   Spoken display math instead of omitting
  --keep-references     Keep bibliography/references section in PDFs
  --save-cleaned-text   Save cleaned plain-English text (default: True)
  --preview             Display cleaned text without generating audio
```

### Examples

1. **Convert Page 1 of a PDF paper:**
   ```bash
   python md_to_audio.py "Deep Learning the Morphology of Dark Matter Substructure.pdf" --pages 1
   ```

2. **Preview cleaned text of a PDF or Markdown before generating audio:**
   ```bash
   python md_to_audio.py "Deep Learning the Morphology of Dark Matter Substructure.pdf" --pages 1 --preview
   ```

3. **Convert any Markdown file to audio:**
   ```bash
   python md_to_audio.py my_notes.md -o my_notes.wav
   ```

4. **Change speaking voice or speed:**
   ```bash
   python md_to_audio.py explanation.md -v af_heart -s 1.1 -o output_fast.wav
   ```

---

## 📂 Project Structure

- [`md_to_audio.py`](file:///home/omega496/Documents/GSOC/deeplance/paper/PDF/md_to_audio.py): CLI launcher script.
- [`src/pdf/cleaner.py`](file:///home/omega496/Documents/GSOC/deeplance/paper/PDF/src/pdf/cleaner.py): Markdown, LaTeX, and formula cleaning engine.
- [`src/pdf/pdf_extractor.py`](file:///home/omega496/Documents/GSOC/deeplance/paper/PDF/src/pdf/pdf_extractor.py): PDF text extraction, de-hyphenation, and layout unwrapping.
- [`src/pdf/tts.py`](file:///home/omega496/Documents/GSOC/deeplance/paper/PDF/src/pdf/tts.py): Kokoro-TTS wrapper with paragraph pacing and progress reporting.
- [`explanation.md`](file:///home/omega496/Documents/GSOC/deeplance/paper/PDF/explanation.md): Sample input explanation markdown.
- [`explanation.wav`](file:///home/omega496/Documents/GSOC/deeplance/paper/PDF/explanation.wav): Generated 15-minute audio narration.
