"""
Mobile2Storage - PC Dashboard with Remote File Explorer.

Architecture:
- Phone grants storage access (one tap)
- PC shows a FILE EXPLORER of the phone's files
- User browses and selects folders/files FROM THE PC
- PC requests transfers — phone sends them over WiFi

The phone never processes or displays large file lists.
All heavy lifting done on the PC side.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import os
from typing import Optional, List

from ..core.receiver_server import (
    ReceiverServer, ServerStats, FileTransfer,
    get_local_ip, find_free_port
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


class PhoneFileExplorer(ctk.CTkFrame):
    """
    File explorer that browses the phone's files remotely.
    Folders load on-demand (only when you click into them).
    """

    def __init__(self, parent, server: ReceiverServer, **kwargs):
        kwargs.setdefault("corner_radius", 12)
        kwargs.setdefault("fg_color", CARD_BG)
        super().__init__(parent, **kwargs)
        
        self.server = server
        self.current_path = ""
        self._selected_items = set()
        self._current_entries = []
        self._item_widgets = []
        
        self._build_ui()

    def _build_ui(self):
        # Header with path breadcrumb
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 5))

        ctk.CTkLabel(
            header, text="📱 Phone Files",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        self.path_label = ctk.CTkLabel(
            header, text="/",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_SECONDARY
        )
        self.path_label.pack(side="right")

        # Navigation buttons
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=12, pady=4)

        self.back_btn = ctk.CTkButton(
            nav, text="⬅ Back", width=70, height=28,
            command=self._go_back, corner_radius=8,
            font=ctk.CTkFont(size=11)
        )
        self.back_btn.pack(side="left", padx=(0, 5))

        self.refresh_btn = ctk.CTkButton(
            nav, text="🔄 Refresh", width=80, height=28,
            command=self._refresh, corner_radius=8,
            font=ctk.CTkFont(size=11)
        )
        self.refresh_btn.pack(side="left", padx=(0, 5))

        self.select_all_btn = ctk.CTkButton(
            nav, text="☑ Select All", width=90, height=28,
            command=self._select_all, corner_radius=8,
            font=ctk.CTkFont(size=11)
        )
        self.select_all_btn.pack(side="left")

        self.selection_label = ctk.CTkLabel(
            nav, text="", font=ctk.CTkFont(size=11),
            text_color=ACCENT_GREEN
        )
        self.selection_label.pack(side="right")

        # File list (scrollable)
        self.file_list = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=TEXT_DIM
        )
        self.file_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Loading / empty state
        self.state_label = ctk.CTkLabel(
            self.file_list, text="Waiting for phone to connect...",
            font=ctk.CTkFont(size=13), text_color=TEXT_DIM
        )
        self.state_label.pack(pady=30)

    def load_directory(self, path: str = ""):
        """Load a directory listing from the phone."""
        self.current_path = path
        self.path_label.configure(text="/" + path if path else "/")
        self._selected_items.clear()
        self._update_selection_label()

        # Show loading state
        self._clear_items()
        self.state_label.configure(text="Loading...")
        self.state_label.pack(pady=30)

        # Load in background thread
        def do_load():
            result = self.server.list_phone_directory(path)
            self.after(0, lambda: self._display_entries(result))

        threading.Thread(target=do_load, daemon=True).start()

    def _display_entries(self, result: dict):
        """Display directory entries."""
        self._clear_items()
        self.state_label.pack_forget()

        entries = result.get("entries", [])
        error = result.get("error", "")

        if error:
            self.state_label.configure(text=f"Error: {error}")
            self.state_label.pack(pady=30)
            return

        if not entries:
            self.state_label.configure(text="Empty folder")
            self.state_label.pack(pady=30)
            return

        self._current_entries = entries

        for entry in entries:
            self._add_entry_widget(entry)

    def _add_entry_widget(self, entry: dict):
        """Add a single file/folder entry to the list."""
        name = entry["name"]
        is_dir = entry["type"] == "dir"
        size = entry.get("size", 0)

        frame = ctk.CTkFrame(
            self.file_list, height=36, corner_radius=6,
            fg_color="#1c2128"
        )
        frame.pack(fill="x", pady=1)
        frame.pack_propagate(False)

        # Checkbox for selection
        var = ctk.BooleanVar(value=False)
        cb = ctk.CTkCheckBox(
            frame, text="", variable=var,
            width=24, height=24,
            checkbox_width=18, checkbox_height=18,
            corner_radius=4,
            command=lambda n=name, v=var: self._toggle_select(n, v)
        )
        cb.pack(side="left", padx=(8, 4))

        # Icon
        if is_dir:
            icon = "📁"
        else:
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            icon_map = {
                "jpg": "🖼️", "jpeg": "🖼️", "png": "🖼️", "heic": "🖼️",
                "mp4": "🎬", "avi": "🎬", "mkv": "🎬", "mov": "🎬",
                "mp3": "🎵", "wav": "🎵", "flac": "🎵", "m4a": "🎵",
                "pdf": "📄", "doc": "📄", "docx": "📄", "txt": "📄",
                "zip": "📦", "rar": "📦", "apk": "📱",
            }
            icon = icon_map.get(ext, "📎")

        icon_label = ctk.CTkLabel(frame, text=icon, width=24)
        icon_label.pack(side="left", padx=2)

        # Name (clickable for folders)
        name_label = ctk.CTkLabel(
            frame, text=name,
            font=ctk.CTkFont(size=12, weight="bold" if is_dir else "normal"),
            text_color=ACCENT_BLUE if is_dir else TEXT_PRIMARY,
            anchor="w", cursor="hand2" if is_dir else ""
        )
        name_label.pack(side="left", fill="x", expand=True, padx=4)

        if is_dir:
            name_label.bind("<Button-1>", lambda e, n=name: self._open_folder(n))

        # Size (for files)
        if not is_dir and size > 0:
            ctk.CTkLabel(
                frame, text=format_size(size),
                font=ctk.CTkFont(size=10), text_color=TEXT_DIM, width=70
            ).pack(side="right", padx=8)

        self._item_widgets.append(frame)

    def _open_folder(self, name: str):
        """Navigate into a folder."""
        new_path = f"{self.current_path}/{name}" if self.current_path else name
        self.load_directory(new_path)

    def _go_back(self):
        """Navigate to parent folder."""
        if "/" in self.current_path:
            parent = self.current_path.rsplit("/", 1)[0]
        else:
            parent = ""
        self.load_directory(parent)

    def _refresh(self):
        """Refresh current directory."""
        self.load_directory(self.current_path)

    def _toggle_select(self, name: str, var):
        """Toggle file/folder selection."""
        if var.get():
            self._selected_items.add(name)
        else:
            self._selected_items.discard(name)
        self._update_selection_label()

    def _select_all(self):
        """Select all items in current view."""
        self._selected_items = {e["name"] for e in self._current_entries}
        self._update_selection_label()
        # Refresh checkboxes
        self._refresh()

    def _update_selection_label(self):
        """Update selection count display."""
        count = len(self._selected_items)
        if count > 0:
            self.selection_label.configure(text=f"✓ {count} selected")
        else:
            self.selection_label.configure(text="")

    def _clear_items(self):
        """Clear file list."""
        for w in self._item_widgets:
            w.destroy()
        self._item_widgets.clear()

    def get_selected_paths(self) -> List[str]:
        """Get full paths of selected items."""
        paths = []
        for name in self._selected_items:
            if self.current_path:
                paths.append(f"{self.current_path}/{name}")
            else:
                paths.append(name)
        return paths

    def get_selected_count(self) -> int:
        return len(self._selected_items)


class DashboardApp(ctk.CTk):
    """
    PC Dashboard with remote phone file explorer.
    Browse phone files from PC → select → transfer.
    """

    def __init__(self):
        super().__init__()

        self.title("Mobile2Storage ⚡")
        self.geometry("850x700")
        self.minsize(750, 600)
        self.configure(fg_color=DARK_BG)

        self._server: Optional[ReceiverServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._destination = os.path.join(os.path.expanduser("~"), "Desktop", "Mobile2Storage")
        self._server_url = ""
        self._phone_connected = False
        self._transferring = False

        self._build_ui()
        self.after(500, self._start_server)

    def _build_ui(self):
        # HEADER
        header = ctk.CTkFrame(self, height=50, fg_color=CARD_BG, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="⚡ Mobile2Storage",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left", padx=15, pady=10)

        self.connection_badge = ctk.CTkLabel(
            header, text="● Phone not connected",
            font=ctk.CTkFont(size=11), text_color=ACCENT_ORANGE
        )
        self.connection_badge.pack(side="left", padx=10)

        # Destination
        self.dest_btn = ctk.CTkButton(
            header, text=f"📂 {os.path.basename(self._destination)}",
            command=self._change_destination,
            width=140, height=28, corner_radius=8,
            font=ctk.CTkFont(size=11)
        )
        self.dest_btn.pack(side="right", padx=15)

        # MAIN AREA
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=12, pady=10)

        # Left: QR + Instructions (narrow)
        left = ctk.CTkFrame(main, fg_color=CARD_BG, corner_radius=12, width=260)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        ctk.CTkLabel(
            left, text="📱 Connect Phone",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(padx=12, pady=(12, 5), anchor="w")

        # QR code
        self.qr_label = ctk.CTkLabel(left, text="Starting...")
        self.qr_label.pack(padx=12, pady=5)

        self.url_label = ctk.CTkLabel(
            left, text="", font=ctk.CTkFont(size=10),
            text_color=ACCENT_BLUE, wraplength=230
        )
        self.url_label.pack(padx=12, pady=2)

        # Instructions
        steps_frame = ctk.CTkFrame(left, fg_color="#0d1a26", corner_radius=8)
        steps_frame.pack(fill="x", padx=12, pady=10)

        for step in [
            "1. Scan QR with phone camera",
            "2. Tap 'Grant Storage Access'",
            "3. Browse & transfer from here ➡️"
        ]:
            ctk.CTkLabel(
                steps_frame, text=step,
                font=ctk.CTkFont(size=11), anchor="w",
                text_color=TEXT_SECONDARY
            ).pack(fill="x", padx=10, pady=2)

        # Right: File Explorer + Transfer button
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True)

        # File explorer (takes most space)
        self.explorer = PhoneFileExplorer(right, None)  # Server set later
        self.explorer.pack(fill="both", expand=True, pady=(0, 8))

        # Transfer button + progress
        bottom = ctk.CTkFrame(right, fg_color=CARD_BG, corner_radius=12, height=100)
        bottom.pack(fill="x")
        bottom.pack_propagate(False)

        btn_row = ctk.CTkFrame(bottom, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=10)

        self.transfer_btn = ctk.CTkButton(
            btn_row, text="📥 Transfer Selected to PC",
            command=self._start_transfer, height=38,
            corner_radius=10, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00aa44", hover_color="#00cc55"
        )
        self.transfer_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.progress_label = ctk.CTkLabel(
            bottom, text="Select files/folders above, then click Transfer",
            font=ctk.CTkFont(size=11), text_color=TEXT_SECONDARY
        )
        self.progress_label.pack(padx=12)

        self.progress_bar = ctk.CTkProgressBar(bottom, height=6, corner_radius=3)
        self.progress_bar.pack(fill="x", padx=12, pady=(4, 10))
        self.progress_bar.set(0)

    def _start_server(self):
        """Start the server."""
        try:
            ip = get_local_ip()
            port = find_free_port()
            self._server_url = f"http://{ip}:{port}"
            os.makedirs(self._destination, exist_ok=True)

            self._server = ReceiverServer(
                port=port,
                destination=self._destination,
                mobile_html=MOBILE_PAGE_HTML,
                progress_callback=self._on_progress,
                phone_ready_callback=self._on_phone_ready
            )

            # Connect explorer to server
            self.explorer.server = self._server

            self._server_thread = threading.Thread(
                target=self._server.serve_forever, daemon=True
            )
            self._server_thread.start()

            # Show QR
            self._show_qr()
            self.url_label.configure(text=f"Or open: {self._server_url}")

        except Exception as e:
            self.qr_label.configure(text=f"Error: {e}", text_color=ACCENT_RED)

    def _show_qr(self):
        """Show QR code."""
        qr_image = generate_qr_for_tkinter(self._server_url, size=160)
        if qr_image:
            self.qr_label.configure(image=qr_image, text="")
            self.qr_label._image = qr_image
        else:
            self.qr_label.configure(
                text=f"Open on phone:\n{self._server_url}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=ACCENT_BLUE
            )

    def _on_phone_ready(self):
        """Called when phone grants access."""
        self._phone_connected = True
        self.after(0, self._phone_connected_ui)

    def _phone_connected_ui(self):
        """Update UI when phone connects."""
        self.connection_badge.configure(
            text="● Phone connected ✓", text_color=ACCENT_GREEN
        )
        # Load root directory
        self.explorer.load_directory("")

    def _on_progress(self, stats: ServerStats):
        """Update progress during transfer."""
        try:
            self.after(0, lambda: self._update_progress(stats))
        except Exception:
            pass

    def _update_progress(self, stats: ServerStats):
        if stats.total_files_received > 0:
            self.progress_label.configure(
                text=f"✅ {stats.total_files_received} files received "
                     f"({format_size(stats.total_bytes_received)})"
            )

    def _start_transfer(self):
        """Transfer selected items from phone to PC."""
        if not self._phone_connected:
            messagebox.showwarning(
                "Phone Not Connected",
                "Scan the QR code with your phone first,\n"
                "then tap 'Grant Storage Access'."
            )
            return

        selected = self.explorer.get_selected_paths()
        if not selected:
            messagebox.showinfo("Nothing Selected", "Select files or folders to transfer.")
            return

        self.transfer_btn.configure(state="disabled", text="Transferring...")
        self.progress_label.configure(text=f"Transferring {len(selected)} items...")
        self.progress_bar.set(0)

        def do_transfer():
            total = len(selected)
            for i, path in enumerate(selected):
                # Check if it's a directory — if so, request all files in it
                entry = next(
                    (e for e in self.explorer._current_entries if e["name"] == path.split("/")[-1]),
                    None
                )

                if entry and entry["type"] == "dir":
                    # Request transfer of entire folder
                    self._transfer_folder(path)
                else:
                    # Single file
                    self._server.request_file_transfer(path)

                progress = (i + 1) / total
                self.after(0, lambda p=progress, idx=i+1: self._update_transfer_progress(p, idx, total))

            self.after(0, self._transfer_complete)

        threading.Thread(target=do_transfer, daemon=True).start()

    def _transfer_folder(self, folder_path: str):
        """Recursively transfer a folder."""
        result = self._server.list_phone_directory(folder_path)
        entries = result.get("entries", [])

        for entry in entries:
            item_path = f"{folder_path}/{entry['name']}"
            if entry["type"] == "dir":
                self._transfer_folder(item_path)
            else:
                self._server.request_file_transfer(item_path)

    def _update_transfer_progress(self, progress: float, current: int, total: int):
        self.progress_bar.set(progress)
        self.progress_label.configure(text=f"Transferring... {current}/{total} items")

    def _transfer_complete(self):
        self.transfer_btn.configure(state="normal", text="📥 Transfer Selected to PC")
        self.progress_bar.set(1.0)
        self.progress_label.configure(
            text=f"✅ Transfer complete! Files saved to: {os.path.basename(self._destination)}"
        )

    def _change_destination(self):
        path = filedialog.askdirectory(title="Choose save location")
        if path:
            self._destination = path
            if self._server:
                self._server.destination_path = path
            self.dest_btn.configure(text=f"📂 {os.path.basename(path)}")

    def on_closing(self):
        if self._server:
            self._server.shutdown()
        self.destroy()


def main():
    app = DashboardApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
