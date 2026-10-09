"""
Zero-persistence Computer Vision and OCR Pipeline.
Processes image byte buffers in RAM using OpenCV and EasyOCR.
Requires no external system binaries.
"""
import cv2
import numpy as np
import easyocr

# Initialize EasyOCR reader in memory (English language model)
# download_enabled=True fetches the lightweight model weights on the first run only.
_reader = None

def get_ocr_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(['en'], gpu=False)
    return _reader

def preprocess_sticker_image(image_bytes: bytes) -> np.ndarray:
    """
    Cleans raw sticker scans/photos: converts to grayscale, reduces noise,
    and applies Otsu binarization to enhance low-contrast thermal text.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Could not decode image buffer.")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    filtered = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    _, thresh = cv2.threshold(
        filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return thresh

def extract_text_from_sticker(image_bytes: bytes) -> str:
    """
    Extracts text from image bytes using EasyOCR.
    Returns plain text lines joined by newlines.
    """
    processed_img = preprocess_sticker_image(image_bytes)
    reader = get_ocr_reader()
    
    # detail=0 returns a list of raw strings
    text_lines = reader.readtext(processed_img, detail=0)
    return "\n".join(text_lines)