"""
Connection Manager for Mobile2Storage.
Handles ADB over WiFi connections to Android 10+ devices.
Supports both USB and wireless ADB connections.
"""

import subprocess
import threading
import time
import re
import os
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
from enum import Enum


class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class DeviceInfo:
    serial: str
    model: str = "Unknown"
    android_version: str = "Unknown"
    storage_total: int = 0
    storage_free: int = 0
    connection_type: str = "unknown"  # "usb" or "wifi"
    ip_address: str = ""
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED


class ConnectionManager:
    """Manages ADB connections to Android devices."""
    
    def __init__(self):
        self.device: Optional[DeviceInfo] = None
        self.status = ConnectionStatus.DISCONNECTED
        self._adb_path = self._find_adb()
        self._callbacks: List[Callable] = []
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
    
    def _find_adb(self) -> str:
        """Find ADB executable path."""
        # Check common locations
        common_paths = [
            "adb",  # In PATH
            os.path.expanduser("~/Android/Sdk/platform-tools/adb"),
            "C:\\Users\\{}\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe".format(
                os.environ.get("USERNAME", "")
            ),
            "C:\\Android\\platform-tools\\adb.exe",
            "/usr/local/bin/adb",
            "/usr/bin/adb",
        ]
        
        for path in common_paths:
            try:
                result = subprocess.run(
                    [path, "version"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                continue
        
        return "adb"  # Default, hope it's in PATH
    
    def add_status_callback(self, callback: Callable):
        """Register a callback for connection status changes."""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self):
        """Notify all registered callbacks of status change."""
        for cb in self._callbacks:
            try:
                cb(self.status, self.device)
            except Exception:
                pass
    
    def run_adb(self, *args, timeout: int = 30) -> Optional[str]:
        """Run an ADB command and return stdout."""
        cmd = [self._adb_path] + list(args)
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None
    
    def run_adb_shell(self, command: str, timeout: int = 30) -> Optional[str]:
        """Run an ADB shell command."""
        return self.run_adb("shell", command, timeout=timeout)
    
    def get_connected_devices(self) -> List[str]:
        """Get list of connected device serials."""
        output = self.run_adb("devices")
        if not output:
            return []
        
        devices = []
        for line in output.split("\n")[1:]:
            parts = line.strip().split("\t")
            if len(parts) == 2 and parts[1] == "device":
                devices.append(parts[0])
        
        return devices
    
    def connect_usb(self) -> bool:
        """Connect to device via USB."""
        self.status = ConnectionStatus.CONNECTING
        self._notify_callbacks()
        
        devices = self.get_connected_devices()
        if not devices:
            self.status = ConnectionStatus.ERROR
            self._notify_callbacks()
            return False
        
        serial = devices[0]
        self.device = self._get_device_info(serial)
        if self.device:
            self.device.connection_type = "usb"
            self.status = ConnectionStatus.CONNECTED
        else:
            self.status = ConnectionStatus.ERROR
        
        self._notify_callbacks()
        return self.status == ConnectionStatus.CONNECTED
    
    def connect_wifi(self, ip_address: str, port: int = 5555) -> bool:
        """Connect to device via WiFi ADB (Android 10+)."""
        self.status = ConnectionStatus.CONNECTING
        self._notify_callbacks()
        
        target = f"{ip_address}:{port}"
        
        # Try to connect
        output = self.run_adb("connect", target, timeout=10)
        if output and ("connected" in output.lower() or "already" in output.lower()):
            self.device = self._get_device_info(target)
            if self.device:
                self.device.connection_type = "wifi"
                self.device.ip_address = ip_address
                self.status = ConnectionStatus.CONNECTED
                self._notify_callbacks()
                return True
        
        self.status = ConnectionStatus.ERROR
        self._notify_callbacks()
        return False
    
    def enable_wifi_adb(self) -> Optional[str]:
        """
        Enable wireless ADB on a USB-connected device (Android 11+).
        Returns the IP address to connect to.
        """
        # First check if device is connected via USB
        devices = self.get_connected_devices()
        if not devices:
            return None
        
        # Get device IP address
        ip_output = self.run_adb_shell("ip route | grep wlan0 | awk '{print $9}'")
        if not ip_output:
            # Try alternative method
            ip_output = self.run_adb_shell(
                "ifconfig wlan0 | grep 'inet addr' | cut -d: -f2 | awk '{print $1}'"
            )
        if not ip_output:
            # Another alternative for newer Android
            ip_output = self.run_adb_shell(
                "ip addr show wlan0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1"
            )
        
        if not ip_output:
            return None
        
        ip_address = ip_output.strip().split("\n")[0]
        
        # Enable tcpip mode
        self.run_adb("tcpip", "5555")
        time.sleep(2)  # Wait for device to restart in TCP mode
        
        return ip_address
    
    def pair_device(self, ip_address: str, port: int, pairing_code: str) -> bool:
        """Pair with a device using Android 11+ wireless debugging."""
        target = f"{ip_address}:{port}"
        try:
            proc = subprocess.Popen(
                [self._adb_path, "pair", target],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = proc.communicate(input=pairing_code + "\n", timeout=15)
            return "successfully" in stdout.lower() or "successfully" in stderr.lower()
        except (subprocess.TimeoutExpired, OSError):
            return False
    
    def _get_device_info(self, serial: str) -> Optional[DeviceInfo]:
        """Get detailed device information."""
        try:
            # Get model
            model = self.run_adb("-s", serial, "shell", "getprop", "ro.product.model")
            if not model:
                model = "Unknown Device"
            
            # Get Android version
            version = self.run_adb("-s", serial, "shell", "getprop", "ro.build.version.release")
            if not version:
                version = "Unknown"
            
            # Get storage info
            storage_total, storage_free = self._get_storage_info(serial)
            
            return DeviceInfo(
                serial=serial,
                model=model,
                android_version=version,
                storage_total=storage_total,
                storage_free=storage_free
            )
        except Exception:
            return None
    
    def _get_storage_info(self, serial: str) -> tuple:
        """Get storage information from device."""
        output = self.run_adb("-s", serial, "shell", "df", "/sdcard")
        if not output:
            return (0, 0)
        
        lines = output.strip().split("\n")
        if len(lines) < 2:
            return (0, 0)
        
        # Parse df output
        parts = lines[1].split()
        try:
            # df outputs in 1K blocks
            total = int(parts[1]) * 1024
            free = int(parts[3]) * 1024
            return (total, free)
        except (IndexError, ValueError):
            return (0, 0)
    
    def disconnect(self):
        """Disconnect from device."""
        if self.device and self.device.connection_type == "wifi":
            self.run_adb("disconnect", f"{self.device.ip_address}:5555")
        
        self.device = None
        self.status = ConnectionStatus.DISCONNECTED
        self._running = False
        self._notify_callbacks()
    
    def start_monitoring(self):
        """Start monitoring connection status in background."""
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self._running = False
    
    def _monitor_loop(self):
        """Background loop to monitor device connection."""
        while self._running:
            if self.status == ConnectionStatus.CONNECTED and self.device:
                devices = self.get_connected_devices()
                if self.device.serial not in devices:
                    self.status = ConnectionStatus.DISCONNECTED
                    self.device = None
                    self._notify_callbacks()
            time.sleep(3)
    
    @property
    def is_connected(self) -> bool:
        return self.status == ConnectionStatus.CONNECTED
    
    @property
    def adb_available(self) -> bool:
        """Check if ADB is available on the system."""
        return self.run_adb("version") is not None
