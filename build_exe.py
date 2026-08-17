"""
Build script to create Mobile2Storage.exe using PyInstaller.

Run this script to generate a standalone Windows executable:
    python build_exe.py

The .exe will be created in the 'dist' folder.
"""

import subprocess
import sys
import os


def build():
    """Build the executable using PyInstaller."""
    
    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Mobile2Storage",
        "--onefile",                    # Single .exe file
        "--windowed",                   # No console window
        "--icon=assets/icon.ico",       # App icon (if exists)
        "--add-data=assets;assets",     # Include assets
        "--clean",                      # Clean cache
        "--noconfirm",                  # Don't ask confirmation
        # Hidden imports for customtkinter
        "--hidden-import=customtkinter",
        "--hidden-import=PIL",
        "--hidden-import=PIL._tkinter_finder",
        # Collect all customtkinter data
        "--collect-data=customtkinter",
        # Main script
        "main.py"
    ]
    
    # Remove icon flag if file doesn't exist
    if not os.path.exists("assets/icon.ico"):
        cmd = [c for c in cmd if "icon.ico" not in c]
    
    # Remove assets flag if folder is empty
    if not os.path.exists("assets") or not os.listdir("assets"):
        cmd = [c for c in cmd if "assets;assets" not in c]
    
    print("=" * 60)
    print("  Mobile2Storage - Building Executable")
    print("=" * 60)
    print()
    print("Building with command:")
    print(" ".join(cmd))
    print()
    
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    
    if result.returncode == 0:
        exe_path = os.path.join("dist", "Mobile2Storage.exe")
        print()
        print("=" * 60)
        print("  ✅ BUILD SUCCESSFUL!")
        print(f"  Output: {os.path.abspath(exe_path)}")
        print("=" * 60)
        print()
        print("To run: double-click Mobile2Storage.exe in the dist/ folder")
    else:
        print()
        print("❌ Build failed! Check the output above for errors.")
        sys.exit(1)


if __name__ == "__main__":
    build()
