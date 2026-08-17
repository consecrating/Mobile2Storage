"""
Custom Eye-Catching Widgets for Mobile2Storage Dashboard.
Includes animated circular progress, gradient bars, and glowing indicators.
"""

import customtkinter as ctk
import tkinter as tk
import math
from typing import Optional, Tuple


class CircularProgress(ctk.CTkCanvas):
    """
    Large, eye-catching circular progress indicator.
    Shows percentage in the center with animated gradient arc.
    Displays both transferred and remaining clearly.
    """
    
    def __init__(self, parent, size: int = 220, line_width: int = 18,
                 bg_color: str = "#1a1a2e", progress_color: str = "#00d4ff",
                 remaining_color: str = "#2a2a4a", **kwargs):
        super().__init__(parent, width=size, height=size,
                        bg=bg_color, highlightthickness=0, **kwargs)
        
        self.size = size
        self.line_width = line_width
        self.bg_color = bg_color
        self.progress_color = progress_color
        self.remaining_color = remaining_color
        self._progress = 0.0
        self._transferred_text = "0 B"
        self._remaining_text = "0 B"
        self._speed_text = ""
        self._animate_target = 0.0
        self._animation_id = None
        
        # Gradient colors for the progress arc
        self._gradient_colors = [
            "#00d4ff", "#00e5ff", "#00f0ff", "#00ffcc",
            "#00ff99", "#33ff77", "#66ff55", "#99ff33"
        ]
        
        self._draw()
    
    def _draw(self):
        """Draw the circular progress indicator."""
        self.delete("all")
        
        padding = self.line_width + 5
        x0, y0 = padding, padding
        x1, y1 = self.size - padding, self.size - padding
        center = self.size / 2
        
        # Background circle (remaining)
        self.create_arc(
            x0, y0, x1, y1, start=90, extent=-360,
            outline=self.remaining_color, width=self.line_width,
            style="arc"
        )
        
        # Progress arc with gradient effect
        if self._progress > 0:
            extent = -360 * self._progress
            
            # Draw multiple thin arcs for gradient effect
            segments = max(1, int(abs(extent) / 3))
            for i in range(segments):
                seg_start = 90 + (extent * i / segments)
                seg_extent = extent / segments
                
                # Pick color from gradient
                color_idx = int(i / segments * (len(self._gradient_colors) - 1))
                color = self._gradient_colors[min(color_idx, len(self._gradient_colors) - 1)]
                
                self.create_arc(
                    x0, y0, x1, y1,
                    start=seg_start, extent=seg_extent,
                    outline=color, width=self.line_width,
                    style="arc"
                )
            
            # Glow effect (outer ring)
            glow_padding = padding - 4
            self.create_arc(
                glow_padding, glow_padding,
                self.size - glow_padding, self.size - glow_padding,
                start=90, extent=extent,
                outline=self._gradient_colors[0], width=2,
                style="arc"
            )
        
        # Center percentage text
        percent = self._progress * 100
        
        # Large percentage
        self.create_text(
            center, center - 20,
            text=f"{percent:.1f}%",
            fill="#ffffff", font=("Segoe UI", 28, "bold"),
            anchor="center"
        )
        
        # "Transferred" label
        self.create_text(
            center, center + 12,
            text=f"✓ {self._transferred_text}",
            fill="#00ff99", font=("Segoe UI", 10, "bold"),
            anchor="center"
        )
        
        # "Remaining" label
        self.create_text(
            center, center + 32,
            text=f"↓ {self._remaining_text} left",
            fill="#ff9944", font=("Segoe UI", 9),
            anchor="center"
        )
        
        # Speed text at bottom
        if self._speed_text:
            self.create_text(
                center, center + 52,
                text=self._speed_text,
                fill="#aaaaaa", font=("Segoe UI", 9),
                anchor="center"
            )
    
    def set_progress(self, progress: float, transferred: str = "",
                    remaining: str = "", speed: str = ""):
        """Update progress with animation."""
        self._animate_target = min(1.0, max(0.0, progress))
        self._transferred_text = transferred
        self._remaining_text = remaining
        self._speed_text = speed
        
        # Smooth animation
        if self._animation_id:
            self.after_cancel(self._animation_id)
        self._animate_step()
    
    def _animate_step(self):
        """Animate progress towards target."""
        diff = self._animate_target - self._progress
        if abs(diff) < 0.001:
            self._progress = self._animate_target
            self._draw()
            return
        
        # Ease-out animation
        self._progress += diff * 0.15
        self._draw()
        self._animation_id = self.after(16, self._animate_step)  # ~60fps


class GlowingProgressBar(ctk.CTkFrame):
    """
    Eye-catching progress bar with glow effect and dual percentage display.
    Shows transferred percentage on left, remaining on right.
    """
    
    def __init__(self, parent, height: int = 35, **kwargs):
        super().__init__(parent, height=height, **kwargs)
        self.pack_propagate(False)
        
        self._progress = 0.0
        self._build_ui()
    
    def _build_ui(self):
        # Top labels
        self.label_frame = ctk.CTkFrame(self, fg_color="transparent", height=18)
        self.label_frame.pack(fill="x")
        self.label_frame.pack_propagate(False)
        
        self.transferred_label = ctk.CTkLabel(
            self.label_frame,
            text="⬤ Transferred: 0%",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#00ff99",
            anchor="w"
        )
        self.transferred_label.pack(side="left", padx=5)
        
        self.remaining_label = ctk.CTkLabel(
            self.label_frame,
            text="Remaining: 100% ⬤",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#ff6644",
            anchor="e"
        )
        self.remaining_label.pack(side="right", padx=5)
        
        # Progress bar
        self.bar_frame = ctk.CTkFrame(self, height=14, corner_radius=7)
        self.bar_frame.pack(fill="x", padx=5, pady=2)
        
        self.progress_bar = ctk.CTkProgressBar(
            self.bar_frame, height=12, corner_radius=6,
            progress_color="#00d4ff",
            fg_color="#2a2a4a"
        )
        self.progress_bar.pack(fill="x", padx=2, pady=1)
        self.progress_bar.set(0)
    
    def set_progress(self, progress: float):
        """Update progress bar with percentage labels."""
        self._progress = min(1.0, max(0.0, progress))
        percent = self._progress * 100
        remaining = 100 - percent
        
        self.progress_bar.set(self._progress)
        self.transferred_label.configure(text=f"⬤ Transferred: {percent:.1f}%")
        self.remaining_label.configure(text=f"Remaining: {remaining:.1f}% ⬤")
        
        # Change colors based on progress
        if percent >= 90:
            self.progress_bar.configure(progress_color="#00ff66")
        elif percent >= 50:
            self.progress_bar.configure(progress_color="#00d4ff")
        elif percent >= 25:
            self.progress_bar.configure(progress_color="#ffaa00")
        else:
            self.progress_bar.configure(progress_color="#ff6644")


class StatCard(ctk.CTkFrame):
    """
    Eye-catching stat card with icon, value, and label.
    Used for speed, ETA, file count, etc.
    """
    
    def __init__(self, parent, icon: str, label: str, value: str = "--",
                 accent_color: str = "#00d4ff", **kwargs):
        kwargs.setdefault("corner_radius", 12)
        super().__init__(parent, **kwargs)
        
        self.accent_color = accent_color
        self._build_ui(icon, label, value)
    
    def _build_ui(self, icon: str, label: str, value: str):
        # Icon
        self.icon_label = ctk.CTkLabel(
            self, text=icon,
            font=ctk.CTkFont(size=22)
        )
        self.icon_label.pack(pady=(8, 2))
        
        # Value
        self.value_label = ctk.CTkLabel(
            self, text=value,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.accent_color
        )
        self.value_label.pack(pady=0)
        
        # Label
        self.label = ctk.CTkLabel(
            self, text=label,
            font=ctk.CTkFont(size=10),
            text_color="#888888"
        )
        self.label.pack(pady=(0, 8))
    
    def set_value(self, value: str):
        """Update the displayed value."""
        self.value_label.configure(text=value)


class AnimatedDots(ctk.CTkLabel):
    """Animated dots indicator for ongoing operations."""
    
    def __init__(self, parent, base_text: str = "Transferring", **kwargs):
        super().__init__(parent, text=base_text, **kwargs)
        self.base_text = base_text
        self._dot_count = 0
        self._animating = False
        self._anim_id = None
    
    def start(self):
        """Start dot animation."""
        self._animating = True
        self._animate()
    
    def stop(self):
        """Stop animation."""
        self._animating = False
        if self._anim_id:
            self.after_cancel(self._anim_id)
    
    def _animate(self):
        if not self._animating:
            return
        self._dot_count = (self._dot_count + 1) % 4
        dots = "." * self._dot_count
        self.configure(text=f"{self.base_text}{dots}")
        self._anim_id = self.after(500, self._animate)


class FileProgressItem(ctk.CTkFrame):
    """Individual file progress display with mini progress bar."""
    
    def __init__(self, parent, filename: str, size_text: str,
                 status_icon: str = "⏳", **kwargs):
        super().__init__(parent, height=36, corner_radius=6, **kwargs)
        self.pack_propagate(False)
        
        # Status icon
        self.status = ctk.CTkLabel(self, text=status_icon, width=25)
        self.status.pack(side="left", padx=4)
        
        # File info
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=2)
        
        self.name_label = ctk.CTkLabel(
            info_frame, text=filename,
            font=ctk.CTkFont(size=11), anchor="w"
        )
        self.name_label.pack(fill="x", side="top")
        
        self.mini_bar = ctk.CTkProgressBar(
            info_frame, height=4, corner_radius=2,
            progress_color="#00d4ff"
        )
        self.mini_bar.pack(fill="x", side="bottom", pady=(0, 2))
        self.mini_bar.set(0)
        
        # Size and percentage
        self.size_label = ctk.CTkLabel(
            self, text=size_text,
            font=ctk.CTkFont(size=10), width=70,
            text_color="#aaaaaa"
        )
        self.size_label.pack(side="right", padx=4)
        
        self.pct_label = ctk.CTkLabel(
            self, text="0%",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=45, text_color="#00d4ff"
        )
        self.pct_label.pack(side="right", padx=2)
    
    def update_progress(self, progress: float, status_icon: str = None):
        """Update file progress."""
        self.mini_bar.set(progress)
        self.pct_label.configure(text=f"{progress * 100:.0f}%")
        if status_icon:
            self.status.configure(text=status_icon)
