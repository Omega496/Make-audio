#!/usr/bin/env python3
"""
Document to Audio CLI tool using Kokoro-TTS.

Takes a Markdown (.md) or PDF (.pdf) file containing LaTeX math, academic notes,
tables, and formatting, cleans it into natural spoken English, and generates
high-quality audio using Kokoro-TTS (default voice: af_heart).
"""

import argparse
import sys
import time
from pathlib import Path

from pdf.cleaner import clean_markdown_for_tts
from pdf.pdf_extractor import extract_text_from_pdf
from pdf.tts import KokoroTTS


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert Markdown (.md) or PDF (.pdf) files into natural plain-English audio using Kokoro-TTS."
    )
    parser.add_argument(
        "input",
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
        help="Computation device (default: auto-detected, uses CUDA if available)",
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


def main():
    args = parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Error: Input file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)

    # 1. Show the file being converted
    print(f"Converting: {input_path.name}")

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

    # Initialize Kokoro TTS Engine quietly
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

    # 2. Show where the audio file is created
    print(f"Audio file saved to: {final_path}")


if __name__ == "__main__":
    main()
