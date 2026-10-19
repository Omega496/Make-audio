#!/usr/bin/env python3
"""
Root entry point for markdown to audio synthesis.
Usage:
    python md_to_audio.py explanation.md
    python md_to_audio.py [input_file.md] [-o output.wav] [-v af_heart] [-s 1.0]
"""

import sys
from pathlib import Path

# Add src to python path
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from pdf.md_to_audio import main

if __name__ == "__main__":
    main()
