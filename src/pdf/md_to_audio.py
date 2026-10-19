#!/usr/bin/env python3
"""
Document to Audio CLI tool with Google Colab and Local Kokoro-TTS.

Takes a Markdown (.md) or PDF (.pdf) file containing LaTeX math, academic notes,
tables, and formatting, cleans it into natural spoken English, and generates
high-quality audio using Google Colab GPU (default) or local Kokoro-TTS.
"""

import argparse
import os
import sys
import time
from pathlib import Path

from pdf.cleaner import clean_markdown_for_tts
from pdf.colab_tts import ColabTTS, ColabTTSError
from pdf.pdf_extractor import extract_text_from_pdf
from pdf.tts import KokoroTTS


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert Markdown (.md) or PDF (.pdf) files into natural plain-English audio using Google Colab or local Kokoro-TTS."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="Path to the .md or .pdf file to convert",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output audio filepath (.wav or .mp3). Defaults to <input_stem>.wav",
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
        "--engine",
        choices=["colab", "local"],
        default=os.environ.get("MAKE_AUDIO_ENGINE", "colab"),
        help="TTS execution engine: 'colab' (uses Google Colab GPU) or 'local' (uses local machine). Default: colab.",
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
        "--stop-session",
        action="store_true",
        help="Stop and release the Colab VM runtime immediately after finishing synthesis",
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

    # Handle quick command: stop colab session
    if args.stop_colab:
        ColabTTS.stop_session(args.colab_session)
        return

    if not args.input:
        print("Error: Path to .md or .pdf file is required.", file=sys.stderr)
        print("Usage: make-audio <file_name> [options]", file=sys.stderr)
        sys.exit(1)

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Error: Input file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)

    # 1. Show the file being converted
    print(f"Converting: {input_path.name} (engine: {args.engine})")

    if input_path.suffix.lower() == ".pdf":
        raw_text = extract_text_from_pdf(
            pdf_path=input_path,
            page_range=args.pages,
            skip_references=not args.keep_references,
        )
    else:
        raw_text = input_path.read_text(encoding="utf-8")

    # Clean the text in-memory for TTS narration
    cleaned_text = clean_markdown_for_tts(
        raw_text,
        remove_display_equations=not args.keep_display_math,
    )

    # Only save cleaned text if explicitly requested with --save-cleaned-text
    if args.save_cleaned_text:
        suffix_tag = f"_p{args.pages}" if (input_path.suffix.lower() == ".pdf" and args.pages) else ""
        text_output_path = Path.cwd() / f"{input_path.stem}{suffix_tag}_cleaned.txt"
        text_output_path.write_text(cleaned_text, encoding="utf-8")
        if args.verbose:
            print(f"Cleaned plain-English text saved to: {text_output_path}")

    if args.preview:
        print("\n" + "=" * 50)
        print("CLEANED TEXT PREVIEW:")
        print("=" * 50)
        print(cleaned_text)
        print("=" * 50)
        return

    # Determine audio output path (saved in current working directory by default)
    if args.output:
        output_audio_path = Path(args.output).resolve()
    else:
        suffix_tag = f"_p{args.pages}" if (input_path.suffix.lower() == ".pdf" and args.pages) else ""
        output_audio_path = Path.cwd() / f"{input_path.stem}{suffix_tag}.wav"

    # 2. Synthesize audio via chosen engine
    if args.engine == "colab":
        try:
            colab = ColabTTS(
                session_name=args.colab_session,
                gpu=args.colab_gpu,
                timeout=args.colab_timeout,
                verbose=args.verbose,
            )
            final_path = colab.convert_to_audio_file(
                text=cleaned_text,
                output_path=output_audio_path,
                voice=args.voice,
                speed=args.speed,
                stop_session_after=args.stop_session,
            )
        except Exception as e:
            if args.fallback_local:
                print(f"\n[make-audio] Colab synthesis encountered an error: {e}", file=sys.stderr)
                print("[make-audio] Falling back to local Kokoro-TTS engine...", file=sys.stderr)
                final_path = _run_local_synthesis(args, cleaned_text, output_audio_path)
            else:
                print(f"\n[make-audio] Colab synthesis error: {e}", file=sys.stderr)
                print("[make-audio] Tip: use '--fallback-local' to automatically use local hardware on failure, or '--engine local'.", file=sys.stderr)
                sys.exit(1)
    else:
        final_path = _run_local_synthesis(args, cleaned_text, output_audio_path)

    # 3. Show where the audio file is created
    print(f"Audio file saved to: {final_path}")


if __name__ == "__main__":
    main()
