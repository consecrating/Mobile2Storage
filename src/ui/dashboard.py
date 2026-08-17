"""
Mobile2Storage - PC Dashboard.
Two connection modes:
1. USB (ADB) — fastest, most reliable, browse files directly from PC
2. WiFi (QR code) — no cable needed, phone grants access via browser

Both modes show a FILE EXPLORER on the PC side.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import os
import tempfile
from typing import Optional, List
from PIL import Image, ImageTk

from ..core.adb_browser import AdbBrowser, PhoneFile, AdbTransferProgress
from ..core.receiver_server import (
    ReceiverServer, ServerStats, get_local_ip, find_free_port
)
from ..core.mobile_page import MOBILE_PAGE_HTML
from ..core.qr_generator import generate_qr_for_tkinter
from ..utils.helpers import format_size, format_speed, format_time


# === THEME ===
DARK_BG = "#0d1117"
CARD_BG = "#161b22"
ACCENT_BLUE = "#00d4ff"
ACCENT_GREEN = "#00ff99"
ACCENT_ORANGE = "#ff9944"
ACCENT_RED = "#ff4466"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#8b949e"
TEXT_DIM = "#484f58"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Thumbnail cache directory
THUMB_CACHE = os.path.join(tempfile.gettempdir(), "m2s_thumbcache")
os.makedirs(THUMB_CACHE, exist_ok=True)

# Image/video extensions for preview
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic"}
VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov", ".3gp", ".webm", ".flv"}


class PreviewWindow(ctk.CTkToplevel):
    """Fullscreen image/video preview with next/back navigation."""

    def __init__(self, parent, adb, files: List, start_index: int = 0):
        super().__init__(parent)
        self.title("Preview")
        self.geometry("900x650")
        self.configure(fg_color="#000000")
        self.adb = adb
        self.files = files  # List of PhoneFile (media only)
        self.index = start_index
        self._photo = None

        # Controls
        nav = ctk.CTkFrame(self, fg_color="#111111", height=50)
        nav.pack(fill="x", side="bottom")
        nav.pack_propagate(False)

        self.prev_btn = ctk.CTkButton(
            nav, text="← Previous", width=100, height=34,
            command=self._prev, corner_radius=8
        )
        self.prev_btn.pack(side="left", padx=10, pady=8)

        self.info_label = ctk.CTkLabel(
            nav, text="", font=ctk.CTkFont(size=12)
        )
        self.info_label.pack(side="left", fill="x", expand=True)

        self.next_btn = ctk.CTkButton(
            nav, text="Next →", width=100, height=34,
            command=self._next, corner_radius=8
        )
        self.next_btn.pack(side="right", padx=10, pady=8)

        # Image display (use tk.Label for reliable PhotoImage support)
        self.image_label = tk.Label(self, text="Loading...", bg="#000000",
                                    fg="#ffffff", font=("Segoe UI", 14))
        self.image_label.pack(fill="both", expand=True)

        # Keyboard bindings
        self.bind("<Left>", lambda e: self._prev())
        self.bind("<Right>", lambda e: self._next())
        self.bind("<Escape>", lambda e: self.destroy())

        self._show_current()

    def _show_current(self):
        """Display the current file."""
        if not self.files or self.index >= len(self.files):
            return

        f = self.files[self.index]
        self.info_label.configure(
            text=f"{f.name}  ({self.index + 1}/{len(self.files)})"
        )

        ext = os.path.splitext(f.name)[1].lower()
        if ext in IMAGE_EXTS:
            self._load_image(f)
        elif ext in VIDEO_EXTS:
            self.image_label.configure(
                text=f"🎬 {f.name}\n\nVideo preview not available\nTransfer to PC to play",
                image=""
            )
        else:
            self.image_label.configure(text=f.name, image="")

    def _load_image(self, f: 'PhoneFile'):
        """Pull and display image."""
        self.image_label.configure(text="Loading...", image="")

        def do_load():
            local = self.adb.pull_thumbnail(f.path, THUMB_CACHE)
            if local:
                self.after(0, lambda: self._display_image(local))
            else:
                self.after(0, lambda: self.image_label.configure(text="Failed to load"))

        threading.Thread(target=do_load, daemon=True).start()

    def _display_image(self, local_path: str):
        """Show image scaled to fit window."""
        try:
            img = Image.open(local_path)
            # Scale to fit window
            w = self.winfo_width() - 20
            h = self.winfo_height() - 80
            if w < 200: w = 850
            if h < 200: h = 550
            img.thumbnail((w, h), Image.LANCZOS)

            # Use raw PhotoImage (more reliable than CTkImage for large images)
            self._photo = ImageTk.PhotoImage(img)
            self.image_label.configure(image=self._photo, text="")
        except Exception as e:
            self.image_label.configure(text=f"Cannot display: {e}", image=None)

    def _next(self):
        if self.index < len(self.files) - 1:
            self.index += 1
            self._show_current()

    def _prev(self):
        if self.index > 0:
            self.index -= 1
            self._show_current()

class FileExplorer(ctk.CTkFrame):
    """
    File explorer showing phone files.
    Click folders to navigate, click images/videos to preview.
    """

    def __init__(self, parent, app=None, **kwargs):
        kwargs.setdefault("corner_radius", 12)
        kwargs.setdefault("fg_color", CARD_BG)
        super().__init__(parent, **kwargs)

        self.app = app  # DashboardApp reference for preview window
        self.adb: Optional[AdbBrowser] = None
        self.current_path = "/sdcard"
        self._entries: List[PhoneFile] = []
        self._selected: set = set()
        self._item_widgets = []
        self._checkboxes = []

        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 4))

        ctk.CTkLabel(
            header, text="📱 Phone Storage",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(side="left")

        self.path_label = ctk.CTkLabel(
            header, text="/sdcard",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=ACCENT_BLUE
        )
        self.path_label.pack(side="right")

        # Safety badge
        safety = ctk.CTkLabel(
            self, text="🛡️ Read-only • Files are only COPIED, never deleted or modified",
            font=ctk.CTkFont(size=10), text_color=TEXT_DIM
        )
        safety.pack(padx=14, anchor="w")

        # Navigation
        nav = ctk.CTkFrame(self, fg_color="#1c2128", corner_radius=8, height=38)
        nav.pack(fill="x", padx=12, pady=6)
        nav.pack_propagate(False)

        self.back_btn = ctk.CTkButton(
            nav, text="← Back", width=70, height=28,
            command=self._go_back, corner_radius=6,
            font=ctk.CTkFont(size=11), fg_color="#2d333b", hover_color="#3a4150"
        )
        self.back_btn.pack(side="left", padx=4, pady=4)

        self.home_btn = ctk.CTkButton(
            nav, text="🏠 Home", width=70, height=28,
            command=self._go_home, corner_radius=6,
            font=ctk.CTkFont(size=11), fg_color="#2d333b", hover_color="#3a4150"
        )
        self.home_btn.pack(side="left", padx=2, pady=4)

        self.refresh_btn = ctk.CTkButton(
            nav, text="↻ Refresh", width=75, height=28,
            command=lambda: self.load_directory(self.current_path),
            corner_radius=6, font=ctk.CTkFont(size=11),
            fg_color="#2d333b", hover_color="#3a4150"
        )
        self.refresh_btn.pack(side="left", padx=2, pady=4)

        self.select_all_btn = ctk.CTkButton(
            nav, text="☑ Select All", width=85, height=28,
            command=self._select_all, corner_radius=6,
            font=ctk.CTkFont(size=11), fg_color="#2d333b", hover_color="#3a4150"
        )
        self.select_all_btn.pack(side="left", padx=2, pady=4)

        self.sel_label = ctk.CTkLabel(
            nav, text="", font=ctk.CTkFont(size=11, weight="bold"),
            text_color=ACCENT_GREEN
        )
        self.sel_label.pack(side="right", padx=8)

        # File list
        self.file_list = ctk.CTkScrollableFrame(
            self, fg_color="#0d1117", corner_radius=8,
            scrollbar_button_color=TEXT_DIM
        )
        self.file_list.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        self.state_label = ctk.CTkLabel(
            self.file_list,
            text="🔌 Connect your phone via USB to browse files\n\n"
                 "Your files will appear here.\n"
                 "Only user files are shown (system files are hidden).",
            font=ctk.CTkFont(size=13), text_color=TEXT_DIM,
            justify="center"
        )
        self.state_label.pack(pady=50)

    def load_directory(self, path: str):
        """Load and display a directory."""
        if not self.adb or not self.adb.is_connected:
            return

        self.current_path = path
        self.path_label.configure(text=path)
        self._selected.clear()
        self._update_sel_label()

        # Show loading
        self._clear()
        self.state_label.configure(text="Loading...")
        self.state_label.pack(pady=40)

        def do_load():
            entries = self.adb.list_directory(path)
            self.after(0, lambda: self._show_entries(entries))

        threading.Thread(target=do_load, daemon=True).start()

    def _show_entries(self, entries: List[PhoneFile]):
        """Display entries."""
        self._clear()
        self.state_label.pack_forget()
        self._entries = entries

        if not entries:
            self.state_label.configure(text="Empty folder")
            self.state_label.pack(pady=40)
            return

        for i, entry in enumerate(entries):
            self._add_item(i, entry)

    def _add_item(self, index: int, entry: PhoneFile):
        """Add one file/folder entry with inline thumbnail for images."""
        ext_lower = ("." + entry.name.rsplit(".", 1)[-1].lower()) if "." in entry.name else ""
        is_image = ext_lower in IMAGE_EXTS
        is_video = ext_lower in VIDEO_EXTS
        is_media = is_image or is_video

        # Taller row for images to fit thumbnail
        row_height = 50 if is_image else 38

        frame = ctk.CTkFrame(
            self.file_list, height=row_height, corner_radius=8,
            fg_color="#161b22", border_width=1, border_color="#21262d"
        )
        frame.pack(fill="x", pady=2, padx=2)
        frame.pack_propagate(False)

        # Checkbox
        var = ctk.BooleanVar(value=False)
        cb = ctk.CTkCheckBox(
            frame, text="", variable=var,
            width=22, checkbox_width=16, checkbox_height=16,
            corner_radius=3,
            command=lambda idx=index, v=var: self._toggle(idx, v)
        )
        cb.pack(side="left", padx=(6, 2))
        self._checkboxes.append((var, cb))

        # Thumbnail or icon
        if is_image:
            # Show placeholder, load thumbnail in background
            thumb_label = ctk.CTkLabel(frame, text="🖼️", width=44, height=44)
            thumb_label.pack(side="left", padx=4)
            # Load thumbnail async
            threading.Thread(
                target=self._load_thumbnail,
                args=(entry, thumb_label, 40),
                daemon=True
            ).start()
        elif is_video:
            ctk.CTkLabel(frame, text="🎬", width=28, font=ctk.CTkFont(size=16)).pack(side="left", padx=4)
        elif entry.is_dir:
            ctk.CTkLabel(frame, text="📁", width=28, font=ctk.CTkFont(size=16)).pack(side="left", padx=4)
        else:
            ext = entry.name.rsplit(".", 1)[-1].lower() if "." in entry.name else ""
            icons = {
                "mp3": "🎵", "wav": "🎵", "flac": "🎵", "m4a": "🎵",
                "pdf": "📄", "doc": "📄", "docx": "📄", "txt": "📝",
                "zip": "📦", "rar": "📦", "7z": "📦", "apk": "📱",
            }
            ctk.CTkLabel(frame, text=icons.get(ext, "📎"), width=28).pack(side="left", padx=4)

        # Name (clickable for folders and media)
        color = ACCENT_BLUE if entry.is_dir else TEXT_PRIMARY
        font = ctk.CTkFont(size=12, weight="bold") if entry.is_dir else ctk.CTkFont(size=12)

        name_label = ctk.CTkLabel(
            frame, text=entry.name, font=font,
            text_color=color, anchor="w",
            cursor="hand2" if (entry.is_dir or is_media) else ""
        )
        name_label.pack(side="left", fill="x", expand=True, padx=4)

        if entry.is_dir:
            name_label.bind("<Button-1>", lambda e, p=entry.path: self.load_directory(p))
        elif is_media:
            name_label.bind("<Button-1>", lambda e, idx=index: self._open_preview(idx))

        # Size
        if not entry.is_dir and entry.size > 0:
            ctk.CTkLabel(
                frame, text=format_size(entry.size),
                font=ctk.CTkFont(size=10), text_color=TEXT_DIM, width=65
            ).pack(side="right", padx=6)

        self._item_widgets.append(frame)

    def _load_thumbnail(self, entry: PhoneFile, label: ctk.CTkLabel, size: int):
        """Pull image from phone and set as thumbnail on the label."""
        try:
            if not self.adb:
                return
            local = self.adb.pull_thumbnail(entry.path, THUMB_CACHE)
            if not local:
                return
            img = Image.open(local)
            img.thumbnail((size, size), Image.LANCZOS)
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
            # Update label on main thread
            label.after(0, lambda: self._set_thumb(label, photo))
        except Exception:
            pass

    def _set_thumb(self, label: ctk.CTkLabel, photo):
        """Set thumbnail image on label (must run on main thread)."""
        try:
            label.configure(image=photo, text="")
            label._thumb_ref = photo  # Keep reference to prevent GC
        except Exception:
            pass

    def _toggle(self, index: int, var):
        if var.get():
            self._selected.add(index)
        else:
            self._selected.discard(index)
        self._update_sel_label()

    def _select_all(self):
        all_selected = len(self._selected) == len(self._entries)
        self._selected.clear()
        if not all_selected:
            self._selected = set(range(len(self._entries)))
        # Update checkboxes
        for i, (var, _) in enumerate(self._checkboxes):
            var.set(i in self._selected)
        self._update_sel_label()

    def _update_sel_label(self):
        n = len(self._selected)
        if n > 0:
            # Calculate total size of selected
            total = sum(
                self._entries[i].size for i in self._selected
                if not self._entries[i].is_dir
            )
            dirs = sum(1 for i in self._selected if self._entries[i].is_dir)
            files = n - dirs
            parts = []
            if dirs: parts.append(f"{dirs} folders")
            if files: parts.append(f"{files} files")
            text = ", ".join(parts)
            if total > 0:
                text += f" ({format_size(total)})"
            self.sel_label.configure(text=f"✓ {text}")
        else:
            self.sel_label.configure(text="")

    def _go_back(self):
        parent = os.path.dirname(self.current_path)
        if parent and parent != self.current_path:
            self.load_directory(parent)

    def _go_home(self):
        self.load_directory("/sdcard")

    def _clear(self):
        for w in self._item_widgets:
            w.destroy()
        self._item_widgets.clear()
        self._checkboxes.clear()

    def get_selected_items(self) -> List[PhoneFile]:
        """Get selected PhoneFile items."""
        return [self._entries[i] for i in self._selected if i < len(self._entries)]

    def _open_preview(self, index: int):
        """Open media file in fullscreen preview window."""
        if not self.adb:
            return
        # Collect all media files in current listing for next/back navigation
        media_files = []
        media_index = 0
        for i, entry in enumerate(self._entries):
            if entry.is_dir:
                continue
            ext = ("." + entry.name.rsplit(".", 1)[-1].lower()) if "." in entry.name else ""
            if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
                if i == index:
                    media_index = len(media_files)
                media_files.append(entry)

        if media_files:
            PreviewWindow(self.winfo_toplevel(), self.adb, media_files, media_index)


class DashboardApp(ctk.CTk):
    """
    Main app with USB (ADB) + WiFi connection options.
    """

    def __init__(self):
        super().__init__()

        self.title("Mobile2Storage ⚡")
        self.geometry("900x700")
        self.minsize(800, 600)
        self.configure(fg_color=DARK_BG)

        # Core
        self.adb = AdbBrowser()
        self._server: Optional[ReceiverServer] = None
        self._destination = os.path.join(os.path.expanduser("~"), "Desktop", "Mobile2Storage")
        self._transferring = False

        self._build_ui()

    def _build_ui(self):
        # === HEADER ===
        header = ctk.CTkFrame(self, height=50, fg_color=CARD_BG, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="⚡ Mobile2Storage",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left", padx=15, pady=10)

        self.status_label = ctk.CTkLabel(
            header, text="● Not connected",
            font=ctk.CTkFont(size=11), text_color=ACCENT_ORANGE
        )
        self.status_label.pack(side="left", padx=10)

        # Destination button
        self.dest_btn = ctk.CTkButton(
            header, text=f"📂 {os.path.basename(self._destination)}",
            command=self._change_destination,
            width=150, height=28, corner_radius=8,
            font=ctk.CTkFont(size=11)
        )
        self.dest_btn.pack(side="right", padx=15)

        # === MAIN AREA ===
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=12, pady=10)

        # Left panel: Connection
        left = ctk.CTkFrame(main, fg_color=CARD_BG, corner_radius=12, width=270)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        self._build_connection_panel(left)

        # Right panel: File Explorer + Transfer
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True)

        # File Explorer
        self.explorer = FileExplorer(right, app=self)
        self.explorer.pack(fill="both", expand=True, pady=(0, 8))

        # Transfer controls
        bottom = ctk.CTkFrame(right, fg_color=CARD_BG, corner_radius=12, height=90)
        bottom.pack(fill="x")
        bottom.pack_propagate(False)

        btn_row = ctk.CTkFrame(bottom, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(10, 4))

        self.transfer_btn = ctk.CTkButton(
            btn_row, text="📥 Transfer Selected to PC",
            command=self._start_transfer, height=36,
            corner_radius=10, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00aa44", hover_color="#00cc55"
        )
        self.transfer_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.cancel_btn = ctk.CTkButton(
            btn_row, text="⏹", width=36, height=36,
            command=self._cancel_transfer, corner_radius=10,
            fg_color=ACCENT_RED, hover_color="#ff6688"
        )
        self.cancel_btn.pack(side="right")

        self.progress_label = ctk.CTkLabel(
            bottom, text="Select files/folders above, then click Transfer",
            font=ctk.CTkFont(size=11), text_color=TEXT_SECONDARY
        )
        self.progress_label.pack(padx=12, anchor="w")

        self.progress_bar = ctk.CTkProgressBar(bottom, height=6, corner_radius=3)
        self.progress_bar.pack(fill="x", padx=12, pady=(4, 10))
        self.progress_bar.set(0)

    def _build_connection_panel(self, parent):
        """Build the connection panel with USB + WiFi options."""
        ctk.CTkLabel(
            parent, text="🔌 Connect Phone",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(padx=12, pady=(12, 8), anchor="w")

        # === USB SECTION ===
        usb_frame = ctk.CTkFrame(parent, fg_color="#0d1a26", corner_radius=10)
        usb_frame.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(
            usb_frame, text="⚡ USB (Recommended)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=ACCENT_GREEN
        ).pack(padx=10, pady=(8, 2), anchor="w")

        ctk.CTkLabel(
            usb_frame, text="Fastest • Most reliable • Direct access",
            font=ctk.CTkFont(size=10), text_color=TEXT_SECONDARY
        ).pack(padx=10, anchor="w")

        self.usb_btn = ctk.CTkButton(
            usb_frame, text="🔌 Connect via USB",
            command=self._connect_usb, height=34,
            corner_radius=8, font=ctk.CTkFont(size=12, weight="bold")
        )
        self.usb_btn.pack(fill="x", padx=10, pady=(8, 10))

        self.usb_status = ctk.CTkLabel(
            usb_frame, text="",
            font=ctk.CTkFont(size=10), text_color=TEXT_SECONDARY
        )
        self.usb_status.pack(padx=10, pady=(0, 8))

        # ADB availability check
        if self.adb.adb_available:
            self.usb_status.configure(text="ADB ✓ ready", text_color=ACCENT_GREEN)
        else:
            self.usb_status.configure(
                text="ADB not found — install Platform Tools",
                text_color=ACCENT_RED
            )

        # === WiFi SECTION ===
        wifi_frame = ctk.CTkFrame(parent, fg_color="transparent")
        wifi_frame.pack(fill="x", padx=12, pady=(8, 0))

        ctk.CTkLabel(
            wifi_frame, text="📶 WiFi (Alternative)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_SECONDARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            wifi_frame, text="No cable • Phone browser needed",
            font=ctk.CTkFont(size=10), text_color=TEXT_DIM
        ).pack(anchor="w")

        self.wifi_btn = ctk.CTkButton(
            wifi_frame, text="📶 Start WiFi Mode",
            command=self._start_wifi_mode, height=30,
            corner_radius=8, font=ctk.CTkFont(size=11),
            fg_color=TEXT_DIM, hover_color="#3a4050"
        )
        self.wifi_btn.pack(fill="x", pady=(6, 0))

        self.qr_label = ctk.CTkLabel(wifi_frame, text="")
        self.qr_label.pack(pady=5)

        self.wifi_url_label = ctk.CTkLabel(
            wifi_frame, text="", font=ctk.CTkFont(size=9),
            text_color=ACCENT_BLUE
        )
        self.wifi_url_label.pack()

        # === DEVICE INFO ===
        self.device_info = ctk.CTkLabel(
            parent, text="",
            font=ctk.CTkFont(size=10), text_color=TEXT_SECONDARY,
            wraplength=240
        )
        self.device_info.pack(padx=12, pady=(15, 10), anchor="w")

    def _connect_usb(self):
        """Connect to phone via USB ADB."""
        self.usb_btn.configure(state="disabled", text="Connecting...")
        self.usb_status.configure(text="", text_color=TEXT_SECONDARY)

        def do_connect():
            success, message = self.adb.connect()
            self.after(0, lambda: self._on_usb_connected(success, message))

        threading.Thread(target=do_connect, daemon=True).start()

    def _on_usb_connected(self, success: bool, message: str):
        """Handle USB connection result."""
        if success:
            self.usb_btn.configure(text="✓ Connected", fg_color=ACCENT_GREEN)
            self.usb_status.configure(text=message, text_color=ACCENT_GREEN)
            self.status_label.configure(text="● USB Connected ✓", text_color=ACCENT_GREEN)

            # Show device info
            info = self.adb.get_device_info()
            if info:
                self.device_info.configure(
                    text=f"📱 {info['model']} • Android {info['android']}\n"
                         f"💾 {format_size(info['storage_free'])} free / "
                         f"{format_size(info['storage_total'])}"
                )

            # Connect explorer and load root
            self.explorer.adb = self.adb
            self.explorer.load_directory("/sdcard")
        else:
            self.usb_btn.configure(state="normal", text="🔌 Connect via USB")
            self.usb_status.configure(text=message, text_color=ACCENT_RED)

    def _start_wifi_mode(self):
        """Start WiFi mode with QR code."""
        try:
            ip = get_local_ip()
            port = find_free_port()
            url = f"http://{ip}:{port}"

            os.makedirs(self._destination, exist_ok=True)

            self._server = ReceiverServer(
                port=port,
                destination=self._destination,
                mobile_html=MOBILE_PAGE_HTML,
                progress_callback=self._on_wifi_progress,
                phone_ready_callback=self._on_phone_ready
            )

            threading.Thread(
                target=self._server.serve_forever, daemon=True
            ).start()

            # Show QR
            qr_image = generate_qr_for_tkinter(url, size=120)
            if qr_image:
                self.qr_label.configure(image=qr_image, text="")
                self.qr_label._image = qr_image
            else:
                self.qr_label.configure(text=f"Open:\n{url}", text_color=ACCENT_BLUE)

            self.wifi_url_label.configure(text=url)
            self.wifi_btn.configure(text="✓ WiFi Server Running", state="disabled")

        except Exception as e:
            self.wifi_url_label.configure(text=f"Error: {e}", text_color=ACCENT_RED)

    def _on_phone_ready(self):
        """Phone connected via WiFi."""
        self.after(0, lambda: self.status_label.configure(
            text="● WiFi Connected ✓", text_color=ACCENT_GREEN
        ))
        # Load via WiFi server
        if self._server and not self.adb.is_connected:
            self.after(0, lambda: self.explorer.state_label.configure(
                text="Phone connected via WiFi.\nUse USB for file browsing or\nsend files from phone browser."
            ))

    def _on_wifi_progress(self, stats: ServerStats):
        """WiFi transfer progress."""
        try:
            self.after(0, lambda: self.progress_label.configure(
                text=f"📶 WiFi: {stats.total_files_received} files received "
                     f"({format_size(stats.total_bytes_received)})"
            ))
        except Exception:
            pass

    def _start_transfer(self):
        """Transfer selected items from phone to PC."""
        if not self.adb.is_connected:
            messagebox.showwarning("Not Connected", "Connect your phone via USB first.")
            return

        items = self.explorer.get_selected_items()
        if not items:
            messagebox.showinfo("Nothing Selected", "Select files or folders to transfer.")
            return

        self._transferring = True
        self.transfer_btn.configure(state="disabled", text="Transferring...")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Starting transfer...")

        def do_transfer():
            self.adb.add_progress_callback(self._on_adb_progress)
            self.adb.transfer_items(items, self._destination)
            self.after(0, self._on_transfer_done)

        threading.Thread(target=do_transfer, daemon=True).start()

    def _on_adb_progress(self, progress: AdbTransferProgress):
        """Update UI with ADB transfer progress."""
        try:
            self.after(0, lambda: self._update_adb_progress(progress))
        except Exception:
            pass

    def _update_adb_progress(self, p: AdbTransferProgress):
        """Update progress display (count-based, since we don't pre-scan)."""
        # Animated indeterminate-style bar based on activity
        if p.is_active:
            # Pulse the bar so user sees it's working
            current = self.progress_bar.get()
            self.progress_bar.set((current + 0.02) % 1.0)
            self.progress_label.configure(
                text=f"📥 {p.transferred_files} files copied • {p.current_file}"
            )
        else:
            self.progress_bar.set(1.0)
            self.progress_label.configure(
                text=f"📥 {p.transferred_files} files copied"
            )

    def _on_transfer_done(self):
        """Transfer complete."""
        self._transferring = False
        p = self.adb.progress
        self.transfer_btn.configure(state="normal", text="📥 Transfer Selected to PC")
        self.progress_bar.set(1.0)

        failed = len(p.failed_files)
        msg = f"✅ Done! {p.transferred_files} files transferred"
        if failed:
            msg += f" • {failed} failed"
        self.progress_label.configure(text=msg)

        messagebox.showinfo(
            "Transfer Complete",
            f"✅ {p.transferred_files} files transferred\n"
            f"❌ {failed} failed\n\n"
            f"Saved to: {self._destination}"
        )

    def _cancel_transfer(self):
        """Cancel transfer."""
        if self._transferring:
            self.adb.cancel_transfer()
            self.progress_label.configure(text="⏹ Cancelled")
            self.transfer_btn.configure(state="normal", text="📥 Transfer Selected to PC")

    def _change_destination(self):
        """Change save folder."""
        path = filedialog.askdirectory(title="Choose save location")
        if path:
            self._destination = path
            if self._server:
                self._server.destination_path = path
            self.dest_btn.configure(text=f"📂 {os.path.basename(path)}")

    def on_closing(self):
        if self._transferring:
            self.adb.cancel_transfer()
        if self._server:
            self._server.shutdown()
        self.destroy()


def main():
    app = DashboardApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
