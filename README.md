# ⚡ Mobile2Storage

## Transfer 50GB+ from Android to PC — in 3 steps

No USB debugging. No developer options. No ADB. No complicated setup.

---

## How It Works

```
1. Open Mobile2Storage.exe on your PC
2. Scan the QR code with your phone
3. Pick files and tap Send
```

**That's it.** Files arrive on your PC at full WiFi speed.

---

## 3 Transfer Modes

| Mode | What it does |
|------|-------------|
| **📄 Pick Specific Files** | Choose exactly which files you want to send |
| **📁 Pick a Folder** | Select any folder — all contents transfer with structure preserved |
| **🗂️ Transfer Everything** | Sends ALL your files (photos, videos, docs, music). Skips system files automatically. **Preserves exact same folder names & directory structure on PC.** |

### "Transfer Everything" Mode Details:

- ✅ Transfers all your personal files
- ✅ Keeps exact folder names and paths (e.g., `DCIM/Camera/photo.jpg` → same on PC)
- ✅ Automatically skips: Android system data, cache, thumbnails, hidden files, temp files
- ✅ No duplicates, no junk

---

## Speed

- Transfers over your local WiFi at **full speed** (typically 20-80 MB/s)
- Large files split into 5MB chunks for reliable fast transfer
- Multiple files handled efficiently — no "stuck calculating"
- Works with **any file size** — 1KB to 50GB+

---

## Requirements

- **PC:** Windows 10/11 (or Mac/Linux with Python)
- **Phone:** Android 10+ (or any phone with a web browser)
- **Both devices on the same WiFi network**

That's all. No apps to install on your phone — it uses your browser.

---

## Quick Start

### Option 1: Run .exe (Windows)

```
1. Download Mobile2Storage.exe
2. Double-click to run
3. Scan QR code with your phone
4. Done!
```

### Option 2: Run from source

```bash
git clone https://github.com/consecrating/Mobile2Storage.git
cd Mobile2Storage
pip install -r requirements.txt
python main.py
```

### Option 3: Build your own .exe

```bash
pip install -r requirements.txt
python build_exe.py
# → dist/Mobile2Storage.exe
```

---

## FAQ

**Q: Do I need to install anything on my phone?**
No. It uses your phone's browser (Chrome, Samsung Internet, etc.)

**Q: Does it work without internet?**
Yes! It uses your local WiFi network only. No data goes to the internet.

**Q: What about large video files (5GB+)?**
Works perfectly. Files are automatically chunked for reliable transfer.

**Q: Can I select specific files or do I have to send everything?**
You get 3 options: pick specific files, pick a folder, or transfer everything.

**Q: Will it preserve my folder structure?**
Yes! If you pick a folder or use "Transfer Everything", the exact same folders and filenames appear on your PC.

**Q: What system files does it skip?**
Android/data, Android/obb, .cache, .thumbnails, LOST.DIR, hidden files (starting with .), .tmp files, and other system junk.

---

## Project Structure

```
Mobile2Storage/
├── main.py                      # Entry point
├── build_exe.py                 # Build script
├── requirements.txt             # Dependencies
├── src/
│   ├── core/
│   │   ├── receiver_server.py   # HTTP server receiving files
│   │   ├── mobile_page.py       # Mobile web UI (HTML/JS)
│   │   └── qr_generator.py     # QR code generation
│   ├── ui/
│   │   └── dashboard.py        # PC dashboard (shows QR + progress)
│   └── utils/
│       └── helpers.py           # Formatting utilities
```

---

**Made to solve one problem: getting your files from phone to PC without headaches.**
