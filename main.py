#!/usr/bin/env python3
"""
Mobile2Storage - Fast Android to PC File Transfer
==================================================
Zero-setup: Open app → Scan QR → Pick files → Send.
No ADB, no USB debugging, no developer options needed.
"""

import sys
import os

# Fix path for both source run and PyInstaller .exe
if getattr(sys, 'frozen', False):
    # Running as compiled .exe
    BASE_DIR = os.path.dirname(sys.executable)
    sys.path.insert(0, BASE_DIR)
else:
    # Running from source
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, BASE_DIR)

from src.ui.dashboard import main


if __name__ == "__main__":
    main()
