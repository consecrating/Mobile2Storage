"""
Mobile2Storage - Simplified Dashboard.
ZERO SETUP. Maximum speed.

How it works:
1. Open app → QR code appears
2. Scan with phone → File picker opens
3. Pick files, tap Send → Files fly to PC at max WiFi speed

That's it. No ADB, no developer options, no IP addresses.
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


class DashboardApp(ctk.CTk):
    """
    Simple, fast dashboard.
    Shows QR code → receives files → shows progress.
    """

    def __init__(self):
        super().__init__()

        self.title("Mobile2Storage ⚡")
        self.geometry("750x650")
        self.minsize(650, 550)
        self.configure(fg_color=DARK_BG)

        # State
        self._server: Optional[ReceiverServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._destination = os.path.join(os.path.expanduser("~"), "Desktop", "Mobile2Storage")
        self._server_url = ""
        self._file_widgets: List[ctk.CTkFrame] = []

        # Build UI
        self._build_ui()

        # Auto-start server
        self.after(500, self._start_server)

    def _build_ui(self):
        """Build the simplified UI."""
        # === HEADER ===
        header = ctk.CTkFrame(self, height=50, fg_color=CARD_BG, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="⚡ Mobile2Storage",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left", padx=15, pady=10)

        ctk.CTkLabel(
            header, text="Speedy Transfer • Phone → PC",
            font=ctk.CTkFont(size=11), text_color=TEXT_SECONDARY
        ).pack(side="left", padx=5)

        # Destination button
        self.dest_btn = ctk.CTkButton(
            header, text=f"📂 {os.path.basename(self._destination)}",
            command=self._change_destination,
            width=140, height=30, corner_radius=8,
            font=ctk.CTkFont(size=11)
        )
        self.dest_btn.pack(side="right", padx=15, pady=10)

        # === MAIN CONTENT ===
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=15)

        # === TOP SECTION: QR Code + Instructions ===
        self.top_section = ctk.CTkFrame(self.main_frame, fg_color=CARD_BG, corner_radius=16)
        self.top_section.pack(fill="x", pady=(0, 12))

        top_content = ctk.CTkFrame(self.top_section, fg_color="transparent")
        top_content.pack(fill="x", padx=20, pady=20)

        # Left: QR code
        self.qr_frame = ctk.CTkFrame(top_content, fg_color="transparent", width=200)
        self.qr_frame.pack(side="left", padx=(0, 25))

        self.qr_label = ctk.CTkLabel(
            self.qr_frame, text="Starting...",
            font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY
        )
        self.qr_label.pack()

        # Right: Instructions
        instructions = ctk.CTkFrame(top_content, fg_color="transparent")
        instructions.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            instructions, text="3 Steps. That's it.",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 12))

        steps = [
            ("1️⃣", "Scan the QR code with your phone camera"),
            ("2️⃣", "Select files you want to transfer"),
            ("3️⃣", "Tap Send → Files arrive on your PC"),
        ]
        for icon, text in steps:
            step_frame = ctk.CTkFrame(instructions, fg_color="transparent")
            step_frame.pack(fill="x", pady=3)
            ctk.CTkLabel(
                step_frame, text=f"{icon}  {text}",
                font=ctk.CTkFont(size=14), anchor="w"
            ).pack(fill="x")

        # Speed note
        ctk.CTkLabel(
            instructions,
            text="⚡ Transfers at your full WiFi speed (no USB needed)",
            font=ctk.CTkFont(size=11), text_color=ACCENT_GREEN, anchor="w"
        ).pack(fill="x", pady=(12, 0))

        # URL display (for manual entry if QR doesn't work)
        self.url_frame = ctk.CTkFrame(self.top_section, fg_color="#0d1a26", corner_radius=8)
        self.url_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.url_label = ctk.CTkLabel(
            self.url_frame, text="Starting server...",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=ACCENT_BLUE
        )
        self.url_label.pack(pady=8)

        # === BOTTOM SECTION: Transfer Progress ===
        self.progress_section = ctk.CTkFrame(self.main_frame, fg_color=CARD_BG, corner_radius=16)
        self.progress_section.pack(fill="both", expand=True)

        # Progress header
        prog_header = ctk.CTkFrame(self.progress_section, fg_color="transparent")
        prog_header.pack(fill="x", padx=16, pady=(12, 5))

        ctk.CTkLabel(
            prog_header, text="📥 Received Files",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        self.stats_label = ctk.CTkLabel(
            prog_header, text="Waiting for files...",
            font=ctk.CTkFont(size=11), text_color=TEXT_SECONDARY
        )
        self.stats_label.pack(side="right")

        # Overall progress bar (hidden until transfer starts)
        self.overall_frame = ctk.CTkFrame(self.progress_section, fg_color="transparent")
        self.overall_frame.pack(fill="x", padx=16, pady=4)

        self.speed_label = ctk.CTkLabel(
            self.overall_frame, text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=ACCENT_BLUE
        )
        self.speed_label.pack(anchor="w")

        # File list (scrollable)
        self.file_list = ctk.CTkScrollableFrame(
            self.progress_section, fg_color="transparent",
            scrollbar_button_color=TEXT_DIM
        )
        self.file_list.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Placeholder text
        self.placeholder = ctk.CTkLabel(
            self.file_list,
            text="📱 Files will appear here as they arrive\nfrom your phone",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_DIM
        )
        self.placeholder.pack(pady=30)

        # === FOOTER ===
        footer = ctk.CTkFrame(self, height=28, fg_color=CARD_BG, corner_radius=0)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        self.footer_text = ctk.CTkLabel(
            footer, text="",
            font=ctk.CTkFont(size=10), text_color=TEXT_SECONDARY
        )
        self.footer_text.pack(side="left", padx=12, pady=5)

    def _start_server(self):
        """Start the receiver server."""
        try:
            ip = get_local_ip()
            port = find_free_port()
            self._server_url = f"http://{ip}:{port}"

            # Ensure destination exists
            os.makedirs(self._destination, exist_ok=True)

            # Create server
            self._server = ReceiverServer(
                port=port,
                destination=self._destination,
                mobile_html=MOBILE_PAGE_HTML,
                progress_callback=self._on_progress
            )

            # Start server thread
            self._server_thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True
            )
            self._server_thread.start()

            # Update UI with QR code
            self._show_qr_code()
            self.url_label.configure(text=f"📎 Or open:  {self._server_url}")
            self.footer_text.configure(
                text=f"Server running on {ip}:{port} • Saving to: {self._destination}"
            )

        except Exception as e:
            self.qr_label.configure(text=f"Error: {e}", text_color=ACCENT_RED)
            self.footer_text.configure(text=f"Failed to start server: {e}")

    def _show_qr_code(self):
        """Display QR code for the server URL."""
        qr_image = generate_qr_for_tkinter(self._server_url, size=180)

        if qr_image:
            self.qr_label.configure(image=qr_image, text="")
            self.qr_label._image = qr_image  # Keep reference
        else:
            # Fallback: show URL prominently if qrcode lib not installed
            self.qr_label.configure(
                text=f"📱 Open on phone:\n\n{self._server_url}\n\n"
                     f"(Install 'qrcode' package\nfor QR code display)",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=ACCENT_BLUE,
                justify="center"
            )

    def _on_progress(self, stats: ServerStats):
        """Handle progress updates from server (called from server thread)."""
        try:
            self.after(0, lambda: self._update_progress(stats))
        except Exception:
            pass

    def _update_progress(self, stats: ServerStats):
        """Update UI with current transfer progress."""
        # Remove placeholder on first file
        if stats.total_files_received > 0 or stats.active_transfers > 0:
            self.placeholder.pack_forget()

        # Update stats label
        if stats.active_transfers > 0:
            self.stats_label.configure(
                text=f"⚡ {stats.active_transfers} active • "
                     f"{stats.total_files_received} complete • "
                     f"{format_size(stats.total_bytes_received)} received"
            )
        elif stats.total_files_received > 0:
            self.stats_label.configure(
                text=f"✅ {stats.total_files_received} files • "
                     f"{format_size(stats.total_bytes_received)} total"
            )

        # Update speed
        active_speed = sum(f.speed for f in stats.files if f.status == "receiving")
        if active_speed > 0:
            self.speed_label.configure(text=f"⚡ {format_speed(active_speed)}")
        else:
            self.speed_label.configure(text="")

        # Update file list
        self._update_file_list(stats.files)

    def _update_file_list(self, files: List[FileTransfer]):
        """Update the file list display."""
        # Clear old widgets
        for w in self._file_widgets:
            w.destroy()
        self._file_widgets.clear()

        # Show files (most recent first)
        display_files = list(reversed(files[-30:]))  # Last 30 files

        for transfer in display_files:
            frame = ctk.CTkFrame(
                self.file_list, height=40, corner_radius=8,
                fg_color="#1c2128" if transfer.status == "complete" else "#0d2233"
            )
            frame.pack(fill="x", pady=2)
            frame.pack_propagate(False)

            # Status icon
            if transfer.status == "complete":
                icon = "✅"
                color = ACCENT_GREEN
            elif transfer.status == "receiving":
                icon = "📤"
                color = ACCENT_BLUE
            else:
                icon = "❌"
                color = ACCENT_RED

            ctk.CTkLabel(
                frame, text=icon, width=28,
                font=ctk.CTkFont(size=14)
            ).pack(side="left", padx=6)

            # File info
            info = ctk.CTkFrame(frame, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True, padx=4)

            name = transfer.filename
            if len(name) > 40:
                name = name[:37] + "..."

            ctk.CTkLabel(
                info, text=name,
                font=ctk.CTkFont(size=11), anchor="w",
                text_color=TEXT_PRIMARY
            ).pack(fill="x", side="top")

            # Progress bar for active transfers
            if transfer.status == "receiving" and transfer.total_size > 0:
                progress = transfer.received_size / transfer.total_size
                bar = ctk.CTkProgressBar(info, height=4, corner_radius=2)
                bar.pack(fill="x", side="bottom", pady=(0, 3))
                bar.set(progress)

            # Size + speed
            if transfer.status == "receiving":
                pct = int(transfer.received_size / max(1, transfer.total_size) * 100)
                right_text = f"{pct}% • {format_speed(transfer.speed)}"
            else:
                right_text = format_size(transfer.received_size)

            ctk.CTkLabel(
                frame, text=right_text,
                font=ctk.CTkFont(size=10), text_color=color,
                width=120
            ).pack(side="right", padx=8)

            self._file_widgets.append(frame)

    def _change_destination(self):
        """Change save destination folder."""
        path = filedialog.askdirectory(title="Choose where to save files")
        if path:
            self._destination = path
            if self._server:
                self._server.destination_path = path
            self.dest_btn.configure(text=f"📂 {os.path.basename(path)}")
            self.footer_text.configure(
                text=f"Server running • Saving to: {path}"
            )

    def on_closing(self):
        """Handle window close."""
        if self._server:
            self._server.shutdown()
        self.destroy()


def main():
    """Entry point."""
    app = DashboardApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
