#!/usr/bin/env python3
"""
Mobile2Storage - Fast Android to PC File Transfer
==================================================

Solves the problem of transferring 50GB+ data from Android 10+
to PC without slow speeds, stuck calculating, or file corruption.

Features:
- Chunked parallel transfers (no more stuck calculating)
- SHA-256 end-to-end integrity verification (zero corruption)
- Adaptive chunk sizing for maximum speed
- Write-Ahead Logging for crash recovery
- Resume support for interrupted transfers
- Eye-catching dashboard with real-time progress
- Support for USB and WiFi ADB connections

Requirements:
- Python 3.10+
- ADB (Android Debug Bridge) installed
- Android device with USB Debugging or Wireless Debugging enabled

Usage:
    python main.py
    
    Or run the .exe after building with PyInstaller.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui.dashboard import main


if __name__ == "__main__":
    main()
