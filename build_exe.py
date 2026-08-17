"""
Build script to create Mobile2Storage.exe using PyInstaller.

Run: python build_exe.py
Output: dist/Mobile2Storage.exe
"""

import subprocess
import sys
import os


def build():
    """Build the executable."""
    
    # Ensure dependencies
    print("Installing dependencies...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "customtkinter", "Pillow", "qrcode", "pyinstaller"
    ])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Mobile2Storage",
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--hidden-import=customtkinter",
        "--hidden-import=PIL",
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=qrcode",
        "--collect-data=customtkinter",
        "main.py"
    ]

    # Add icon if exists
    if os.path.exists("assets/icon.ico"):
        cmd.insert(-1, "--icon=assets/icon.ico")

    print()
    print("=" * 50)
    print("  Building Mobile2Storage.exe")
    print("=" * 50)
    print()

    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))

    if result.returncode == 0:
        print()
        print("=" * 50)
        print("  ✅ SUCCESS!")
        print(f"  → dist/Mobile2Storage.exe")
        print("=" * 50)
    else:
        print("❌ Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    build()
