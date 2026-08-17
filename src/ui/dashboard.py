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
from typing import Optional, List

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


class FileExplorer(ctk.CTkFrame):
    """
    File explorer showing phone files.
    Works with ADB browser for direct file listing.
    """

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("corner_radius", 12)
        kwargs.setdefault("fg_color", CARD_BG)
        super().__init__(parent, **kwargs)

        self.adb: Optional[AdbBrowser] = None
        self.current_path = "/sdcard"
        self._entries: List[PhoneFile] = []
        self._selected: set = set()  # indices of selected entries
        self._item_widgets = []
        self._checkboxes = []

        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            header, text="📱 Phone Storage",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        self.path_label = ctk.CTkLabel(
            header, text="/sdcard",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=TEXT_SECONDARY
        )
        self.path_label.pack(side="right")

        # Navigation
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=12, pady=4)

        self.back_btn = ctk.CTkButton(
            nav, text="⬅ Back", width=65, height=26,
            command=self._go_back, corner_radius=6,
            font=ctk.CTkFont(size=11)
        )
        self.back_btn.pack(side="left", padx=(0, 4))

        self.home_btn = ctk.CTkButton(
            nav, text="🏠", width=30, height=26,
            command=self._go_home, corner_radius=6
        )
        self.home_btn.pack(side="left", padx=(0, 4))

        self.refresh_btn = ctk.CTkButton(
            nav, text="🔄", width=30, height=26,
            command=lambda: self.load_directory(self.current_path),
            corner_radius=6
        )
        self.refresh_btn.pack(side="left", padx=(0, 8))

        self.select_all_btn = ctk.CTkButton(
            nav, text="☑ All", width=50, height=26,
            command=self._select_all, corner_radius=6,
            font=ctk.CTkFont(size=11)
        )
        self.select_all_btn.pack(side="left")

        self.sel_label = ctk.CTkLabel(
            nav, text="", font=ctk.CTkFont(size=11),
            text_color=ACCENT_GREEN
        )
        self.sel_label.pack(side="right")

        # File list
        self.file_list = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=TEXT_DIM
        )
        self.file_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.state_label = ctk.CTkLabel(
            self.file_list, text="Connect your phone to browse files",
            font=ctk.CTkFont(size=12), text_color=TEXT_DIM
        )
        self.state_label.pack(pady=40)

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
        """Add one file/folder entry."""
        frame = ctk.CTkFrame(
            self.file_list, height=34, corner_radius=5,
            fg_color="#1c2128"
        )
        frame.pack(fill="x", pady=1)
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

        # Icon + Name
        if entry.is_dir:
            icon = "📁"
            color = ACCENT_BLUE
            font = ctk.CTkFont(size=12, weight="bold")
        else:
            ext = entry.name.rsplit(".", 1)[-1].lower() if "." in entry.name else ""
            icons = {
                "jpg": "🖼️", "jpeg": "🖼️", "png": "🖼️", "heic": "🖼️", "webp": "🖼️",
                "mp4": "🎬", "avi": "🎬", "mkv": "🎬", "mov": "🎬", "3gp": "🎬",
                "mp3": "🎵", "wav": "🎵", "flac": "🎵", "m4a": "🎵",
                "pdf": "📄", "doc": "📄", "docx": "📄", "txt": "📄",
                "zip": "📦", "rar": "📦", "7z": "📦", "apk": "📱",
            }
            icon = icons.get(ext, "📎")
            color = TEXT_PRIMARY
            font = ctk.CTkFont(size=12)

        ctk.CTkLabel(frame, text=icon, width=22).pack(side="left", padx=2)

        name_label = ctk.CTkLabel(
            frame, text=entry.name, font=font,
            text_color=color, anchor="w",
            cursor="hand2" if entry.is_dir else ""
        )
        name_label.pack(side="left", fill="x", expand=True, padx=4)

        if entry.is_dir:
            name_label.bind("<Button-1>", lambda e, p=entry.path: self.load_directory(p))

        # Size
        if not entry.is_dir and entry.size > 0:
            ctk.CTkLabel(
                frame, text=format_size(entry.size),
                font=ctk.CTkFont(size=10), text_color=TEXT_DIM, width=65
            ).pack(side="right", padx=6)

        self._item_widgets.append(frame)

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
        self.explorer = FileExplorer(right)
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
        """Update progress display."""
        if p.total_files > 0:
            pct = p.transferred_files / p.total_files
            self.progress_bar.set(pct)
            self.progress_label.configure(
                text=f"📥 {p.transferred_files}/{p.total_files} files • "
                     f"{p.current_file}"
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
