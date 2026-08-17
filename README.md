# 📱➡️💻 Mobile2Storage

## Fast, Verified Android-to-PC File Transfer (50GB+)

> **Solve the problem once and for all:** No more stuck "calculating", no more slow transfers, no more corrupted files.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🚨 The Problem

When transferring **50GB+ data** from Android 10+ to PC:
- Windows Explorer gets **stuck on "Calculating..."** for hours
- Large files **slow down or fail** mid-transfer
- Files get **corrupted** without any warning
- No way to **resume** interrupted transfers
- MTP protocol is unreliable for large datasets

## ✅ The Solution

**Mobile2Storage** uses cutting-edge transfer technology:

| Feature | How It Solves the Problem |
|---------|--------------------------|
| 🔥 **Chunked Parallel Transfers** | Files split into optimal chunks (16-128MB), transferred simultaneously. Never gets stuck. |
| 🛡️ **SHA-256 End-to-End Verification** | Hash computed on Android, verified on PC. **ZERO corruption guaranteed.** |
| ⚡ **Streaming File Discovery** | Starts transferring immediately - no waiting for full file count calculation. |
| 🔄 **Auto-Resume with WAL** | Write-Ahead Logging ensures interrupted transfers resume from exact byte position. |
| 🔁 **Smart Retry with Backoff** | Failed chunks auto-retry with exponential backoff. Never loses data. |
| ⚛️ **Atomic Writes** | Files only appear after full verification. No partial/corrupt files on disk. |
| 📊 **Advanced Dashboard** | Eye-catching real-time progress with circular indicator, speed stats, and file queue. |

---

## 🖥️ Screenshots

The dashboard features:
- **Large circular progress indicator** with animated gradient
- **Big percentage display** showing exactly how much is transferred vs remaining
- **Real-time speed, peak speed, and ETA** stat cards
- **File queue** with per-file progress bars
- **Integrity verification** counter showing all files are verified

---

## ⚡ Quick Start

### Prerequisites

1. **ADB (Android Debug Bridge)** - [Download Platform Tools](https://developer.android.com/tools/releases/platform-tools)
2. **Python 3.10+** (only for running from source)
3. **Android Device** with:
   - **USB Debugging** enabled (Settings → Developer Options → USB Debugging)
   - OR **Wireless Debugging** enabled (Android 11+)

### Option 1: Run the .exe (Windows)

```bash
# Download Mobile2Storage.exe from Releases
# Double-click to run - that's it!
```

### Option 2: Run from Source

```bash
# Clone the repository
git clone https://github.com/consecrating/Mobile2Storage.git
cd Mobile2Storage

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Option 3: Build Your Own .exe

```bash
# Method 1: Use the build script
python build_exe.py

# Method 2: Use the batch file (Windows)
build_exe.bat

# Method 3: Manual PyInstaller
pip install pyinstaller customtkinter Pillow
pyinstaller Mobile2Storage.spec

# The exe will be in dist/Mobile2Storage.exe
```

---

## 📱 How to Connect Your Android Device

### USB Connection (Recommended for 50GB+ transfers)

1. Enable **Developer Options** on your Android:
   - Go to Settings → About Phone
   - Tap "Build Number" 7 times
2. Enable **USB Debugging**:
   - Settings → Developer Options → USB Debugging → ON
3. Connect phone via USB cable
4. Click **"🔌 USB"** in Mobile2Storage
5. Accept the debugging prompt on your phone

### WiFi Connection (Android 11+)

1. Enable **Wireless Debugging**:
   - Settings → Developer Options → Wireless Debugging → ON
2. Note the **IP address** shown
3. Click **"📶 WiFi"** in Mobile2Storage
4. Enter the IP address
5. Accept the pairing prompt on your phone

---

## 🔧 How It Works

### Transfer Pipeline

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│ 1. DISCOVER │ ──→ │ 2. HASH      │ ──→ │ 3. TRANSFER │ ──→ │ 4.VERIFY │
│  (Streaming)│     │ (On Android) │     │  (Chunked)  │     │(SHA-256) │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────┘
       │                    │                    │                   │
       ▼                    ▼                    ▼                   ▼
  Start instantly    Compute hash on     Parallel chunks      Compare hashes
  No "calculating"   device BEFORE       with retry &         Device vs PC
  stall             transfer begins      resume support       MUST match!
                                                                    │
                                                                    ▼
                                                           ┌──────────────┐
                                                           │ 5. ATOMIC    │
                                                           │    SAVE      │
                                                           │ File appears │
                                                           │ only after   │
                                                           │ verification │
                                                           └──────────────┘
```

### Why It's Fast

| Traditional (MTP/Explorer) | Mobile2Storage |
|---------------------------|----------------|
| Scans ALL files before starting | Starts transfer immediately |
| Single file at a time | 4 files in parallel |
| No chunking | Adaptive 16-128MB chunks |
| No resume | Resume from exact byte |
| Silent corruption | SHA-256 verification |
| Gets stuck on large dirs | Streaming discovery |

### Data Integrity Guarantee

Every file goes through this verification chain:
1. **Source Hash** - SHA-256 computed on Android device before transfer
2. **Chunk Hash** - Each chunk verified individually after transfer
3. **Size Check** - Byte-exact size comparison
4. **Final Hash** - Complete file hash computed on PC
5. **Atomic Rename** - File only appears if ALL checks pass

If ANY check fails → automatic retry (up to 5 times with exponential backoff).

---

## 📁 Project Structure

```
Mobile2Storage/
├── main.py                 # Application entry point
├── build_exe.py            # .exe build script
├── build_exe.bat           # Windows batch builder
├── Mobile2Storage.spec     # PyInstaller configuration
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── assets/                 # Icons and images
└── src/
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   ├── connection_manager.py   # ADB USB/WiFi connections
    │   ├── file_discovery.py       # Streaming file scanner
    │   └── transfer_engine.py      # Advanced transfer engine
    ├── ui/
    │   ├── __init__.py
    │   ├── dashboard.py            # Main dashboard window
    │   └── widgets.py              # Custom eye-catching widgets
    └── utils/
        ├── __init__.py
        └── helpers.py              # Utility functions
```

---

## 🛡️ Safety Features

- **Write-Ahead Log (WAL)** - Even if the app crashes, no data is lost
- **Atomic file operations** - Files never appear in a corrupt state
- **Exponential backoff retry** - Smart retry that doesn't hammer the device
- **Pre-allocation** - Disk space reserved upfront to prevent fragmentation
- **fsync after every chunk** - Data flushed to physical disk, not just OS buffer

---

## ⚙️ Configuration

The engine auto-configures based on your files:

| File Size | Chunk Size | Strategy |
|-----------|-----------|----------|
| < 50MB | Single pull | Direct ADB pull |
| 50MB - 500MB | 16MB chunks | Parallel chunked |
| 500MB - 2GB | 64MB chunks | Large parallel |
| > 2GB | 128MB chunks | Maximum throughput |

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "ADB not found" | Install [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools) and add to PATH |
| Device not detected (USB) | Try a different USB cable, enable USB Debugging |
| WiFi connection fails | Ensure phone and PC are on same network |
| Slow speeds | Use USB 3.0 port and cable for best speed |
| Transfer hangs | The app auto-retries; check USB cable quality |

---

## 📄 License

MIT License - Free to use, modify, and distribute.

---

## 🤝 Contributing

Contributions welcome! Please open an issue or PR.

---

**Made with ❤️ to solve the most frustrating file transfer problem.**
