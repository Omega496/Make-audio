#!/usr/bin/env python3
"""
Bengali Markdown Cleaning CLI Tool.

Cleans Bengali Markdown (.md, .markdown, .txt) files containing complex LaTeX equations,
flowcharts, diagrams, tables, and markup into clean, readable Markdown files
optimized for Bengali Text-to-Speech (TTS) narration or clean reading.

Usage:
    bengali_clean file.md
    bengali_clean file.md -o cleaned_file.md
    bengali_clean file.md --preview
    bengali_clean file.md --stdout
    bengali_clean docs/
"""

import argparse
import sys
from pathlib import Path
from typing import List

try:
    from pdf.cleaner import clean_bengali_markdown
except ModuleNotFoundError:
    src_dir = Path(__file__).resolve().parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from pdf.cleaner import clean_bengali_markdown

SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt"}
IGNORE_FILENAMES = {"requirements.txt", "constraints.txt"}


def parse_args(args: List[str] = None):
    parser = argparse.ArgumentParser(
        prog="bengali_clean",
        description="Clean Bengali Markdown files containing complex LaTeX equations, flowcharts, diagrams, and tables into clean Markdown."
    )
    parser.add_argument(
        "input",
        nargs="+",
        help="Path to Bengali .md, .markdown, or .txt file(s) or directory to clean.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output filepath (.md) for a single file, or destination folder for batch cleaning.",
    )
    parser.add_argument(
        "-i",
        "--in-place",
        action="store_true",
        default=False,
        help="Overwrite input file(s) in place instead of creating a new cleaned file.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        default=False,
        help="Print cleaned markdown to standard output instead of writing to a file.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        default=False,
        help="Display preview of cleaned text in terminal without modifying files.",
    )
    parser.add_argument(
        "--strip-math",
        action="store_true",
        default=False,
        help="Completely omit all LaTeX equations instead of converting them to clean notation.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Show detailed processing progress and statistics.",
    )

    return parser.parse_args(args)


def collect_files(input_args: List[str]) -> List[Path]:
    """
    Collect all valid files to process from arguments, supporting files and directories.
    Skips hidden files and existing cleaned files.
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
                if f.name.endswith("_cleaned.md") or f.name.endswith("_cleaned.txt"):
                    continue
                if f.name.lower() in IGNORE_FILENAMES:
                    continue
                if f.suffix.lower() in SUPPORTED_EXTENSIONS:
                    collected.append(f)
        elif p.is_file():
            if p.suffix.lower() in SUPPORTED_EXTENSIONS:
                collected.append(p)
            else:
                collected.append(p)
    return collected


def resolve_output_path(
    input_file: Path,
    output_arg: str = None,
    in_place: bool = False,
    is_batch: bool = False,
) -> Path:
    """
    Determine the output file path.
    Default: input_file.parent / f"{input_file.stem}_cleaned.md"
    """
    if in_place:
        return input_file

    if output_arg:
        out = Path(output_arg).resolve()
        if is_batch:
            if out.suffix and not out.is_dir():
                return out.parent / f"{input_file.stem}_cleaned.md"
            else:
                out.mkdir(parents=True, exist_ok=True)
                return out / f"{input_file.stem}_cleaned.md"
        else:
            if out.is_dir():
                return out / f"{input_file.stem}_cleaned.md"
            return out

    return input_file.parent / f"{input_file.stem}_cleaned.md"


def clean_bengali_file(file_path: Path, strip_math: bool = False) -> str:
    """
    Read and clean a Bengali markdown file.
    """
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw_text = file_path.read_text(encoding="latin-1")

    return clean_bengali_markdown(raw_text, strip_math=strip_math)


def main(argv: List[str] = None):
    args = parse_args(argv)

    if not args.input:
        print("Error: Input file(s) or directory is required.", file=sys.stderr)
        print("Usage: bengali_clean <bengali_file_name>.md [options]", file=sys.stderr)
        sys.exit(1)

    files_to_process = collect_files(args.input)
    if not files_to_process:
        print(f"Error: No convertible files ({', '.join(sorted(SUPPORTED_EXTENSIONS))}) found in specified path(s).", file=sys.stderr)
        sys.exit(1)

    is_batch = len(files_to_process) > 1 or (len(args.input) == 1 and Path(args.input[0]).is_dir())

    if is_batch and not args.stdout and not args.preview:
        print(f"Found {len(files_to_process)} Bengali file(s) to clean:")
        for f in files_to_process:
            print(f"  • {f.name}")

    total_files = len(files_to_process)
    successful_count = 0

    for idx, file_path in enumerate(files_to_process, 1):
        if is_batch and not args.stdout and not args.preview:
            print(f"\n[{idx}/{total_files}] Cleaning Bengali file: {file_path.name}")
        elif args.verbose and not args.stdout:
            print(f"Cleaning Bengali file: {file_path.name}")

        cleaned_content = clean_bengali_file(
            file_path=file_path,
            strip_math=args.strip_math,
        )

        if not cleaned_content.strip():
            print(f"Warning: {file_path.name} is empty after cleaning.", file=sys.stderr)

        if args.stdout:
            sys.stdout.write(cleaned_content)
            if not cleaned_content.endswith("\n"):
                sys.stdout.write("\n")
            sys.stdout.flush()
            successful_count += 1
            continue

        if args.preview:
            print("\n" + "=" * 60)
            print(f"BENGALI CLEANED PREVIEW: {file_path.name}")
            print("=" * 60)
            print(cleaned_content)
            print("=" * 60)
            successful_count += 1
            continue

        out_path = resolve_output_path(
            input_file=file_path,
            output_arg=args.output,
            in_place=args.in_place,
            is_batch=is_batch,
        )

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(cleaned_content, encoding="utf-8")
        successful_count += 1

        if args.in_place:
            print(f"Cleaned Bengali (in-place): {out_path}")
        else:
            print(f"Cleaned Bengali markdown saved to: {out_path}")

        if args.verbose:
            paras = [p for p in cleaned_content.split("\n\n") if p.strip()]
            words = sum(len(p.split()) for p in paras)
            chars = len(cleaned_content)
            print(f"  Stats: {len(paras)} paragraphs, {words} words, {chars} characters")

    if is_batch and not args.stdout and not args.preview:
        print(f"\n✓ Successfully cleaned {successful_count}/{total_files} Bengali file(s).")


if __name__ == "__main__":
    main()
