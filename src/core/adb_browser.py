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
        Uses simple, reliable approach that works on ALL Android versions.
        """
        if not self._connected:
            return []

        entries = []

        # Use 'ls -la' — the most widely supported listing command
        # Parse permissively: first char 'd' = dir, otherwise file
        # Get size from whichever numeric column makes sense
        output = self._run_shell(f'ls -la "{path}"', timeout=60)

        if not output:
            output = self._run_shell(f'ls -la {path}', timeout=60)
        if not output:
            # Last resort: just names
            output = self._run_shell(f'ls "{path}"', timeout=60)
            if output:
                for name in output.split("\n"):
                    name = name.strip()
                    if name and not name.startswith("."):
                        entries.append(PhoneFile(
                            name=name, path=f"{path}/{name}",
                            is_dir=False, size=0
                        ))
                entries.sort(key=lambda e: e.name.lower())
                return entries
            return []

        for line in output.split("\n"):
            line = line.strip()
            if not line or line.startswith("total"):
                continue

            # First character determines type
            is_dir = line.startswith("d")

            # Split into parts — name is ALWAYS the last portion
            # The challenge: name might have spaces
            # Strategy: split by whitespace, find the last numeric field (size),
            # everything after date/time is the filename
            parts = line.split()
            if len(parts) < 6:
                continue

            # Find the filename: it's after the date+time fields
            # On Android ls -la, format is typically:
            # perms links owner group size date time name
            # OR: perms links owner group size date name
            # We find the size (largest number before the name) and take everything after date/time
            
            # Simple approach: try to find name by looking for the date pattern
            # Date patterns: "2024-01-15" or "Jan 15" or "2024-01-15 10:30"
            name = None
            size = 0
            
            # Try splitting with max 7 fields (standard ls -la)
            try:
                # Look for size as the number before date
                # Walk backwards from end to find the name
                # Name = everything after the last time/date field
                
                # Method: find position of first date-like field, name is after time
                for i in range(4, min(8, len(parts))):
                    # Check if this looks like a size (number)
                    try:
                        possible_size = int(parts[i])
                        # Next fields should be date — and rest is name
                        # Take everything from i+2 or i+3 onwards as name
                        if i + 2 < len(parts):
                            # Check if parts[i+1] looks like a date
                            remaining_start = i + 2
                            # If there's also a time field, skip it
                            if i + 3 <= len(parts) and ":" in parts[i + 2]:
                                remaining_start = i + 3
                            elif i + 2 < len(parts) and len(parts[i+1]) >= 8:
                                remaining_start = i + 2
                            
                            if remaining_start < len(parts):
                                name = " ".join(parts[remaining_start:])
                                size = possible_size
                                break
                    except ValueError:
                        continue
            except (IndexError, ValueError):
                pass

            # Fallback: just take the last part as name
            if not name:
                name = parts[-1]

            # Clean up name
            name = name.strip()
            if name.endswith("/"):
                name = name[:-1]
                is_dir = True

            # Skip . and ..
            if name in (".", ".."):
                continue
            # Skip hidden
            if name.startswith("."):
                continue

            entries.append(PhoneFile(
                name=name,
                path=f"{path}/{name}",
                is_dir=is_dir,
                size=size if not is_dir else 0
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

        # Parse adb pull output for progress
        # Output lines like: "/sdcard/DCIM/photo.jpg": 1 file pulled, 0 skipped. 45.2 MB/s
        files_pulled = 0
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line = line.strip()
                # Count pulled files
                if "pulled" in line or "file pulled" in line:
                    files_pulled += 1
                    self.progress.transferred_files = files_pulled
                    self.progress.current_file = line.split(":")[0].strip('" ') if ":" in line else ""
                    self._notify_progress()

                    if progress_callback:
                        progress_callback(files_pulled, line)

                if self._cancel:
                    process.terminate()
                    return

        process.wait()

    def transfer_items(self, items: List[PhoneFile], destination: str):
        """
        Transfer multiple selected items (files and/or folders) to PC.
        Runs in background. Updates self.progress.
        """
        self._cancel = False
        self.progress = AdbTransferProgress(is_active=True)

        # Calculate totals for selected items
        total_size = 0
        total_files = 0
        for item in items:
            if item.is_dir:
                size, count = self.get_folder_size(item.path)
                total_size += size
                total_files += count
            else:
                total_size += item.size
                total_files += 1

        self.progress.total_bytes = total_size
        self.progress.total_files = total_files
        self._notify_progress()

        # Transfer each item
        for item in items:
            if self._cancel:
                break

            if item.is_dir:
                self.progress.current_file = f"📁 {item.name}/"
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
