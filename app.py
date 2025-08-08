import io
import struct
import sys
import streamlit as st
from PIL import Image, ImageCms, ImageFile
import numpy as np

ImageFile.LOAD_TRUNCATED_IMAGES = True

# ---- Prüf-Schwellen ----
REQUIRED_DPI = 300
REQUIRED_LONGEST_PX = 2401
REQUIRED_ICC_NAME = "eciRGB v2"

st.set_page_config(page_title="Bild-Qualitätskontrolle", page_icon="🖼️")
st.title("🖼️ Bild-Qualitätskontrolle")
st.caption("Prüft: 300 DPI • längste Seite ≥ 2401 px • ICC: eciRGB v2 • Freistellungspfad aktiv & geschlossen")

uploaded = st.file_uploader("Bild hochladen (JPG, TIFF, PNG empfohlen)", type=["jpg", "jpeg", "tif", "tiff", "png"])

def get_dpi(img: Image.Image):
    # 1) Direkt aus info
    if "dpi" in img.info and isinstance(img.info["dpi"], tuple):
        xdpi, ydpi = img.info["dpi"]
        return float(xdpi), float(ydpi)
    # 2) EXIF-Fallback
    try:
        exif = img.getexif()
        XRes = exif.get(0x011A)  # 282
        YRes = exif.get(0x011B)  # 283
        Unit = exif.get(0x0128)  # 296: 2=inch, 3=cm
        def rational_to_float(val):
            try:
                if isinstance(val, tuple) and len(val) == 2:
                    return float(val[0]) / float(val[1] or 1)
                return float(val)
            except Exception:
                return None
        x = rational_to_float(XRes)
        y = rational_to_float(YRes)
        if x and y and Unit:
            if Unit == 2:  # inch
                return x, y
            if Unit == 3:  # cm
                return x * 2.54, y * 2.54
    except Exception:
        pass
    return None, None

def get_icc_description(img: Image.Image):
    icc_bytes = img.info.get("icc_profile")
    if not icc_bytes:
        return None
    try:
        prof = ImageCms.getOpenProfile(io.BytesIO(icc_bytes))
        # Beschreibung/Name auslesen
        desc = ImageCms.getProfileDescription(prof) or ""
        name = ImageCms.getProfileName(prof) or ""
        # Kombinieren & vereinheitlichen
        return (desc + " " + name).strip()
    except Exception:
        return None

# --- Photoshop APP13 / 8BIM Parser (für JPEG, ggf. auch in TIFF-Tag 34377, hier Fokus: JPEG) ---
def parse_jpeg_app13_psir(jpeg_bytes: bytes):
    """Gibt eine Liste von (res_id, name, data) der 8BIM-Resources aus APP13 (Photoshop 3.0) zurück."""
    res = []
    i = 0
    # JPEG Marker-Scan
    while i < len(jpeg_bytes) - 1:
        if jpeg_bytes[i] == 0xFF and jpeg_bytes[i+1] != 0x00:
            marker = jpeg_bytes[i+1]
            i += 2
            # SOI/EOI/SOS ohne Länge überspringen
            if marker in (0xD8, 0xD9, 0xDA):
                continue
            if i + 2 > len(jpeg_bytes):
                break
            seglen = struct.unpack(">H", jpeg_bytes[i:i+2])[0]
            i += 2
            payload = jpeg_bytes[i:i+seglen-2]
            i += seglen-2
            # APP13 = 0xED
            if marker == 0xED and payload.startswith(b"Photoshop 3.0\x00"):
                psir = payload[14:]
                # APP13 kann mehrfach vorkommen – wi
