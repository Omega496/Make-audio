#!/usr/bin/env python3
"""
Root entry point for markdown cleaning.
Usage:
    python clean_md.py file.md
    python clean_md.py file.md -o cleaned_file.md
    python clean_md.py file.md --preview
"""

import sys
from pathlib import Path

# Add src to python path
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from pdf.clean_md import main

if __name__ == "__main__":
    main()
