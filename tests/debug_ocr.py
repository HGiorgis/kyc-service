import pytesseract
from PIL import Image
import cv2
import numpy as np
import os

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def debug_ocr(image_path):
    """Debug OCR on an image"""
    
    print("=" * 60)
    print(f"DEBUGGING OCR ON: {image_path}")
    print("=" * 60)
    
    # Check if file exists
    if not os.path.exists(image_path):
        print(f"❌ File not found: {image_path}")
        return
    
    # 1. Try direct OCR without preprocessing
    print("\n1. DIRECT OCR (no preprocessing):")
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    print(f"Extracted text: {text[:200] if text else 'NO TEXT FOUND'}")
    
    # 2. Try with grayscale conversion
    print("\n2. GRAYSCALE OCR:")
    img_cv = cv2.imread(image_path)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)
    print(f"Extracted text: {text[:200] if text else 'NO TEXT FOUND'}")
    
    # 3. Try with thresholding
    print("\n3. THRESHOLD OCR:")
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    text = pytesseract.image_to_string(thresh)
    print(f"Extracted text: {text[:200] if text else 'NO TEXT FOUND'}")
    
    # 4. Try with different page segmentation modes
    print("\n4. DIFFERENT PSM MODES:")
    psm_modes = [3, 6, 7, 8, 11, 12, 13]
    for psm in psm_modes:
        custom_config = f'--psm {psm}'
        text = pytesseract.image_to_string(thresh, config=custom_config)
        if text.strip():
            print(f"PSM {psm}: {text[:100]}")
    
    # 5. Get detailed data
    print("\n5. DETAILED OCR DATA:")
    data = pytesseract.image_to_data(thresh, output_type=pytesseract.Output.DICT)
    
    confidences = []
    for i, conf in enumerate(data['conf']):
        if conf != '-1' and int(conf) > 0:
            confidences.append(int(conf))
            if data['text'][i].strip():
                print(f"Word: {data['text'][i]}, Confidence: {conf}%, Position: {data['left'][i]},{data['top'][i]}")
    
    if confidences:
        avg_conf = sum(confidences) / len(confidences)
        print(f"\nAverage confidence: {avg_conf:.1f}%")
    
    # 6. Save preprocessed image for inspection
    cv2.imwrite('debug_threshold.jpg', thresh)
    print("\n✅ Saved threshold image as 'debug_threshold.jpg' - check this file!")

if __name__ == "__main__":
    # Test on your images
    debug_ocr(r"D:\Pictures\Personal\front.jpg")
    debug_ocr(r"D:\Pictures\Personal\back.jpg")