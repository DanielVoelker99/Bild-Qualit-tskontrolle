import io
import struct
import streamlit as st
from PIL import Image, ImageCms, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

# ---- Prüf-Schwellen ----
REQUIRED_DPI = 300
REQUIRED_LONGEST_PX = 2401
REQUIRED_ICC_NAME = "eciRGB v2"

st.set_page_config(page_title="Bild-Qualitätskontrolle", page_icon="🖼️")
st.title("🖼️ Bild-Qualitätskontrolle")
st.caption("Prüft: 300 DPI • längste Seite ≥ 2401 px • ICC: eciRGB v2 • Freistellungspfad aktiv & geschlossen")

uploaded = st.file_uploader("Bild hochladen (JPG, TIFF, PNG empfohlen)", type=["jpg", "jpeg", "tif", "tiff", "png"])

# ----------------- Hilfsfunktionen -----------------
def get_dpi(img: Image.Image):
    if "dpi" in img.info and isinstance(img.info["dpi"], tuple):
        xdpi, ydpi = img.info["dpi"]
        return float(xdpi), float(ydpi)
    try:
        exif = img.getexif()
        XRes = exif.get(0x011A)  # 282
        YRes = exif.get(0x011B)  # 283
        Unit = exif.get(0x0128)  # 296: 2=inch, 3=cm

        def rational_to_float(val):
            try:
                if isinstance(val, tuple) and len(val) == 2:
                    return float(val[0]) / float(val[1] or 1)
                return
