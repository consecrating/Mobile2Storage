"""
Utility helpers for Mobile2Storage.
Provides formatting functions and hash calculation.
"""

import hashlib
import os
from typing import Optional


def format_size(size_bytes: int) -> str:
    """Convert bytes to human-readable size string."""
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} B"
    return f"{size:.2f} {units[unit_index]}"


def format_speed(bytes_per_second: float) -> str:
    """Convert bytes/second to human-readable speed string."""
    if bytes_per_second <= 0:
        return "0 B/s"
    
    units = ["B/s", "KB/s", "MB/s", "GB/s"]
    unit_index = 0
    speed = float(bytes_per_second)
    
    while speed >= 1024.0 and unit_index < len(units) - 1:
        speed /= 1024.0
        unit_index += 1
    
    return f"{speed:.1f} {units[unit_index]}"


def format_time(seconds: float) -> str:
    """Convert seconds to human-readable time string."""
    if seconds <= 0:
        return "0s"
    if seconds == float('inf'):
        return "Calculating..."
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def calculate_hash(filepath: str, algorithm: str = "md5", chunk_size: int = 8192) -> Optional[str]:
    """Calculate file hash for integrity verification."""
    try:
        hasher = hashlib.new(algorithm)
        with open(filepath, "rb") as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                hasher.update(data)
        return hasher.hexdigest()
    except (IOError, OSError):
        return None


def ensure_directory(path: str) -> bool:
    """Ensure a directory exists, creating it if necessary."""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except OSError:
        return False


def get_file_extension(filename: str) -> str:
    """Get file extension in lowercase."""
    _, ext = os.path.splitext(filename)
    return ext.lower()


def is_media_file(filename: str) -> bool:
    """Check if file is a common media file."""
    media_extensions = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif',
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.3gp', '.webm',
        '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
    }
    return get_file_extension(filename) in media_extensions
