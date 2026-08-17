"""
ADB File Browser for Mobile2Storage.
Browses and pulls files from Android via USB ADB connection.
READ-ONLY: only pulls files, never deletes or modifies anything.
"""

import os
import subprocess
import re
from typing import Optional, List, Callable, Tuple
from dataclasses import dataclass, field


@dataclass
class PhoneFile:
    name: str
    path: str
    is_dir: bool
    size: int = 0


@dataclass
class AdbTransferProgress:
    total_files: int = 0
    transferred_files: int = 0
    total_bytes: int = 0
    transferred_bytes: int = 0
    current_file: str = ""
    speed: float = 0.0
    is_active: bool = False
    failed_files: List[str] = field(default_factory=list)


def _hide_window_kwargs():
    """Get subprocess kwargs to hide console window on Windows."""
    kwargs = {}
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        kwargs["startupinfo"] = si
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


class AdbBrowser:
    """
    Browse and transfer files from Android via ADB (USB).
    READ-ONLY — never deletes or modifies phone files.
    """

    HIDDEN_FOLDERS = {"Android", "data", "obb", "LOST.DIR"}

    def __init__(self):
        self._adb = self._find_adb()
        self._serial: Optional[str] = None
        self._connected = False
        self.progress = AdbTransferProgress()
        self._callbacks: List[Callable] = []
        self._cancel = False

    def add_progress_callback(self, cb: Callable):
        self._callbacks.append(cb)

    def _notify(self):
        for cb in self._callbacks:
            try:
                cb(self.progress)
            except Exception:
                pass

    def _find_adb(self) -> str:
        for p in ["adb",
                  os.path.expanduser("~/Android/Sdk/platform-tools/adb"),
                  r"C:\platform-tools\adb.exe",
                  r"C:\Android\adb.exe",
                  r"C:\Android\platform-tools\adb.exe"]:
            try:
                r = subprocess.run([p, "version"], capture_output=True,
                                   text=True, timeout=5, **_hide_window_kwargs())
                if r.returncode == 0:
                    return p
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                continue
        return "adb"

    @property
    def adb_available(self) -> bool:
        try:
            r = subprocess.run([self._adb, "version"], capture_output=True,
                               text=True, timeout=5, **_hide_window_kwargs())
            return r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _run(self, *args, timeout=30) -> Optional[str]:
        """Run adb command with args passed individually. Hidden window."""
        cmd = [self._adb]
        if self._serial:
            cmd += ["-s", self._serial]
        cmd += list(args)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=timeout, **_hide_window_kwargs())
            return r.stdout if r.returncode == 0 else None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    def connect(self) -> Tuple[bool, str]:
        """Connect to device via USB."""
        if not self.adb_available:
            return False, "ADB not found. Install Android Platform Tools."

        out = self._run("devices")
        if not out:
            return False, "ADB failed."

        devices = []
        for line in out.strip().split("\n")[1:]:
            parts = line.strip().split("\t")
            if len(parts) == 2 and parts[1] == "device":
                devices.append(parts[0])

        if not devices:
            return False, "No device found. Check USB cable and USB Debugging."

        self._serial = devices[0]
        self._connected = True

        model = (self._run("shell", "getprop", "ro.product.model") or "").strip()
        ver = (self._run("shell", "getprop", "ro.build.version.release") or "").strip()
        return True, f"Connected: {model} (Android {ver})"

    def disconnect(self):
        self._connected = False
        self._serial = None

    def list_directory(self, path: str = "/sdcard") -> List[PhoneFile]:
        """
        List directory contents using 'adb shell ls -la PATH'.
        Each argument passed separately (not as a single string) to
        avoid Windows shell quoting issues that caused empty results.
        """
        if not self._connected:
            return []

        # Key: trailing slash forces ls to list CONTENTS, not the dir itself
        # Without it, some devices return the symlink entry for /sdcard
        target = path if path.endswith("/") else path + "/"
        output = self._run("shell", "ls", "-la", target, timeout=60)
        if not output:
            output = self._run("shell", "ls", "-l", target, timeout=60)
        if not output:
            return []

        entries = []
        for line in output.split("\n"):
            line = line.rstrip("\r").strip()
            if not line or line.startswith("total"):
                continue
            if len(line) < 10:
                continue

            # First char determines type
            first = line[0]
            if first == "d":
                is_dir = True
            elif first in ("-", "l"):
                is_dir = False
            else:
                continue

            # Parse name: everything after time (HH:MM) or date
            name = None
            size = 0

            # Try: name after HH:MM
            m = re.search(r'\d{2}:\d{2}\s+(.+)$', line)
            if not m:
                # Try: name after YYYY-MM-DD
                m = re.search(r'\d{4}-\d{2}-\d{2}\s+(.+)$', line)
            if m:
                name = m.group(1).strip()
            else:
                # Fallback: last space-separated token
                name = line.split()[-1]

            # Parse size: number before date
            sm = re.search(r'\s(\d+)\s+\d{4}-\d{2}-\d{2}', line)
            if not sm:
                sm = re.search(r'\s(\d+)\s+\w{3}\s+\d', line)
            if sm:
                try:
                    size = int(sm.group(1))
                except ValueError:
                    size = 0

            # Clean name
            if " -> " in name:
                name = name.split(" -> ")[0].strip()
            name = name.rstrip("/")

            if name in (".", "..") or name.startswith(".") or not name:
                continue

            entries.append(PhoneFile(
                name=name,
                path=f"{path}/{name}",
                is_dir=is_dir,
                size=size if not is_dir else 0
            ))

        entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))

        # Safety: hide system folders at root
        if path in ("/sdcard", "/storage/emulated/0"):
            entries = [e for e in entries if e.name not in self.HIDDEN_FOLDERS]

        return entries

    def pull_file(self, remote: str, local: str) -> bool:
        """Pull single file from phone."""
        os.makedirs(os.path.dirname(local), exist_ok=True)
        return self._run("pull", remote, local, timeout=600) is not None

    def pull_folder(self, remote: str, local_base: str):
        """Pull entire folder recursively via 'adb pull'. No CMD window."""
        folder = os.path.basename(remote)
        dest = os.path.join(local_base, folder)
        os.makedirs(dest, exist_ok=True)

        cmd = [self._adb]
        if self._serial:
            cmd += ["-s", self._serial]
        cmd += ["pull", remote + "/.", dest]

        kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
        }
        kwargs.update(_hide_window_kwargs())

        proc = subprocess.Popen(cmd, **kwargs)

        base = self.progress.transferred_files
        count = 0
        try:
            while True:
                if self._cancel:
                    proc.terminate()
                    return
                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        break
                    continue
                line = line.strip()
                # Each file pulled produces output
                if "/" in line or "pull" in line:
                    count += 1
                    self.progress.transferred_files = base + count
                    # Extract short filename
                    parts = line.replace("\\", "/").split("/")
                    self.progress.current_file = parts[-1][:40] if parts else line[:40]
                    self._notify()
        except Exception:
            pass

        proc.wait()

    def transfer_items(self, items: List[PhoneFile], destination: str):
        """Transfer selected items to PC. Starts immediately, no pre-scan."""
        self._cancel = False
        self.progress = AdbTransferProgress(is_active=True, total_files=len(items))
        self._notify()

        for item in items:
            if self._cancel:
                break

            if item.is_dir:
                self.progress.current_file = f"{item.name}/"
                self._notify()
                self.pull_folder(item.path, destination)
            else:
                self.progress.current_file = item.name
                self._notify()
                local = os.path.join(destination, item.name)
                if os.path.exists(local):
                    n, ext = os.path.splitext(item.name)
                    c = 1
                    while os.path.exists(local):
                        local = os.path.join(destination, f"{n}_{c}{ext}")
                        c += 1
                ok = self.pull_file(item.path, local)
                if ok:
                    self.progress.transferred_files += 1
                    self.progress.transferred_bytes += item.size
                else:
                    self.progress.failed_files.append(item.path)
                self._notify()

        self.progress.is_active = False
        self._notify()

    def cancel_transfer(self):
        self._cancel = True

    def get_device_info(self) -> dict:
        if not self._connected:
            return {}
        model = (self._run("shell", "getprop", "ro.product.model") or "").strip()
        ver = (self._run("shell", "getprop", "ro.build.version.release") or "").strip()
        df = (self._run("shell", "df", "/sdcard") or "")
        total = free = 0
        lines = df.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[-1].split()
            try:
                total = int(parts[1]) * 1024
                free = int(parts[3]) * 1024
            except (IndexError, ValueError):
                pass
        return {"model": model, "android": ver,
                "storage_total": total, "storage_free": free,
                "serial": self._serial or ""}
