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
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Ensure dependencies
    print("Installing dependencies...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "customtkinter", "Pillow", "qrcode", "pyinstaller"
    ])

    # Write the spec file dynamically (avoids import issues)
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect customtkinter assets
ctk_datas = collect_data_files("customtkinter")
ctk_imports = collect_submodules("customtkinter")

a = Analysis(
    ["main.py"],
    pathex=[r"{script_dir}"],
    binaries=[],
    datas=ctk_datas,
    hiddenimports=[
        "src",
        "src.core",
        "src.core.receiver_server",
        "src.core.mobile_page",
        "src.core.qr_generator",
        "src.ui",
        "src.ui.dashboard",
        "src.utils",
        "src.utils.helpers",
        "customtkinter",
        "PIL",
        "PIL._tkinter_finder",
        "qrcode",
        "qrcode.image.pil",
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
    ] + ctk_imports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "scipy", "pandas", "pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Mobile2Storage",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico" if os.path.exists("assets/icon.ico") else None,
)
'''

    spec_path = os.path.join(script_dir, "Mobile2Storage.spec")
    with open(spec_path, "w") as f:
        f.write(spec_content)

    print()
    print("=" * 50)
    print("  Building Mobile2Storage.exe")
    print("=" * 50)
    print()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        spec_path
    ]

    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = os.path.join("dist", "Mobile2Storage.exe")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print()
            print("=" * 50)
            print("  ✅ BUILD SUCCESSFUL!")
            print(f"  → dist/Mobile2Storage.exe ({size_mb:.1f} MB)")
            print("=" * 50)
            print()
            print("  Double-click Mobile2Storage.exe to run!")
        else:
            print()
            print("=" * 50)
            print("  ✅ BUILD SUCCESSFUL!")
            print("  → dist/Mobile2Storage.exe")
            print("=" * 50)
    else:
        print()
        print("❌ Build failed! See errors above.")
        print()
        print("TROUBLESHOOTING:")
        print("  1. Make sure you're in the Mobile2Storage folder")
        print("  2. Try: pip install --upgrade pyinstaller customtkinter Pillow qrcode")
        print("  3. Try: python -m PyInstaller --onefile --windowed main.py")
        sys.exit(1)


if __name__ == "__main__":
    build()
