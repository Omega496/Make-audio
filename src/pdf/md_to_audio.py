#!/usr/bin/env python3
"""
Document to Audio CLI tool with Local Kokoro-TTS and Google Colab Acceleration.

Takes Markdown (.md), Text (.txt), or PDF (.pdf) files containing LaTeX math, academic notes,
tables, and formatting, cleans them into natural spoken English, and generates
high-quality audio using local Kokoro-TTS (default) or Google Colab GPU (--colab).
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import List

from pdf.cleaner import clean_markdown_for_tts
from pdf.colab_tts import ColabTTS, ColabTTSError
from pdf.pdf_extractor import extract_text_from_pdf
from pdf.tts import KokoroTTS

SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt", ".pdf"}
IGNORE_FILENAMES = {"requirements.txt", "constraints.txt"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert Markdown (.md), Text (.txt), or PDF (.pdf) files into natural plain-English audio using local Kokoro-TTS or Google Colab."
    )
    parser.add_argument(
        "input",
        nargs="*",
        default=[],
        help="Path to .md, .txt, .pdf file(s) or directory (e.g. '.') to convert",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output audio filepath (.wav or .mp3) for a single file, or destination folder for batch conversion.",
    )
    parser.add_argument(
        "-v",
        "--voice",
        default="af_heart",
        help="Kokoro voice pack to use (default: af_heart). Examples: af_heart, af_sarah, am_adam, etc.",
    )
    parser.add_argument(
        "-s",
        "--speed",
        type=float,
        default=1.0,
        help="Speaking speed multiplier (default: 1.0)",
    )
    parser.add_argument(
        "-p",
        "--pages",
        default=None,
        help="For PDF files: page range to convert (e.g., '1', '1-3', '1,2,5'). Defaults to all pages.",
    )
    parser.add_argument(
        "-d",
        "--device",
        choices=["cuda", "cpu"],
        default=None,
        help="For local engine: computation device (default: auto-detected, uses CUDA if available)",
    )
    parser.add_argument(
        "--colab",
        action="store_true",
        default=False,
        help="Run TTS remotely on Google Colab GPU (automatically stops VM when done)",
    )
    parser.add_argument(
        "--engine",
        choices=["local", "colab"],
        default=os.environ.get("MAKE_AUDIO_ENGINE", "local"),
        help="TTS execution engine: 'local' (uses local machine, default) or 'colab' (uses Google Colab GPU).",
    )
    parser.add_argument(
        "--colab-session",
        default="make-audio",
        help="Google Colab session name (default: make-audio)",
    )
    parser.add_argument(
        "--colab-gpu",
        default="T4",
        help="Colab GPU accelerator variant (e.g. 'T4', 'L4', 'A100', or 'none'). Default: T4",
    )
    parser.add_argument(
        "--colab-timeout",
        type=float,
        default=600.0,
        help="Timeout in seconds for remote Colab synthesis (default: 600.0)",
    )
    parser.add_argument(
        "--keep-colab",
        action="store_true",
        default=False,
        help="Keep the Colab VM running after synthesis instead of automatically stopping it",
    )
    parser.add_argument(
        "--stop-colab",
        action="store_true",
        help="Stop the active Colab VM session and exit immediately",
    )
    parser.add_argument(
        "--fallback-local",
        action="store_true",
        default=False,
        help="Automatically fall back to local hardware synthesis if Google Colab fails or is offline",
    )
    parser.add_argument(
        "--keep-display-math",
        action="store_true",
        help="Convert display math to spoken English instead of omitting it",
    )
    parser.add_argument(
        "--keep-references",
        action="store_true",
        help="For PDF files: keep the bibliography / references section (default: omitted)",
    )
    parser.add_argument(
        "--save-cleaned-text",
        action="store_true",
        default=False,
        help="Save the cleaned plain-English text to a .txt file (default: False)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Clean and display the plain-English text without generating audio",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed synthesis progress and audio specifications",
    )
    return parser.parse_args()


def collect_files(input_args: List[str]) -> List[Path]:
    """
    Collect all valid files to process from arguments, supporting files and directories.
    """
    collected: List[Path] = []
    for item_str in input_args:
        p = Path(item_str).resolve()
        if not p.exists():
            print(f"Warning: Input path '{item_str}' does not exist, skipping.", file=sys.stderr)
            continue
        if p.is_dir():
            for f in sorted(p.iterdir()):
                if not f.is_file():
                    continue
                if f.name.startswith("."):
                    continue
                if f.name.endswith("_cleaned.txt"):
                    continue
                if f.name.lower() in IGNORE_FILENAMES:
                    continue
                if f.suffix.lower() in SUPPORTED_EXTENSIONS:
                    collected.append(f)
        elif p.is_file():
            if p.suffix.lower() in SUPPORTED_EXTENSIONS:
                collected.append(p)
            else:
                # Still include if explicitly passed
                collected.append(p)
    return collected


def _run_local_synthesis(args, cleaned_text: str, output_audio_path: Path) -> Path:
    """Run audio synthesis locally using PyTorch and KokoroTTS."""
    tts = KokoroTTS(lang_code="a", device=args.device)

    progress_callback = None
    if args.verbose:
        paragraphs = [p for p in cleaned_text.split("\n\n") if p.strip()]
        total_paras = len(paragraphs)
        word_count = sum(len(p.split()) for p in paragraphs)
        print(f"Processing {total_paras} paragraphs ({word_count} words) on {tts.device.upper()}...")

        def _progress(current: int, total: int, snippet: str):
            pct = (current / total) * 100
            clean_snippet = snippet.replace("\n", " ").strip()
            if len(clean_snippet) > 50:
                clean_snippet = clean_snippet[:47] + "..."
            sys.stdout.write(f"\r[{pct:5.1f}%] [{current:02d}/{total:02d}] Generating: \"{clean_snippet}\"")
            sys.stdout.flush()

        progress_callback = _progress

    final_path = tts.convert_to_audio_file(
        text=cleaned_text,
        output_path=output_audio_path,
        voice=args.voice,
        speed=args.speed,
        progress_callback=progress_callback,
    )

    if args.verbose:
        print()

    return final_path


def main():
    args = parse_args()

    # If --colab is specified, use the colab engine
    if args.colab:
        args.engine = "colab"

    # Handle quick command: stop colab session
    if args.stop_colab:
        ColabTTS.stop_session(args.colab_session, verbose=args.verbose)
        return

    if not args.input:
        print("Error: Input file or directory is required (e.g. 'make-audio .' or 'make-audio notes.md')", file=sys.stderr)
        print("Usage: make-audio [files_or_dirs...] [options]", file=sys.stderr)
        sys.exit(1)

    files_to_process = collect_files(args.input)
    if not files_to_process:
        print(f"Error: No convertible files ({', '.join(sorted(SUPPORTED_EXTENSIONS))}) found in specified path(s).", file=sys.stderr)
        sys.exit(1)

    is_batch = len(files_to_process) > 1 or (len(args.input) == 1 and Path(args.input[0]).is_dir())
    if is_batch:
        engine_str = f" (engine: {args.engine})" if args.verbose else ""
        print(f"Found {len(files_to_process)} file(s) to convert{engine_str}:")
        for f in files_to_process:
            print(f"  • {f.name}")

    colab_instance = None
    if args.engine == "colab":
        colab_instance = ColabTTS(
            session_name=args.colab_session,
            gpu=args.colab_gpu,
            timeout=args.colab_timeout,
            verbose=args.verbose,
        )

    try:
        total_files = len(files_to_process)
        for idx, file_path in enumerate(files_to_process, 1):
            if is_batch:
                print(f"\n[{idx}/{total_files}] Converting: {file_path.name}")
            else:
                engine_str = f" (engine: {args.engine})" if args.verbose else ""
                print(f"Converting: {file_path.name}{engine_str}")

            # Extract raw text
            if file_path.suffix.lower() == ".pdf":
                raw_text = extract_text_from_pdf(
                    pdf_path=file_path,
                    page_range=args.pages,
                    skip_references=not args.keep_references,
                )
            else:
                try:
                    raw_text = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    raw_text = file_path.read_text(encoding="latin-1")

            # Clean the text in-memory for TTS narration
            cleaned_text = clean_markdown_for_tts(
                raw_text,
                remove_display_equations=not args.keep_display_math,
            )

            if not cleaned_text.strip():
                print(f"Skipping {file_path.name}: text is empty after cleaning.")
                continue

            # Save cleaned text if requested
            if args.save_cleaned_text:
                suffix_tag = f"_p{args.pages}" if (file_path.suffix.lower() == ".pdf" and args.pages) else ""
                text_output_path = Path.cwd() / f"{file_path.stem}{suffix_tag}_cleaned.txt"
                text_output_path.write_text(cleaned_text, encoding="utf-8")
                if args.verbose:
                    print(f"Cleaned plain-English text saved to: {text_output_path}")

            if args.preview:
                print("\n" + "=" * 50)
                print(f"CLEANED TEXT PREVIEW: {file_path.name}")
                print("=" * 50)
                print(cleaned_text)
                print("=" * 50)
                continue

            # Determine audio output path
            if args.output:
                out_path = Path(args.output).resolve()
                if is_batch:
                    if out_path.suffix and not out_path.is_dir():
                        output_audio_path = out_path.parent / f"{file_path.stem}{out_path.suffix}"
                    else:
                        out_path.mkdir(parents=True, exist_ok=True)
                        output_audio_path = out_path / f"{file_path.stem}.wav"
                else:
                    output_audio_path = out_path
            else:
                suffix_tag = f"_p{args.pages}" if (file_path.suffix.lower() == ".pdf" and args.pages) else ""
                output_audio_path = Path.cwd() / f"{file_path.stem}{suffix_tag}.wav"

            # Synthesize audio via chosen engine
            if args.engine == "colab":
                try:
                    final_path = colab_instance.convert_to_audio_file(
                        text=cleaned_text,
                        output_path=output_audio_path,
                        voice=args.voice,
                        speed=args.speed,
                        stop_session_after=False,
                    )
                except Exception as e:
                    if args.fallback_local:
                        print(f"\n[make-audio] Colab error on {file_path.name}: {e}", file=sys.stderr)
                        print("[make-audio] Falling back to local Kokoro-TTS engine...", file=sys.stderr)
                        final_path = _run_local_synthesis(args, cleaned_text, output_audio_path)
                    else:
                        print(f"\n[make-audio] Colab error on {file_path.name}: {e}", file=sys.stderr)
                        print("[make-audio] Tip: use '--fallback-local' to fall back on failure, or omit '--colab'.", file=sys.stderr)
                        raise
            else:
                final_path = _run_local_synthesis(args, cleaned_text, output_audio_path)

            print(f"Audio file saved to: {final_path}")

    finally:
        # Automatically stop Colab session when done unless user specifically asked to keep it
        if args.engine == "colab" and not args.keep_colab:
            ColabTTS.stop_session(args.colab_session, verbose=args.verbose)


if __name__ == "__main__":
    main()
