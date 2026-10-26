#!/usr/bin/env python3
"""
Root entry point for Bengali markdown cleaning.
Usage:
    bengali_clean <file_name>.md
    python bengali_clean.py <file_name>.md
    python bengali_clean.py <file_name>.md -o output.md
"""

import sys
from pathlib import Path

# Add src to python path
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from pdf.bengali_clean import main

if __name__ == "__main__":
    main()
