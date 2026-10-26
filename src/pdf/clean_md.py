#!/usr/bin/env python3
"""
Markdown Cleaning CLI Tool.

Cleans Markdown (.md, .markdown, .txt) files containing complex LaTeX equations,
flowcharts, diagrams, tables, and markup into clean, readable Markdown files
optimized for Text-to-Speech (TTS) narration or clean reading.

Usage:
    clean_md file.md
    clean_md file.md -o cleaned_file.md
    clean_md file.md --preview
    clean_md file.md --stdout
    clean_md docs/
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

from pdf.cleaner import (
    clean_markdown_for_tts,
    clean_bengali_markdown,
    is_bengali_text,
)

SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt"}
IGNORE_FILENAMES = {"requirements.txt", "constraints.txt"}


def parse_args(args: List[str] = None):
    parser = argparse.ArgumentParser(
        prog="clean_md",
        description="Clean Markdown files containing complex LaTeX equations, flowcharts, diagrams, and tables into clean Markdown."
    )
    parser.add_argument(
        "input",
        nargs="+",
        help="Path to .md, .markdown, or .txt file(s) or directory to clean.",
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
        "--keep-display-math",
        action="store_true",
        default=False,
        help="Convert display LaTeX equations ($$...$$) into spoken English instead of omitting them.",
    )
    parser.add_argument(
        "--strip-inline-math",
        action="store_true",
        default=False,
        help="Strip inline LaTeX equations instead of converting them to spoken English.",
    )
    parser.add_argument(
        "--drop-code",
        action="store_true",
        default=False,
        help="Completely omit code blocks instead of inserting a placeholder description.",
    )
    parser.add_argument(
        "--drop-diagrams",
        action="store_true",
        default=False,
        help="Completely omit diagrams and flowcharts instead of inserting a placeholder description.",
    )
    parser.add_argument(
        "--no-placeholders",
        action="store_true",
        default=False,
        help="Completely omit both code blocks and diagrams without inserting any placeholder descriptions.",
    )
    parser.add_argument(
        "--code-placeholder",
        default="Please refer to the code block shown in the document.",
        help="Placeholder text to use for code blocks (default: 'Please refer to the code block shown in the document.').",
    )
    parser.add_argument(
        "--diagram-placeholder",
        default="Please refer to the diagram shown in the document.",
        help="Placeholder text to use for diagrams and flowcharts (default: 'Please refer to the diagram shown in the document.').",
    )
    parser.add_argument(
        "--lang",
        choices=["auto", "en", "bn"],
        default="auto",
        help="Language mode: 'auto' (detect automatically), 'en' (English), or 'bn' (Bengali). Default: auto.",
    )
    parser.add_argument(
        "--bengali",
        "--bn",
        action="store_true",
        default=False,
        help="Force Bengali markdown cleaning mode.",
    )
    parser.add_argument(
        "--strip-math",
        action="store_true",
        default=False,
        help="Completely omit all LaTeX formulas.",
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
                # Still include if explicitly passed
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
                # Provided a filename during batch conversion: place alongside or inside parent
                return out.parent / f"{input_file.stem}_cleaned.md"
            else:
                out.mkdir(parents=True, exist_ok=True)
                return out / f"{input_file.stem}_cleaned.md"
        else:
            if out.is_dir():
                return out / f"{input_file.stem}_cleaned.md"
            return out

    # Default output naming alongside input file: <filename>_cleaned.md
    return input_file.parent / f"{input_file.stem}_cleaned.md"


def clean_file(
    file_path: Path,
    remove_display_equations: bool = True,
    drop_code: bool = False,
    drop_diagrams: bool = False,
    strip_inline_math: bool = False,
    code_placeholder: str = "Please refer to the code block shown in the document.",
    diagram_placeholder: str = "Please refer to the diagram shown in the document.",
    lang: str = "auto",
    bengali: bool = False,
    strip_math: bool = False,
) -> str:
    """
    Read and clean a markdown file using cleaner module, auto-detecting language.
    """
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw_text = file_path.read_text(encoding="latin-1")

    use_bengali = bengali or (lang == "bn") or (lang == "auto" and is_bengali_text(raw_text))

    if use_bengali:
        return clean_bengali_markdown(
            markdown_text=raw_text,
            strip_math=strip_math,
        )

    return clean_markdown_for_tts(
        markdown_text=raw_text,
        remove_display_equations=remove_display_equations,
        drop_code=drop_code,
        drop_diagrams=drop_diagrams,
        strip_inline_math=strip_inline_math or strip_math,
        code_placeholder=code_placeholder,
        diagram_placeholder=diagram_placeholder,
    )


def main(argv: List[str] = None):
    args = parse_args(argv)

    if not args.input:
        print("Error: Input file(s) or directory is required.", file=sys.stderr)
        print("Usage: clean_md <file_name>.md [options]", file=sys.stderr)
        sys.exit(1)

    files_to_process = collect_files(args.input)
    if not files_to_process:
        print(f"Error: No convertible files ({', '.join(sorted(SUPPORTED_EXTENSIONS))}) found in specified path(s).", file=sys.stderr)
        sys.exit(1)

    drop_code = args.drop_code or args.no_placeholders
    drop_diagrams = args.drop_diagrams or args.no_placeholders
    code_placeholder = "" if args.no_placeholders else args.code_placeholder
    diagram_placeholder = "" if args.no_placeholders else args.diagram_placeholder

    is_batch = len(files_to_process) > 1 or (len(args.input) == 1 and Path(args.input[0]).is_dir())

    if is_batch and not args.stdout and not args.preview:
        print(f"Found {len(files_to_process)} file(s) to clean:")
        for f in files_to_process:
            print(f"  • {f.name}")

    total_files = len(files_to_process)
    successful_count = 0

    for idx, file_path in enumerate(files_to_process, 1):
        if is_batch and not args.stdout and not args.preview:
            print(f"\n[{idx}/{total_files}] Cleaning: {file_path.name}")
        elif args.verbose and not args.stdout:
            print(f"Cleaning: {file_path.name}")

        cleaned_content = clean_file(
            file_path=file_path,
            remove_display_equations=not args.keep_display_math,
            drop_code=drop_code,
            drop_diagrams=drop_diagrams,
            strip_inline_math=args.strip_inline_math,
            code_placeholder=code_placeholder,
            diagram_placeholder=diagram_placeholder,
            lang=args.lang,
            bengali=args.bengali,
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
            print(f"CLEANED PREVIEW: {file_path.name}")
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
            print(f"Cleaned (in-place): {out_path}")
        else:
            print(f"Cleaned markdown saved to: {out_path}")

        if args.verbose:
            paras = [p for p in cleaned_content.split("\n\n") if p.strip()]
            words = sum(len(p.split()) for p in paras)
            chars = len(cleaned_content)
            print(f"  Stats: {len(paras)} paragraphs, {words} words, {chars} characters")

    if is_batch and not args.stdout and not args.preview:
        print(f"\n✓ Successfully cleaned {successful_count}/{total_files} file(s).")


if __name__ == "__main__":
    main()
