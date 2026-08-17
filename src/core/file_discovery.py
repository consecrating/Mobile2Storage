"""
File Discovery Module for Mobile2Storage.
Uses streaming/incremental file discovery to avoid the 'stuck calculating' problem.
Files are discovered progressively and transfer begins immediately.
"""

import threading
import time
from typing import Optional, List, Callable, Generator
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from .connection_manager import ConnectionManager


class FileCategory(Enum):
    PHOTO = "Photos"
    VIDEO = "Videos"
    AUDIO = "Audio"
    DOCUMENT = "Documents"
    APP = "Apps"
    OTHER = "Other"


@dataclass
class FileItem:
    """Represents a single file on the Android device."""
    remote_path: str
    filename: str
    size: int
    category: FileCategory
    modified_time: str = ""
    transferred: bool = False
    transfer_progress: float = 0.0
    error: Optional[str] = None


@dataclass
class DiscoveryStats:
    """Real-time discovery statistics."""
    files_found: int = 0
    total_size_found: int = 0
    directories_scanned: int = 0
    is_complete: bool = False
    is_running: bool = False
    categories: dict = field(default_factory=lambda: {
        cat: {"count": 0, "size": 0} for cat in FileCategory
    })


# File extension to category mapping
EXTENSION_MAP = {
    # Photos
    '.jpg': FileCategory.PHOTO, '.jpeg': FileCategory.PHOTO,
    '.png': FileCategory.PHOTO, '.gif': FileCategory.PHOTO,
    '.bmp': FileCategory.PHOTO, '.webp': FileCategory.PHOTO,
    '.heic': FileCategory.PHOTO, '.heif': FileCategory.PHOTO,
    '.raw': FileCategory.PHOTO, '.dng': FileCategory.PHOTO,
    # Videos
    '.mp4': FileCategory.VIDEO, '.avi': FileCategory.VIDEO,
    '.mkv': FileCategory.VIDEO, '.mov': FileCategory.VIDEO,
    '.wmv': FileCategory.VIDEO, '.flv': FileCategory.VIDEO,
    '.3gp': FileCategory.VIDEO, '.webm': FileCategory.VIDEO,
    '.m4v': FileCategory.VIDEO,
    # Audio
    '.mp3': FileCategory.AUDIO, '.wav': FileCategory.AUDIO,
    '.flac': FileCategory.AUDIO, '.aac': FileCategory.AUDIO,
    '.ogg': FileCategory.AUDIO, '.wma': FileCategory.AUDIO,
    '.m4a': FileCategory.AUDIO, '.opus': FileCategory.AUDIO,
    # Documents
    '.pdf': FileCategory.DOCUMENT, '.doc': FileCategory.DOCUMENT,
    '.docx': FileCategory.DOCUMENT, '.xls': FileCategory.DOCUMENT,
    '.xlsx': FileCategory.DOCUMENT, '.ppt': FileCategory.DOCUMENT,
    '.pptx': FileCategory.DOCUMENT, '.txt': FileCategory.DOCUMENT,
    '.csv': FileCategory.DOCUMENT, '.zip': FileCategory.DOCUMENT,
    '.rar': FileCategory.DOCUMENT, '.7z': FileCategory.DOCUMENT,
    # Apps
    '.apk': FileCategory.APP, '.xapk': FileCategory.APP,
}


class FileDiscovery:
    """
    Streaming file discovery that begins transfer immediately.
    Solves the 'stuck calculating' problem by not requiring full scan before transfer.
    """
    
    def __init__(self, connection: ConnectionManager):
        self.connection = connection
        self.stats = DiscoveryStats()
        self._file_queue: deque = deque()
        self._all_files: List[FileItem] = []
        self._discovery_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._callbacks: List[Callable] = []
        
        # Default scan paths on Android
        self.scan_paths = [
            "/sdcard/DCIM",
            "/sdcard/Pictures",
            "/sdcard/Download",
            "/sdcard/Documents",
            "/sdcard/Music",
            "/sdcard/Movies",
            "/sdcard/WhatsApp",
            "/sdcard/Telegram",
            "/sdcard/Android/media",
        ]
    
    def add_discovery_callback(self, callback: Callable):
        """Register callback for discovery progress updates."""
        self._callbacks.append(callback)
    
    def _notify(self):
        """Notify callbacks of discovery progress."""
        for cb in self._callbacks:
            try:
                cb(self.stats)
            except Exception:
                pass
    
    def start_discovery(self, paths: Optional[List[str]] = None, 
                       categories: Optional[List[FileCategory]] = None):
        """
        Start streaming file discovery in background.
        Files are immediately available for transfer as they're found.
        """
        if self._running:
            return
        
        if paths:
            self.scan_paths = paths
        
        self._running = True
        self.stats = DiscoveryStats()
        self.stats.is_running = True
        self._file_queue.clear()
        self._all_files.clear()
        
        self._discovery_thread = threading.Thread(
            target=self._discover_files,
            args=(categories,),
            daemon=True
        )
        self._discovery_thread.start()
    
    def stop_discovery(self):
        """Stop ongoing discovery."""
        self._running = False
        self.stats.is_running = False
    
    def _discover_files(self, categories: Optional[List[FileCategory]] = None):
        """
        Main discovery loop - scans directories incrementally.
        Uses 'find' command for efficient listing without loading everything in memory.
        """
        for scan_path in self.scan_paths:
            if not self._running:
                break
            
            self._scan_directory(scan_path, categories)
        
        self.stats.is_complete = True
        self.stats.is_running = False
        self._notify()
    
    def _scan_directory(self, path: str, categories: Optional[List[FileCategory]] = None):
        """
        Scan a single directory using ADB shell find command.
        Processes results in batches for efficiency.
        """
        # Use find command for efficient file listing with size
        # Format: size path
        cmd = f'find "{path}" -type f -exec stat -c "%s %Y %n" {{}} \\; 2>/dev/null'
        output = self.connection.run_adb_shell(cmd, timeout=120)
        
        if not output:
            # Fallback: try ls -laR for compatibility
            cmd_fallback = f'ls -laR "{path}" 2>/dev/null'
            output = self.connection.run_adb_shell(cmd_fallback, timeout=120)
            if output:
                self._parse_ls_output(output, path, categories)
            return
        
        self.stats.directories_scanned += 1
        
        for line in output.split("\n"):
            if not self._running:
                break
            
            line = line.strip()
            if not line:
                continue
            
            try:
                parts = line.split(" ", 2)
                if len(parts) < 3:
                    continue
                
                size = int(parts[0])
                modified = parts[1]
                filepath = parts[2]
                
                # Get filename
                filename = filepath.split("/")[-1] if "/" in filepath else filepath
                
                # Determine category
                ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
                category = EXTENSION_MAP.get(ext, FileCategory.OTHER)
                
                # Filter by category if specified
                if categories and category not in categories:
                    continue
                
                # Skip very small files (< 1KB) - likely system files
                if size < 1024:
                    continue
                
                file_item = FileItem(
                    remote_path=filepath,
                    filename=filename,
                    size=size,
                    category=category,
                    modified_time=modified
                )
                
                with self._lock:
                    self._file_queue.append(file_item)
                    self._all_files.append(file_item)
                    self.stats.files_found += 1
                    self.stats.total_size_found += size
                    self.stats.categories[category]["count"] += 1
                    self.stats.categories[category]["size"] += size
                
                # Notify every 50 files for UI responsiveness
                if self.stats.files_found % 50 == 0:
                    self._notify()
                    
            except (ValueError, IndexError):
                continue
        
        self._notify()
    
    def _parse_ls_output(self, output: str, base_path: str, 
                         categories: Optional[List[FileCategory]] = None):
        """Fallback parser for ls -laR output."""
        current_dir = base_path
        
        for line in output.split("\n"):
            if not self._running:
                break
            
            line = line.strip()
            
            if line.endswith(":"):
                current_dir = line[:-1]
                self.stats.directories_scanned += 1
                continue
            
            if not line or line.startswith("total") or line.startswith("d"):
                continue
            
            # Parse ls -la line: permissions links owner group size date time filename
            parts = line.split(None, 7)
            if len(parts) < 8:
                continue
            
            try:
                size = int(parts[4])
                filename = parts[7]
                filepath = f"{current_dir}/{filename}"
                
                ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
                category = EXTENSION_MAP.get(ext, FileCategory.OTHER)
                
                if categories and category not in categories:
                    continue
                
                if size < 1024:
                    continue
                
                file_item = FileItem(
                    remote_path=filepath,
                    filename=filename,
                    size=size,
                    category=category
                )
                
                with self._lock:
                    self._file_queue.append(file_item)
                    self._all_files.append(file_item)
                    self.stats.files_found += 1
                    self.stats.total_size_found += size
                    self.stats.categories[category]["count"] += 1
                    self.stats.categories[category]["size"] += size
                
                if self.stats.files_found % 50 == 0:
                    self._notify()
                    
            except (ValueError, IndexError):
                continue
    
    def get_next_batch(self, batch_size: int = 10) -> List[FileItem]:
        """Get next batch of files ready for transfer (non-blocking)."""
        batch = []
        with self._lock:
            for _ in range(min(batch_size, len(self._file_queue))):
                batch.append(self._file_queue.popleft())
        return batch
    
    def get_all_files(self) -> List[FileItem]:
        """Get all discovered files so far."""
        with self._lock:
            return list(self._all_files)
    
    def get_files_by_category(self, category: FileCategory) -> List[FileItem]:
        """Get files filtered by category."""
        with self._lock:
            return [f for f in self._all_files if f.category == category]
    
    @property
    def has_pending_files(self) -> bool:
        """Check if there are files waiting to be transferred."""
        with self._lock:
            return len(self._file_queue) > 0
    
    @property
    def pending_count(self) -> int:
        """Number of files waiting to transfer."""
        with self._lock:
            return len(self._file_queue)
