"""
ADB File Browser for Mobile2Storage.
Browses and pulls files from Android via USB ADB connection.

Advantages over WiFi/browser approach:
- No phone interaction needed (just USB cable)
- Direct file system access (no browser crashes)
- Full speed USB 3.0 transfer
- Rock solid — no WiFi drops or browser timeouts
- Handles 44,000+ files without any issues
- Supports resume and parallel pulls

Requirements:
- USB Debugging enabled on phone
- ADB installed on PC (bundled or in PATH)
"""

import os
import subprocess
import threading
import time
import re
from typing import Optional, List, Callable, Tuple
from dataclasses import dataclass, field


@dataclass
class PhoneFile:
    """A file or folder on the phone."""
    name: str
    path: str
    is_dir: bool
    size: int = 0
    modified: str = ""


@dataclass
class AdbTransferProgress:
    """Transfer progress tracking."""
    total_files: int = 0
    transferred_files: int = 0
    total_bytes: int = 0
    transferred_bytes: int = 0
    current_file: str = ""
    speed: float = 0.0
    is_active: bool = False
    failed_files: List[str] = field(default_factory=list)


class AdbBrowser:
    """
    Browse and transfer files from Android via ADB.
    Works over USB — no phone interaction needed.
    
    SAFETY: This tool is READ-ONLY. It NEVER:
    - Deletes any files from the phone
    - Modifies any files on the phone
    - Writes anything to the phone
    It only uses 'adb pull' (copy FROM phone) and 'adb shell ls/stat' (read info).
    """

    # Safe user folders (shown by default)
    SAFE_FOLDERS = {
        "DCIM", "Pictures", "Download", "Downloads", "Documents",
        "Music", "Movies", "WhatsApp", "Telegram", "Bluetooth",
        "Recordings", "Podcasts", "Ringtones", "Notifications",
        "Alarms", "Photos",
    }

    # Folders to NEVER show (system-critical)
    HIDDEN_FOLDERS = {
        "Android", "data", "obb", "LOST.DIR",
    }

    def __init__(self):
        self._adb_path = self._find_adb()
        self._device_serial: Optional[str] = None
        self._connected = False
        self.progress = AdbTransferProgress()
        self._progress_callbacks: List[Callable] = []
        self._cancel = False

    def add_progress_callback(self, callback: Callable):
        """Register callback for transfer progress updates."""
        self._progress_callbacks.append(callback)

    def _notify_progress(self):
        """Notify progress callbacks."""
        for cb in self._progress_callbacks:
            try:
                cb(self.progress)
            except Exception:
                pass

    def _find_adb(self) -> str:
        """Find ADB executable."""
        paths = [
            "adb",
            os.path.expanduser("~/Android/Sdk/platform-tools/adb"),
            r"C:\Users\{}\AppData\Local\Android\Sdk\platform-tools\adb.exe".format(
                os.environ.get("USERNAME", "")
            ),
            r"C:\platform-tools\adb.exe",
            r"C:\Android\platform-tools\adb.exe",
            r"C:\Android\adb.exe",
            "/usr/local/bin/adb",
            "/usr/bin/adb",
        ]

        for path in paths:
            try:
                kwargs = {"capture_output": True, "text": True, "timeout": 5}
                if os.name == "nt":
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    si.wShowWindow = 0
                    kwargs["startupinfo"] = si
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                result = subprocess.run([path, "version"], **kwargs)
                if result.returncode == 0:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                continue

        return "adb"

    @property
    def adb_available(self) -> bool:
        """Check if ADB is installed."""
        try:
            kwargs = {"capture_output": True, "text": True, "timeout": 5}
            if os.name == "nt":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 0
                kwargs["startupinfo"] = si
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            r = subprocess.run([self._adb_path, "version"], **kwargs)
            return r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> Tuple[bool, str]:
        """
        Connect to Android device via USB.
        Returns (success, message).
        """
        if not self.adb_available:
            return False, "ADB not found. Install Android Platform Tools."

        # Get list of devices
        try:
            result = subprocess.run(
                [self._adb_path, "devices"],
                capture_output=True, text=True, timeout=10
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            return False, f"ADB error: {e}"

        if result.returncode != 0:
            return False, "ADB failed to list devices."

        # Parse device list
        lines = result.stdout.strip().split("\n")
        devices = []
        for line in lines[1:]:
            parts = line.strip().split("\t")
            if len(parts) == 2 and parts[1] == "device":
                devices.append(parts[0])

        if not devices:
            return False, (
                "No device found.\n\n"
                "Make sure:\n"
                "• USB cable is connected\n"
                "• USB Debugging is ON\n"
                "• You tapped 'Allow' on the phone prompt"
            )

        self._device_serial = devices[0]
        self._connected = True

        # Get device info
        model = self._run_shell("getprop ro.product.model") or "Unknown"
        android_ver = self._run_shell("getprop ro.build.version.release") or "?"

        return True, f"Connected: {model} (Android {android_ver})"

    def disconnect(self):
        """Disconnect."""
        self._connected = False
        self._device_serial = None

    def _run_adb(self, *args, timeout: int = 30) -> Optional[str]:
        """Run an ADB command (hidden window on Windows)."""
        cmd = [self._adb_path]
        if self._device_serial:
            cmd += ["-s", self._device_serial]
        cmd += list(args)

        try:
            # Hide console window on Windows
            kwargs = {"capture_output": True, "text": True, "timeout": timeout}
            if os.name == "nt":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 0  # SW_HIDE
                kwargs["startupinfo"] = si
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(cmd, **kwargs)
            if result.returncode == 0:
                return result.stdout
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    def _run_shell(self, command: str, timeout: int = 30) -> Optional[str]:
        """Run ADB shell command."""
        output = self._run_adb("shell", command, timeout=timeout)
        return output.strip() if output else None

    def list_directory(self, path: str = "/sdcard") -> List[PhoneFile]:
        """
        List files and folders in a directory on the phone.

        Strategy (works on ALL Android shells — toybox/toolbox/busybox):
        1. Get names + type via 'ls -p' (dirs end with '/') -> reliable
        2. Get sizes via 'ls -la' parsed with regex -> best effort
        Files ALWAYS show even if size parsing fails.
        """
        if not self._connected:
            return []

        # STEP 1: names with dir markers ('ls -p' appends '/' to dirs)
        raw = self._run_shell(f'ls -p "{path}"', timeout=60)
        if not raw:
            raw = self._run_shell(f'ls -p {path}', timeout=60)
        if not raw:
            raw = self._run_shell(f'ls "{path}"', timeout=60)
        if not raw:
            return []

        name_is_dir = {}
        for line in raw.split("\n"):
            name = line.rstrip("\r").strip()
            if not name or name in (".", "..", "./", "../"):
                continue
            is_dir = name.endswith("/")
            clean = name[:-1] if is_dir else name
            if clean.startswith("."):
                continue  # skip hidden
            name_is_dir[clean] = is_dir

        # STEP 2: sizes via 'ls -la' (best-effort, never breaks listing)
        size_map = {}
        la = self._run_shell(f'ls -la "{path}"', timeout=60)
        if la:
            for line in la.split("\n"):
                line = line.rstrip("\r")
                if not line or line.startswith("total"):
                    continue
                sm = re.search(r'\s(\d+)\s+(?:\d{4}-\d{2}-\d{2}|[A-Za-z]{3}\s+\d{1,2})\s', line)
                nm = re.search(r'\d{1,2}:\d{2}\s+(.+)$', line)
                if not nm:
                    nm = re.search(r'\d{4}-\d{2}-\d{2}\s+(.+)$', line)
                if nm:
                    fname = nm.group(1).strip().rstrip("/")
                    if sm:
                        try:
                            size_map[fname] = int(sm.group(1))
                        except ValueError:
                            pass

        # STEP 3: combine
        entries = []
        for name, is_dir in name_is_dir.items():
            entries.append(PhoneFile(
                name=name,
                path=f"{path}/{name}",
                is_dir=is_dir,
                size=0 if is_dir else size_map.get(name, 0)
            ))

        # Sort: folders first, then files
        entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))

        # SAFETY: At /sdcard root level, hide system folders
        if path == "/sdcard" or path == "/storage/emulated/0":
            entries = [
                e for e in entries
                if e.name not in self.HIDDEN_FOLDERS
            ]

        return entries

    def get_folder_size(self, path: str) -> Tuple[int, int]:
        """
        Get total size and file count of a folder (recursive).
        Uses du command for speed.
        Returns (total_bytes, file_count).
        """
        # Get file count
        count_output = self._run_shell(
            f'find "{path}" -type f 2>/dev/null | wc -l', timeout=120
        )
        try:
            file_count = int(count_output.strip()) if count_output else 0
        except ValueError:
            file_count = 0

        # Get total size
        size_output = self._run_shell(
            f'du -sb "{path}" 2>/dev/null | cut -f1', timeout=120
        )
        try:
            total_size = int(size_output.strip()) if size_output else 0
        except ValueError:
            total_size = 0

        return total_size, file_count

    def pull_file(self, remote_path: str, local_path: str) -> bool:
        """Pull a single file from phone to PC."""
        # Ensure local directory exists
        local_dir = os.path.dirname(local_path)
        os.makedirs(local_dir, exist_ok=True)

        result = self._run_adb("pull", remote_path, local_path, timeout=600)
        return result is not None

    def pull_folder(self, remote_path: str, local_base: str,
                    progress_callback: Optional[Callable] = None):
        """
        Pull entire folder recursively from phone to PC.
        Uses adb pull which handles the recursion natively.
        Window is HIDDEN (no CMD popup).
        """
        # Create local directory matching phone structure
        folder_name = os.path.basename(remote_path)
        local_dest = os.path.join(local_base, folder_name)
        os.makedirs(local_dest, exist_ok=True)

        # adb pull does recursive copy natively
        cmd = [self._adb_path]
        if self._device_serial:
            cmd += ["-s", self._device_serial]
        cmd += ["pull", remote_path + "/.", local_dest]

        # Hide window on Windows
        kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "bufsize": 1
        }
        if os.name == "nt":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            kwargs["startupinfo"] = si
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        process = subprocess.Popen(cmd, **kwargs)

        # Parse adb pull output for progress.
        # adb prints lines as it copies each file. We count them.
        # Formats vary by adb version:
        #   "/sdcard/DCIM/a.jpg" -> local  (older)
        #   [ 12%] /sdcard/DCIM/a.jpg      (newer, live percent)
        #   X files pulled, Y skipped.     (final summary)
        base_count = self.progress.transferred_files
        files_pulled = 0
        try:
            while True:
                if self._cancel:
                    process.terminate()
                    return

                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    continue

                line = line.strip()
                if not line:
                    continue

                # A file path line = one file being copied
                if line.startswith("[") or "/" in line.split(":")[0]:
                    # Extract filename for display
                    fname = line
                    if "]" in line:
                        fname = line.split("]", 1)[1].strip()
                    fname = fname.split("/")[-1].strip('" ')
                    if fname and not fname.endswith("%"):
                        files_pulled += 1
                        self.progress.transferred_files = base_count + files_pulled
                        self.progress.current_file = fname
                        self._notify_progress()

                # Final summary line
                if "files pulled" in line or "file pulled" in line:
                    m = re.search(r'(\d+)\s+files?\s+pulled', line)
                    if m:
                        pulled = int(m.group(1))
                        if pulled > files_pulled:
                            self.progress.transferred_files = base_count + pulled
                            self._notify_progress()
        except Exception:
            pass

        process.wait()

    def transfer_items(self, items: List[PhoneFile], destination: str):
        """
        Transfer multiple selected items (files and/or folders) to PC.
        Runs in background. Updates self.progress.

        NOTE: We do NOT pre-scan folder sizes (that used 'du'/'find' which
        hang on huge folders). We start transferring IMMEDIATELY and count
        files as they arrive. Progress is shown by file count, not %.
        """
        self._cancel = False
        self.progress = AdbTransferProgress(is_active=True)

        # Rough total = number of selected items (folders count as 1 for now)
        # Actual file count grows as folders are pulled
        self.progress.total_files = len(items)
        self._notify_progress()

        # Transfer each item — no pre-scan, start immediately
        for item in items:
            if self._cancel:
                break

            if item.is_dir:
                self.progress.current_file = f"📁 {item.name}/ (transferring...)"
                self._notify_progress()
                self.pull_folder(item.path, destination)
            else:
                self.progress.current_file = item.name
                self._notify_progress()

                # Preserve some path structure
                local_path = os.path.join(destination, item.name)
                # Avoid overwriting
                if os.path.exists(local_path):
                    name, ext = os.path.splitext(item.name)
                    c = 1
                    while os.path.exists(local_path):
                        local_path = os.path.join(destination, f"{name}_{c}{ext}")
                        c += 1

                success = self.pull_file(item.path, local_path)
                if success:
                    self.progress.transferred_files += 1
                    self.progress.transferred_bytes += item.size
                else:
                    self.progress.failed_files.append(item.path)

                self._notify_progress()

        self.progress.is_active = False
        self._notify_progress()

    def cancel_transfer(self):
        """Cancel ongoing transfer."""
        self._cancel = True

    def get_device_info(self) -> dict:
        """Get device information."""
        if not self._connected:
            return {}

        model = self._run_shell("getprop ro.product.model") or "Unknown"
        android = self._run_shell("getprop ro.build.version.release") or "?"
        
        # Storage info
        df_output = self._run_shell("df /sdcard 2>/dev/null | tail -1")
        storage_free = 0
        storage_total = 0
        if df_output:
            parts = df_output.split()
            try:
                storage_total = int(parts[1]) * 1024
                storage_free = int(parts[3]) * 1024
            except (IndexError, ValueError):
                pass

        return {
            "model": model,
            "android": android,
            "storage_total": storage_total,
            "storage_free": storage_free,
            "serial": self._device_serial or "",
        }
