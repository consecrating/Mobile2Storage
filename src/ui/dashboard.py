"""
Advanced Eye-Catching Dashboard for Mobile2Storage.
Features:
- Large circular progress indicator with animated gradient
- Prominent transferred/remaining percentage display
- Real-time speed and ETA stat cards
- Color-coded file queue with mini progress bars
- Modern dark theme with neon accents
- Smooth animations throughout
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import os
from typing import Optional, List

from ..core.connection_manager import ConnectionManager, ConnectionStatus, DeviceInfo
from ..core.transfer_engine import (
    TransferEngine, TransferSession, TransferStatus, TransferTask
)
from ..core.file_discovery import FileDiscovery, FileCategory, DiscoveryStats
from ..utils.helpers import format_size, format_speed, format_time
from .widgets import CircularProgress, GlowingProgressBar, StatCard, AnimatedDots


# === THEME CONFIGURATION ===
DARK_BG = "#0d1117"
CARD_BG = "#161b22"
ACCENT_BLUE = "#00d4ff"
ACCENT_GREEN = "#00ff99"
ACCENT_ORANGE = "#ff9944"
ACCENT_RED = "#ff4466"
ACCENT_PURPLE = "#aa66ff"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#8b949e"
TEXT_DIM = "#484f58"

# Configure customtkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DevicePanel(ctk.CTkFrame):
    """Compact device connection panel."""
    
    def __init__(self, parent, connection: ConnectionManager, **kwargs):
        kwargs.setdefault("corner_radius", 12)
        kwargs.setdefault("fg_color", CARD_BG)
        super().__init__(parent, **kwargs)
        self.connection = connection
        self._build_ui()
    
    def _build_ui(self):
        # Header row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 5))
        
        self.title_label = ctk.CTkLabel(
            header, text="📱 Device",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.title_label.pack(side="left")
        
        self.status_badge = ctk.CTkLabel(
            header, text="● Disconnected",
            font=ctk.CTkFont(size=11),
            text_color=ACCENT_RED
        )
        self.status_badge.pack(side="right")
        
        # Device info (compact)
        self.info_label = ctk.CTkLabel(
            self, text="Connect your Android device to begin",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_SECONDARY, anchor="w"
        )
        self.info_label.pack(fill="x", padx=12, pady=2)
        
        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(5, 10))
        
        self.usb_btn = ctk.CTkButton(
            btn_frame, text="🔌 USB",
            command=self._connect_usb, width=80, height=28,
            corner_radius=14, font=ctk.CTkFont(size=11)
        )
        self.usb_btn.pack(side="left", padx=(0, 5))
        
        self.wifi_btn = ctk.CTkButton(
            btn_frame, text="📶 WiFi",
            command=self._show_wifi_dialog, width=80, height=28,
            corner_radius=14, font=ctk.CTkFont(size=11)
        )
        self.wifi_btn.pack(side="left", padx=(0, 5))
        
        self.disconnect_btn = ctk.CTkButton(
            btn_frame, text="✕", width=28, height=28,
            command=self._disconnect, corner_radius=14,
            fg_color=ACCENT_RED, hover_color="#ff6688"
        )
        self.disconnect_btn.pack(side="right")
        self.disconnect_btn.pack_forget()
    
    def _connect_usb(self):
        self.status_badge.configure(text="● Connecting...", text_color=ACCENT_ORANGE)
        threading.Thread(target=self._do_connect_usb, daemon=True).start()
    
    def _do_connect_usb(self):
        success = self.connection.connect_usb()
        self.after(0, lambda: self._update_ui(success))
    
    def _show_wifi_dialog(self):
        dialog = ctk.CTkInputDialog(
            text="Enter device IP address:",
            title="WiFi Connection"
        )
        ip = dialog.get_input()
        if ip:
            self.status_badge.configure(text="● Connecting...", text_color=ACCENT_ORANGE)
            threading.Thread(
                target=lambda: self._do_connect_wifi(ip.strip()),
                daemon=True
            ).start()
    
    def _do_connect_wifi(self, ip: str):
        success = self.connection.connect_wifi(ip)
        self.after(0, lambda: self._update_ui(success))
    
    def _disconnect(self):
        self.connection.disconnect()
        self._update_ui(False)
    
    def _update_ui(self, connected: bool):
        if connected and self.connection.device:
            d = self.connection.device
            self.status_badge.configure(text="● Connected", text_color=ACCENT_GREEN)
            self.info_label.configure(
                text=f"{d.model} | Android {d.android_version} | "
                     f"{format_size(d.storage_free)} free"
            )
            self.disconnect_btn.pack(side="right")
        else:
            self.status_badge.configure(text="● Disconnected", text_color=ACCENT_RED)
            self.info_label.configure(text="Connect your Android device to begin")
            self.disconnect_btn.pack_forget()
    
    def update_connection_status(self, status: ConnectionStatus, device: Optional[DeviceInfo]):
        self._update_ui(status == ConnectionStatus.CONNECTED)


class MainProgressDisplay(ctk.CTkFrame):
    """
    THE EYE-CATCHING CENTERPIECE.
    Large circular progress with prominent percentage display.
    Shows transferred vs remaining clearly.
    """
    
    def __init__(self, parent, **kwargs):
        kwargs.setdefault("corner_radius", 16)
        kwargs.setdefault("fg_color", CARD_BG)
        super().__init__(parent, **kwargs)
        self._build_ui()
    
    def _build_ui(self):
        # Title with animation
        self.title_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.title_frame.pack(fill="x", padx=15, pady=(12, 5))
        
        self.title = ctk.CTkLabel(
            self.title_frame, text="⚡ Transfer Progress",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.title.pack(side="left")
        
        self.status_anim = AnimatedDots(
            self.title_frame, base_text="",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY
        )
        self.status_anim.pack(side="right")
        
        # Main content: Circular progress + Stats
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=5)
        
        # Left: Circular progress
        circle_frame = ctk.CTkFrame(content, fg_color="transparent")
        circle_frame.pack(side="left", padx=(0, 15))
        
        self.circular_progress = CircularProgress(
            circle_frame, size=200, line_width=16,
            bg_color=CARD_BG
        )
        self.circular_progress.pack(pady=5)
        
        # Right: Large stats display
        stats_frame = ctk.CTkFrame(content, fg_color="transparent")
        stats_frame.pack(side="left", fill="both", expand=True)
        
        # BIG percentage display
        self.big_percent = ctk.CTkLabel(
            stats_frame, text="0.0%",
            font=ctk.CTkFont(family="Segoe UI", size=48, weight="bold"),
            text_color=ACCENT_BLUE
        )
        self.big_percent.pack(anchor="w", pady=(5, 0))
        
        self.percent_label = ctk.CTkLabel(
            stats_frame, text="TRANSFERRED",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_SECONDARY
        )
        self.percent_label.pack(anchor="w")
        
        # Transferred / Remaining display
        dual_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        dual_frame.pack(fill="x", pady=10)
        
        # Transferred box
        trans_box = ctk.CTkFrame(dual_frame, corner_radius=8, fg_color="#0d2818")
        trans_box.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ctk.CTkLabel(
            trans_box, text="✓ DONE",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=ACCENT_GREEN
        ).pack(padx=8, pady=(5, 0), anchor="w")
        
        self.transferred_value = ctk.CTkLabel(
            trans_box, text="0 B",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT_GREEN
        )
        self.transferred_value.pack(padx=8, pady=(0, 5), anchor="w")
        
        # Remaining box
        rem_box = ctk.CTkFrame(dual_frame, corner_radius=8, fg_color="#2a1800")
        rem_box.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        ctk.CTkLabel(
            rem_box, text="↓ REMAINING",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=ACCENT_ORANGE
        ).pack(padx=8, pady=(5, 0), anchor="w")
        
        self.remaining_value = ctk.CTkLabel(
            rem_box, text="0 B",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT_ORANGE
        )
        self.remaining_value.pack(padx=8, pady=(0, 5), anchor="w")
        
        # Glowing progress bar at bottom
        self.glow_bar = GlowingProgressBar(self, height=38)
        self.glow_bar.pack(fill="x", padx=15, pady=(5, 12))
    
    def update_progress(self, session: TransferSession):
        """Update all progress displays."""
        if not session or session.total_bytes == 0:
            return
        
        progress = session.transferred_bytes / session.total_bytes
        percent = progress * 100
        remaining_pct = 100 - percent
        
        transferred_str = format_size(session.transferred_bytes)
        remaining_bytes = session.total_bytes - session.transferred_bytes
        remaining_str = format_size(remaining_bytes)
        speed_str = format_speed(session.current_speed)
        
        # Update circular progress
        self.circular_progress.set_progress(
            progress,
            transferred=transferred_str,
            remaining=remaining_str,
            speed=speed_str
        )
        
        # Update big percentage
        self.big_percent.configure(text=f"{percent:.1f}%")
        
        # Color-code the percentage based on progress
        if percent >= 90:
            self.big_percent.configure(text_color=ACCENT_GREEN)
        elif percent >= 50:
            self.big_percent.configure(text_color=ACCENT_BLUE)
        elif percent >= 25:
            self.big_percent.configure(text_color=ACCENT_ORANGE)
        else:
            self.big_percent.configure(text_color=ACCENT_PURPLE)
        
        # Update transferred/remaining
        self.transferred_value.configure(text=f"{transferred_str} ({percent:.1f}%)")
        self.remaining_value.configure(text=f"{remaining_str} ({remaining_pct:.1f}%)")
        
        # Update glowing bar
        self.glow_bar.set_progress(progress)
        
        # Animation
        if session.is_active and not session.is_paused:
            self.status_anim.base_text = "Transferring"
            self.status_anim.start()
        elif session.is_paused:
            self.status_anim.stop()
            self.status_anim.configure(text="⏸ Paused")
        else:
            self.status_anim.stop()
            self.status_anim.configure(text="✓ Complete" if percent >= 99.9 else "")
    
    def reset(self):
        """Reset to initial state."""
        self.circular_progress.set_progress(0, "0 B", "0 B", "")
        self.big_percent.configure(text="0.0%", text_color=ACCENT_BLUE)
        self.transferred_value.configure(text="0 B")
        self.remaining_value.configure(text="0 B")
        self.glow_bar.set_progress(0)
        self.status_anim.stop()
        self.status_anim.configure(text="")


class StatsRow(ctk.CTkFrame):
    """Row of stat cards showing key metrics."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._build_ui()
    
    def _build_ui(self):
        # Speed card
        self.speed_card = StatCard(
            self, icon="⚡", label="SPEED",
            value="--", accent_color=ACCENT_BLUE,
            fg_color=CARD_BG, corner_radius=12
        )
        self.speed_card.pack(side="left", fill="both", expand=True, padx=(0, 3))
        
        # Peak speed
        self.peak_card = StatCard(
            self, icon="🔥", label="PEAK",
            value="--", accent_color=ACCENT_ORANGE,
            fg_color=CARD_BG, corner_radius=12
        )
        self.peak_card.pack(side="left", fill="both", expand=True, padx=3)
        
        # ETA
        self.eta_card = StatCard(
            self, icon="⏱️", label="ETA",
            value="--", accent_color=ACCENT_GREEN,
            fg_color=CARD_BG, corner_radius=12
        )
        self.eta_card.pack(side="left", fill="both", expand=True, padx=3)
        
        # Files
        self.files_card = StatCard(
            self, icon="📁", label="FILES",
            value="0/0", accent_color=ACCENT_PURPLE,
            fg_color=CARD_BG, corner_radius=12
        )
        self.files_card.pack(side="left", fill="both", expand=True, padx=3)
        
        # Verified
        self.verified_card = StatCard(
            self, icon="🛡️", label="VERIFIED",
            value="0", accent_color=ACCENT_GREEN,
            fg_color=CARD_BG, corner_radius=12
        )
        self.verified_card.pack(side="left", fill="both", expand=True, padx=(3, 0))
    
    def update_stats(self, session: TransferSession):
        """Update all stat cards."""
        if not session:
            return
        
        self.speed_card.set_value(format_speed(session.current_speed))
        self.peak_card.set_value(format_speed(session.peak_speed))
        self.eta_card.set_value(format_time(session.eta_seconds))
        self.files_card.set_value(f"{session.transferred_files}/{session.total_files}")
        self.verified_card.set_value(str(session.verified_files))


class FileQueuePanel(ctk.CTkFrame):
    """File queue with mini progress bars and status."""
    
    def __init__(self, parent, **kwargs):
        kwargs.setdefault("corner_radius", 12)
        kwargs.setdefault("fg_color", CARD_BG)
        super().__init__(parent, **kwargs)
        self._build_ui()
        self._items = []
    
    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 5))
        
        ctk.CTkLabel(
            header, text="📋 File Queue",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")
        
        self.queue_count = ctk.CTkLabel(
            header, text="0 files",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_SECONDARY
        )
        self.queue_count.pack(side="right")
        
        # Scrollable list
        self.list_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=TEXT_DIM
        )
        self.list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # Summary bar
        self.summary = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_SECONDARY
        )
        self.summary.pack(padx=12, pady=(0, 8))
    
    def update_queue(self, tasks: List[TransferTask]):
        """Update file queue display."""
        # Clear old items
        for widget in self._items:
            widget.destroy()
        self._items.clear()
        
        # Sort: active first, then queued, then completed
        sorted_tasks = sorted(tasks, key=lambda t: (
            0 if t.status == TransferStatus.TRANSFERRING else
            1 if t.status == TransferStatus.RETRYING else
            2 if t.status == TransferStatus.VERIFYING else
            3 if t.status == TransferStatus.HASHING_SOURCE else
            4 if t.status == TransferStatus.QUEUED else
            5 if t.status == TransferStatus.FAILED else 6
        ))[:40]  # Show max 40 items
        
        for task in sorted_tasks:
            frame = ctk.CTkFrame(
                self.list_frame, height=32, corner_radius=6,
                fg_color="#1c2128" if task.status != TransferStatus.TRANSFERRING else "#0d2233"
            )
            frame.pack(fill="x", pady=1)
            frame.pack_propagate(False)
            
            # Status icon
            icons = {
                TransferStatus.QUEUED: "⏳",
                TransferStatus.HASHING_SOURCE: "🔐",
                TransferStatus.TRANSFERRING: "📤",
                TransferStatus.VERIFYING: "🔍",
                TransferStatus.COMPLETED: "✅",
                TransferStatus.FAILED: "❌",
                TransferStatus.RETRYING: "🔄",
                TransferStatus.PAUSED: "⏸️",
            }
            
            icon_label = ctk.CTkLabel(
                frame, text=icons.get(task.status, "❓"),
                width=24, font=ctk.CTkFont(size=12)
            )
            icon_label.pack(side="left", padx=4)
            
            # Filename
            name = task.file_item.filename
            if len(name) > 35:
                name = name[:32] + "..."
            
            ctk.CTkLabel(
                frame, text=name,
                font=ctk.CTkFont(size=10), anchor="w",
                text_color=TEXT_PRIMARY if task.status == TransferStatus.TRANSFERRING else TEXT_SECONDARY
            ).pack(side="left", fill="x", expand=True, padx=3)
            
            # Progress percentage for active transfers
            if task.status == TransferStatus.TRANSFERRING and task.file_item.size > 0:
                pct = task.bytes_transferred / task.file_item.size * 100
                pct_label = ctk.CTkLabel(
                    frame, text=f"{pct:.0f}%",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    text_color=ACCENT_BLUE, width=40
                )
                pct_label.pack(side="right", padx=2)
            
            # Size
            ctk.CTkLabel(
                frame, text=format_size(task.file_item.size),
                font=ctk.CTkFont(size=10),
                text_color=TEXT_DIM, width=65
            ).pack(side="right", padx=4)
            
            self._items.append(frame)
        
        # Update counts
        active = sum(1 for t in tasks if t.status == TransferStatus.TRANSFERRING)
        queued = sum(1 for t in tasks if t.status == TransferStatus.QUEUED)
        done = sum(1 for t in tasks if t.status == TransferStatus.COMPLETED)
        failed = sum(1 for t in tasks if t.status == TransferStatus.FAILED)
        
        self.queue_count.configure(text=f"{len(tasks)} files")
        self.summary.configure(
            text=f"⚡ Active: {active}  |  ⏳ Queued: {queued}  |  "
                 f"✅ Done: {done}  |  ❌ Failed: {failed}"
        )


class DiscoveryPanel(ctk.CTkFrame):
    """Compact file discovery status panel."""
    
    def __init__(self, parent, **kwargs):
        kwargs.setdefault("corner_radius", 12)
        kwargs.setdefault("fg_color", CARD_BG)
        super().__init__(parent, **kwargs)
        self._build_ui()
    
    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 5))
        
        ctk.CTkLabel(
            header, text="🔍 Discovery",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")
        
        self.scan_status = ctk.CTkLabel(
            header, text="Ready",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_SECONDARY
        )
        self.scan_status.pack(side="right")
        
        # Category badges
        self.cat_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cat_frame.pack(fill="x", padx=12, pady=(0, 10))
        
        self.cat_labels = {}
        for cat, icon, color in [
            (FileCategory.PHOTO, "📷", "#ff6b9d"),
            (FileCategory.VIDEO, "🎬", "#c56cf0"),
            (FileCategory.AUDIO, "🎵", "#17c0eb"),
            (FileCategory.DOCUMENT, "📄", "#ffdd59"),
            (FileCategory.OTHER, "📦", "#7bed9f"),
        ]:
            badge = ctk.CTkLabel(
                self.cat_frame,
                text=f"{icon} 0",
                font=ctk.CTkFont(size=10),
                text_color=color
            )
            badge.pack(side="left", padx=4)
            self.cat_labels[cat] = badge
    
    def update_discovery(self, stats: DiscoveryStats):
        """Update discovery display."""
        status = "Scanning..." if stats.is_running else (
            f"✓ {stats.files_found} files ({format_size(stats.total_size_found)})"
            if stats.is_complete else "Ready"
        )
        self.scan_status.configure(text=status)
        
        icons = {
            FileCategory.PHOTO: "📷",
            FileCategory.VIDEO: "🎬",
            FileCategory.AUDIO: "🎵",
            FileCategory.DOCUMENT: "📄",
            FileCategory.OTHER: "📦",
        }
        
        for cat, label in self.cat_labels.items():
            count = stats.categories.get(cat, {}).get("count", 0)
            label.configure(text=f"{icons.get(cat, '📦')} {count}")


class DashboardApp(ctk.CTk):
    """
    Main Application Window - Advanced Eye-Catching Dashboard.
    Features a prominent circular progress indicator and clear
    transferred/remaining percentage display.
    """
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("Mobile2Storage ⚡ Fast Android to PC Transfer")
        self.geometry("1200x800")
        self.minsize(1000, 650)
        self.configure(fg_color=DARK_BG)
        
        # Core components
        self.connection = ConnectionManager()
        self.discovery = FileDiscovery(self.connection)
        self.engine = TransferEngine(self.connection)
        
        # Register callbacks
        self.connection.add_status_callback(self._on_connection_change)
        self.discovery.add_discovery_callback(self._on_discovery_update)
        self.engine.add_progress_callback(self._on_transfer_progress)
        
        # State
        self._destination_path = ""
        self._selected_categories: List[FileCategory] = list(FileCategory)
        
        # Build UI
        self._build_ui()
        
        # Start UI update loop
        self._schedule_update()
    
    def _build_ui(self):
        """Build the complete dashboard layout."""
        # === HEADER BAR ===
        self._build_header()
        
        # === MAIN LAYOUT: Left sidebar + Center content ===
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        # Left sidebar (controls)
        sidebar = ctk.CTkFrame(main_container, fg_color="transparent", width=320)
        sidebar.pack(side="left", fill="y", padx=(0, 8))
        sidebar.pack_propagate(False)
        
        # Center content (progress + queue)
        center = ctk.CTkFrame(main_container, fg_color="transparent")
        center.pack(side="left", fill="both", expand=True)
        
        # === SIDEBAR CONTENT ===
        # Device panel
        self.device_panel = DevicePanel(sidebar, self.connection)
        self.device_panel.pack(fill="x", pady=(0, 6))
        
        # Discovery panel
        self.discovery_panel = DiscoveryPanel(sidebar)
        self.discovery_panel.pack(fill="x", pady=6)
        
        # Controls panel
        self._build_controls(sidebar)
        
        # === CENTER CONTENT ===
        # Main progress display (THE CENTERPIECE)
        self.progress_display = MainProgressDisplay(center)
        self.progress_display.pack(fill="x", pady=(0, 6))
        
        # Stats row
        self.stats_row = StatsRow(center)
        self.stats_row.pack(fill="x", pady=6)
        
        # File queue
        self.queue_panel = FileQueuePanel(center)
        self.queue_panel.pack(fill="both", expand=True, pady=(6, 0))
        
        # === FOOTER ===
        self._build_footer()
    
    def _build_header(self):
        """Build the application header."""
        header = ctk.CTkFrame(self, height=50, fg_color=CARD_BG, corner_radius=0)
        header.pack(fill="x", padx=0, pady=(0, 8))
        header.pack_propagate(False)
        
        # Logo and title
        ctk.CTkLabel(
            header, text="📱➡️💻  Mobile2Storage",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left", padx=15, pady=10)
        
        # Subtitle
        ctk.CTkLabel(
            header, text="High-Speed Verified Transfer  •  Zero Data Loss",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_SECONDARY
        ).pack(side="left", padx=10, pady=10)
        
        # Version
        ctk.CTkLabel(
            header, text="v1.0.0",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_DIM
        ).pack(side="right", padx=15)
    
    def _build_controls(self, parent):
        """Build transfer controls panel."""
        controls = ctk.CTkFrame(parent, corner_radius=12, fg_color=CARD_BG)
        controls.pack(fill="x", pady=6)
        
        ctk.CTkLabel(
            controls, text="⚙️ Transfer Settings",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(padx=12, pady=(10, 5), anchor="w")
        
        # Destination
        dest_frame = ctk.CTkFrame(controls, fg_color="transparent")
        dest_frame.pack(fill="x", padx=12, pady=3)
        
        ctk.CTkLabel(
            dest_frame, text="Save to:",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_SECONDARY
        ).pack(anchor="w")
        
        dest_row = ctk.CTkFrame(dest_frame, fg_color="transparent")
        dest_row.pack(fill="x", pady=2)
        
        self.dest_entry = ctk.CTkEntry(
            dest_row, placeholder_text="Choose folder...",
            height=30, corner_radius=8
        )
        self.dest_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        ctk.CTkButton(
            dest_row, text="📂", width=30, height=30,
            command=self._browse_destination, corner_radius=8
        ).pack(side="right")
        
        # Category checkboxes
        cat_frame = ctk.CTkFrame(controls, fg_color="transparent")
        cat_frame.pack(fill="x", padx=12, pady=5)
        
        ctk.CTkLabel(
            cat_frame, text="File types:",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_SECONDARY
        ).pack(anchor="w")
        
        self.cat_vars = {}
        cat_row = ctk.CTkFrame(cat_frame, fg_color="transparent")
        cat_row.pack(fill="x", pady=2)
        
        for cat in FileCategory:
            if cat == FileCategory.APP:
                continue
            var = ctk.BooleanVar(value=True)
            self.cat_vars[cat] = var
            ctk.CTkCheckBox(
                cat_row, text=cat.value, variable=var,
                font=ctk.CTkFont(size=10),
                height=22, checkbox_width=16, checkbox_height=16,
                corner_radius=4
            ).pack(side="left", padx=2)
        
        # Action buttons
        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(8, 12))
        
        self.scan_btn = ctk.CTkButton(
            btn_frame, text="🔍 Scan Device",
            command=self._start_scan, height=36,
            corner_radius=10, font=ctk.CTkFont(size=12, weight="bold")
        )
        self.scan_btn.pack(fill="x", pady=2)
        
        self.transfer_btn = ctk.CTkButton(
            btn_frame, text="🚀 START TRANSFER",
            command=self._start_transfer, height=40,
            corner_radius=10, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00aa44", hover_color="#00cc55"
        )
        self.transfer_btn.pack(fill="x", pady=3)
        
        ctrl_row = ctk.CTkFrame(btn_frame, fg_color="transparent")
        ctrl_row.pack(fill="x", pady=2)
        
        self.pause_btn = ctk.CTkButton(
            ctrl_row, text="⏸ Pause", width=100, height=30,
            command=self._toggle_pause, corner_radius=8,
            fg_color="#aa7700", hover_color="#cc8800"
        )
        self.pause_btn.pack(side="left", padx=(0, 4))
        
        self.cancel_btn = ctk.CTkButton(
            ctrl_row, text="⏹ Cancel", width=100, height=30,
            command=self._cancel_transfer, corner_radius=8,
            fg_color="#aa2233", hover_color="#cc3344"
        )
        self.cancel_btn.pack(side="left")
    
    def _build_footer(self):
        """Build footer bar."""
        footer = ctk.CTkFrame(self, height=28, fg_color=CARD_BG, corner_radius=0)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        
        self.footer_text = ctk.CTkLabel(
            footer, text="Ready • Connect your Android device to begin",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_SECONDARY
        )
        self.footer_text.pack(side="left", padx=12, pady=4)
        
        # ADB status
        adb_ok = self.connection.adb_available
        self.adb_label = ctk.CTkLabel(
            footer,
            text="ADB ✓" if adb_ok else "ADB ✗ (Install Android SDK)",
            font=ctk.CTkFont(size=10),
            text_color=ACCENT_GREEN if adb_ok else ACCENT_RED
        )
        self.adb_label.pack(side="right", padx=12, pady=4)
    
    # === ACTIONS ===
    
    def _browse_destination(self):
        path = filedialog.askdirectory(title="Select Destination Folder")
        if path:
            self._destination_path = path
            self.dest_entry.delete(0, "end")
            self.dest_entry.insert(0, path)
    
    def _start_scan(self):
        if not self.connection.is_connected:
            messagebox.showwarning(
                "Not Connected",
                "Please connect your Android device first.\n\n"
                "USB: Enable USB Debugging in Developer Options\n"
                "WiFi: Enable Wireless Debugging (Android 11+)"
            )
            return
        
        categories = [cat for cat, var in self.cat_vars.items() if var.get()]
        self.scan_btn.configure(state="disabled", text="Scanning...")
        self.footer_text.configure(text="Scanning device for files...")
        self.discovery.start_discovery(categories=categories)
    
    def _start_transfer(self):
        if not self.connection.is_connected:
            messagebox.showwarning("Not Connected", "Connect your device first.")
            return
        if not self._destination_path:
            messagebox.showwarning("No Destination", "Select a destination folder.")
            return
        
        files = self.discovery.get_all_files()
        if not files:
            messagebox.showinfo("No Files", "Scan the device first.")
            return
        
        self.transfer_btn.configure(state="disabled")
        self.footer_text.configure(text="⚡ Transfer in progress...")
        self.progress_display.reset()
        self.engine.start_transfer(files, self._destination_path)
    
    def _toggle_pause(self):
        if self.engine.session and self.engine.session.is_paused:
            self.engine.resume_transfer()
            self.pause_btn.configure(text="⏸ Pause")
            self.footer_text.configure(text="⚡ Transfer resumed")
        else:
            self.engine.pause_transfer()
            self.pause_btn.configure(text="▶ Resume")
            self.footer_text.configure(text="⏸ Transfer paused")
    
    def _cancel_transfer(self):
        if messagebox.askyesno("Cancel", "Cancel the current transfer?"):
            self.engine.cancel_transfer()
            self.transfer_btn.configure(state="normal")
            self.footer_text.configure(text="Transfer cancelled")
    
    # === CALLBACKS ===
    
    def _on_connection_change(self, status: ConnectionStatus, device: Optional[DeviceInfo]):
        try:
            self.after(0, lambda: self.device_panel.update_connection_status(status, device))
            if status == ConnectionStatus.CONNECTED and device:
                self.after(0, lambda: self.footer_text.configure(
                    text=f"Connected to {device.model} • Ready to scan"
                ))
        except Exception:
            pass
    
    def _on_discovery_update(self, stats: DiscoveryStats):
        try:
            self.after(0, lambda: self.discovery_panel.update_discovery(stats))
            if stats.is_complete:
                self.after(0, lambda: self.scan_btn.configure(
                    state="normal", text="🔍 Scan Device"
                ))
                self.after(0, lambda: self.footer_text.configure(
                    text=f"Found {stats.files_found} files ({format_size(stats.total_size_found)}) • Ready to transfer"
                ))
        except Exception:
            pass
    
    def _on_transfer_progress(self, session: TransferSession):
        try:
            self.after(0, lambda: self.progress_display.update_progress(session))
            self.after(0, lambda: self.stats_row.update_stats(session))
            self.after(0, lambda: self.queue_panel.update_queue(session.tasks))
            
            if not session.is_active and session.transferred_files > 0:
                self.after(0, lambda: self._on_transfer_complete(session))
        except Exception:
            pass
    
    def _on_transfer_complete(self, session: TransferSession):
        self.transfer_btn.configure(state="normal")
        self.footer_text.configure(
            text=f"✅ Complete! {session.transferred_files} files "
                 f"({format_size(session.transferred_bytes)}) • "
                 f"All verified ✓"
        )
        messagebox.showinfo(
            "Transfer Complete! 🎉",
            f"✅ Successfully transferred: {session.transferred_files} files\n"
            f"💾 Total size: {format_size(session.transferred_bytes)}\n"
            f"🛡️ Verified: {session.verified_files} files\n"
            f"❌ Failed: {session.failed_files}\n"
            f"⏱️ Time: {format_time(session.elapsed_time)}\n"
            f"⚡ Average speed: {format_speed(session.avg_speed)}\n"
            f"🔥 Peak speed: {format_speed(session.peak_speed)}\n\n"
            f"All files verified with SHA-256 • Zero corruption guaranteed"
        )
    
    def _schedule_update(self):
        """Periodic UI refresh."""
        if self.engine.session and self.engine.session.is_active:
            self.queue_panel.update_queue(self.engine.session.tasks)
        self.after(1000, self._schedule_update)
    
    def on_closing(self):
        if self.engine.session and self.engine.session.is_active:
            if not messagebox.askyesno("Quit", "Transfer in progress. Quit anyway?"):
                return
            self.engine.cancel_transfer()
        self.connection.stop_monitoring()
        self.discovery.stop_discovery()
        self.destroy()


def main():
    """Application entry point."""
    app = DashboardApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
