"""
QR Code Generator for Mobile2Storage.
Generates QR code image for easy phone connection.
Uses a pure-Python QR code implementation (no external dependency needed for basic QR).
"""

import io
import math
from typing import Optional


def generate_qr_data(url: str) -> list:
    """
    Generate QR code matrix data.
    Simple implementation for URL encoding.
    Returns a 2D list of booleans (True = black module).
    """
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=4,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=1,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Get matrix
        matrix = qr.get_matrix()
        return matrix
    except ImportError:
        # Fallback: return None, UI will show URL text instead
        return None


def generate_qr_image_bytes(url: str, size: int = 200) -> Optional[bytes]:
    """
    Generate QR code as PNG image bytes.
    Returns PNG data that can be displayed in tkinter.
    """
    try:
        import qrcode
        from PIL import Image
        
        qr = qrcode.QRCode(
            version=4,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=3,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="white", back_color="#161b22")
        img = img.resize((size, size), Image.NEAREST)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
        
    except ImportError:
        return None


def generate_qr_for_tkinter(url: str, size: int = 200):
    """
    Generate QR code as a tkinter-compatible PhotoImage.
    Returns a CTkImage or PhotoImage that can be set on a label.
    """
    try:
        import qrcode
        from PIL import Image, ImageTk
        import customtkinter as ctk
        
        qr = qrcode.QRCode(
            version=4,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=3,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="white", back_color="#161b22")
        img = img.get_image().resize((size, size), Image.NEAREST)
        
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        
    except ImportError:
        return None
