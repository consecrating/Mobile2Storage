"""
Receiver Server for Mobile2Storage.
A local HTTP server that receives file uploads from the phone's browser.
Supports chunked uploads for large files with progress tracking.

How it works:
1. PC starts this HTTP server on local network
2. Phone connects via browser (QR code scan)
3. Phone selects files and uploads them
4. Server receives chunks and saves to destination folder
"""

import os
import json
import time
import socket
import threading
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse, unquote
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass, field

from ..utils.helpers import format_size, ensure_directory


@dataclass
class FileTransfer:
    """Tracks a single file being received."""
    filename: str
    total_size: int
    received_size: int = 0
    start_time: float = 0.0
    status: str = "receiving"  # receiving, complete, failed
    local_path: str = ""
    speed: float = 0.0


@dataclass
class ServerStats:
    """Overall server statistics."""
    total_files_received: int = 0
    total_bytes_received: int = 0
    active_transfers: int = 0
    current_speed: float = 0.0
    connected_devices: int = 0
    is_running: bool = False
    files: List[FileTransfer] = field(default_factory=list)


class UploadHandler(BaseHTTPRequestHandler):
    """HTTP request handler for file uploads from mobile browser."""

    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass

    def do_GET(self):
        """Serve the mobile upload page."""
        if self.path == "/" or self.path == "/index.html":
            self._serve_upload_page()
        elif self.path == "/status":
            self._serve_status()
        elif self.path == "/phone-command":
            self._serve_phone_command()
        elif self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Handle file upload."""
        if self.path == "/upload":
            self._handle_upload()
        elif self.path == "/upload-chunk":
            self._handle_chunked_upload()
        elif self.path == "/phone-ready":
            self._handle_phone_ready()
        elif self.path == "/phone-response":
            self._handle_phone_response()
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def _set_cors_headers(self):
        """Set CORS headers for cross-origin access."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def _serve_upload_page(self):
        """Serve the mobile-friendly upload HTML page."""
        html = self.server.mobile_page_html
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode())))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(html.encode())

    def _serve_status(self):
        """Return server status as JSON."""
        stats = self.server.get_stats()
        data = json.dumps({
            "files_received": stats.total_files_received,
            "bytes_received": stats.total_bytes_received,
            "active": stats.active_transfers,
            "speed": stats.current_speed,
            "phone_connected": self.server.phone_connected,
        })
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(data.encode())

    def _serve_phone_command(self):
        """Phone polls this to get commands from PC."""
        # Get next command from queue (or empty response)
        cmd = self.server.get_next_command()
        data = json.dumps(cmd) if cmd else json.dumps({})
        status = 200 if cmd else 204
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._set_cors_headers()
        self.end_headers()
        if cmd:
            self.wfile.write(data.encode())

    def _handle_phone_ready(self):
        """Phone signals it's ready to serve files."""
        self.server.phone_connected = True
        if self.server.phone_ready_callback:
            self.server.phone_ready_callback()
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def _handle_phone_response(self):
        """Phone sends response to a command."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body)
            cmd_id = data.get("id", "")
            response_data = data.get("data", {})
            self.server.set_response(cmd_id, response_data)
        except (json.JSONDecodeError, KeyError):
            pass
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def _handle_upload(self):
        """Handle a direct file upload (for smaller files)."""
        content_length = int(self.headers.get("Content-Length", 0))
        raw_filename = unquote(self.headers.get("X-Filename", "unknown_file"))
        
        # Preserve folder structure: X-Filename can be "DCIM/Camera/photo.jpg"
        relative_path = self._sanitize_path(raw_filename)
        filename = os.path.basename(relative_path)
        
        # Create file transfer record
        transfer = FileTransfer(
            filename=filename,
            total_size=content_length,
            start_time=time.time()
        )
        self.server.stats.files.append(transfer)
        self.server.stats.active_transfers += 1

        # Determine save path (preserve folder structure)
        dest = self.server.destination_path
        local_path = os.path.join(dest, relative_path)
        local_path = self._unique_path(local_path)
        transfer.local_path = local_path

        ensure_directory(os.path.dirname(local_path))

        # Receive file data in chunks
        try:
            bytes_received = 0
            last_time = time.time()
            last_bytes = 0

            with open(local_path, "wb") as f:
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(1024 * 1024, remaining)  # 1MB chunks
                    data = self.rfile.read(chunk_size)
                    if not data:
                        break
                    f.write(data)
                    bytes_received += len(data)
                    remaining -= len(data)
                    transfer.received_size = bytes_received

                    # Calculate speed every 0.5s
                    now = time.time()
                    if now - last_time >= 0.5:
                        transfer.speed = (bytes_received - last_bytes) / (now - last_time)
                        last_time = now
                        last_bytes = bytes_received

                    # Notify progress
                    if self.server.progress_callback:
                        self.server.progress_callback(self.server.stats)

            transfer.status = "complete"
            self.server.stats.total_files_received += 1
            self.server.stats.total_bytes_received += bytes_received
            self.server.stats.active_transfers -= 1

            if self.server.progress_callback:
                self.server.progress_callback(self.server.stats)

            # Send success response
            response = json.dumps({"success": True, "filename": filename, "size": bytes_received})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(response.encode())

        except Exception as e:
            transfer.status = "failed"
            self.server.stats.active_transfers -= 1
            response = json.dumps({"success": False, "error": str(e)})
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(response.encode())

    def _handle_chunked_upload(self):
        """Handle chunked upload for large files."""
        content_length = int(self.headers.get("Content-Length", 0))
        raw_filename = unquote(self.headers.get("X-Filename", "unknown_file"))
        chunk_index = int(self.headers.get("X-Chunk-Index", "0"))
        total_chunks = int(self.headers.get("X-Total-Chunks", "1"))
        total_size = int(self.headers.get("X-Total-Size", "0"))

        # Preserve folder structure
        relative_path = self._sanitize_path(raw_filename)
        filename = os.path.basename(relative_path)
        dest = self.server.destination_path
        
        # Use temp file during chunked upload
        temp_path = os.path.join(dest, f".{filename}.m2s_partial")
        final_path = os.path.join(dest, relative_path)
        final_path = self._unique_path(final_path)

        ensure_directory(dest)

        # Find or create transfer record
        transfer = None
        for t in self.server.stats.files:
            if t.filename == filename and t.status == "receiving":
                transfer = t
                break
        
        if transfer is None:
            transfer = FileTransfer(
                filename=filename,
                total_size=total_size,
                start_time=time.time(),
                local_path=final_path
            )
            self.server.stats.files.append(transfer)
            self.server.stats.active_transfers += 1

        try:
            # Read chunk data
            data = self.rfile.read(content_length)

            # Append to temp file
            mode = "ab" if chunk_index > 0 else "wb"
            with open(temp_path, mode) as f:
                f.write(data)

            transfer.received_size += len(data)
            
            # Calculate speed
            elapsed = time.time() - transfer.start_time
            if elapsed > 0:
                transfer.speed = transfer.received_size / elapsed

            # Notify progress
            if self.server.progress_callback:
                self.server.progress_callback(self.server.stats)

            # If last chunk, finalize file
            if chunk_index == total_chunks - 1:
                os.rename(temp_path, final_path)
                transfer.status = "complete"
                transfer.local_path = final_path
                self.server.stats.total_files_received += 1
                self.server.stats.total_bytes_received += transfer.received_size
                self.server.stats.active_transfers -= 1

                if self.server.progress_callback:
                    self.server.progress_callback(self.server.stats)

            response = json.dumps({
                "success": True,
                "chunk": chunk_index,
                "total_chunks": total_chunks,
                "done": chunk_index == total_chunks - 1
            })
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(response.encode())

        except Exception as e:
            transfer.status = "failed"
            self.server.stats.active_transfers -= 1
            response = json.dumps({"success": False, "error": str(e)})
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(response.encode())

    def _sanitize_filename(self, filename: str) -> str:
        """Make filename safe for Windows/Mac/Linux."""
        # Remove path components
        filename = filename.replace("\\", "/").split("/")[-1]
        # Remove dangerous characters
        invalid = '<>:"|?*\x00'
        for ch in invalid:
            filename = filename.replace(ch, "_")
        filename = filename.strip(". ")
        return filename or "unnamed_file"

    def _sanitize_path(self, relative_path: str) -> str:
        """
        Sanitize a relative file path while PRESERVING folder structure.
        'DCIM/Camera/photo.jpg' → 'DCIM/Camera/photo.jpg' (kept as-is)
        Removes dangerous characters but keeps the directory hierarchy.
        """
        # Normalize separators
        relative_path = relative_path.replace("\\", "/")
        
        # Remove leading slashes (prevent absolute paths)
        relative_path = relative_path.lstrip("/")
        
        # Remove any .. components (prevent path traversal)
        parts = relative_path.split("/")
        safe_parts = []
        for part in parts:
            if part == ".." or part == "":
                continue
            # Remove dangerous characters from each component
            invalid = '<>:"|?*\x00'
            for ch in invalid:
                part = part.replace(ch, "_")
            part = part.strip(". ")
            if part:
                safe_parts.append(part)
        
        if not safe_parts:
            return "unnamed_file"
        
        return "/".join(safe_parts)

    def _unique_path(self, path: str) -> str:
        """Generate unique path if file already exists."""
        if not os.path.exists(path):
            return path
        name, ext = os.path.splitext(path)
        counter = 1
        while os.path.exists(path):
            path = f"{name}_{counter}{ext}"
            counter += 1
        return path


class ReceiverServer(HTTPServer):
    """
    Enhanced HTTP server for receiving files from mobile devices.
    Also handles PC↔Phone command protocol for remote file browsing.
    """

    def __init__(self, port: int, destination: str, mobile_html: str,
                 progress_callback: Optional[Callable] = None,
                 phone_ready_callback: Optional[Callable] = None):
        self.destination_path = destination
        self.mobile_page_html = mobile_html
        self.progress_callback = progress_callback
        self.phone_ready_callback = phone_ready_callback
        self.stats = ServerStats()
        self.phone_connected = False
        
        # Command queue: PC puts commands, phone polls them
        self._command_queue = []
        self._responses = {}  # cmd_id -> response data
        self._cmd_lock = threading.Lock()
        self._response_events = {}  # cmd_id -> threading.Event
        
        # Bind to all interfaces
        super().__init__(("0.0.0.0", port), UploadHandler)
        self.stats.is_running = True

    def get_stats(self) -> ServerStats:
        return self.stats
    
    def send_command(self, action: str, **kwargs) -> dict:
        """Send a command to phone and wait for response (blocking)."""
        import uuid
        cmd_id = str(uuid.uuid4())[:8]
        cmd = {"id": cmd_id, "action": action, **kwargs}
        
        event = threading.Event()
        with self._cmd_lock:
            self._command_queue.append(cmd)
            self._response_events[cmd_id] = event
        
        # Wait for phone to respond (timeout 30s)
        event.wait(timeout=30)
        
        with self._cmd_lock:
            response = self._responses.pop(cmd_id, {})
            self._response_events.pop(cmd_id, None)
        
        return response
    
    def get_next_command(self) -> Optional[dict]:
        """Get next command for phone (called by phone polling)."""
        with self._cmd_lock:
            if self._command_queue:
                return self._command_queue.pop(0)
        return None
    
    def set_response(self, cmd_id: str, data: dict):
        """Store phone response and signal waiting thread."""
        with self._cmd_lock:
            self._responses[cmd_id] = data
            event = self._response_events.get(cmd_id)
            if event:
                event.set()
    
    def list_phone_directory(self, path: str = "") -> dict:
        """Ask phone to list a directory. Returns {entries: [...], path: '...'}"""
        if not self.phone_connected:
            return {"entries": [], "path": path, "error": "Phone not connected"}
        return self.send_command("list", path=path)
    
    def request_file_transfer(self, path: str) -> dict:
        """Ask phone to send a specific file."""
        if not self.phone_connected:
            return {"success": False, "error": "Phone not connected"}
        return self.send_command("send", path=path)


def get_local_ip() -> str:
    """Get the machine's local network IP address."""
    try:
        # Create a UDP socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # Fallback
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            return "127.0.0.1"


def find_free_port(start: int = 8080, end: int = 9000) -> int:
    """Find an available port."""
    for port in range(start, end):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("0.0.0.0", port))
            s.close()
            return port
        except OSError:
            continue
    return 8080
