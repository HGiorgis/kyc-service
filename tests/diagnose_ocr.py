import pytesseract
from PIL import Image
import cv2
import numpy as np
import os
import sys

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def diagnose_ocr():
    """Complete OCR diagnosis"""
    
    print("=" * 60)
    print("OCR DIAGNOSTIC TOOL")
    print("=" * 60)
    
    # 1. Check Tesseract installation
    print("\n1. CHECKING TESSERACT INSTALLATION")
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract version: {version}")
    except Exception as e:
        print(f"❌ Tesseract not found: {e}")
        print("   Please install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki")
        return False
    
    # 2. Create a test image with text
    print("\n2. CREATING TEST IMAGE")
    test_img = np.ones((300, 800, 3), dtype=np.uint8) * 255
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(test_img, "TEST PASSPORT ID: AB123456", (50, 100), font, 1, (0,0,0), 2)
    cv2.putText(test_img, "NAME: JOHN DOE", (50, 150), font, 1, (0,0,0), 2)
    cv2.putText(test_img, "DATE: 01/01/1990", (50, 200), font, 1, (0,0,0), 2)
    
    test_path = "test_image.jpg"
    cv2.imwrite(test_path, test_img)
    print(f"✅ Test image created: {test_path}")
    
    # 3. Test OCR on generated image
    print("\n3. TESTING OCR ON GENERATED IMAGE")
    img = Image.open(test_path)
    text = pytesseract.image_to_string(img)
    print(f"Extracted text: {text.strip()}")
    
    if "AB123456" in text and "JOHN DOE" in text:
        print("✅ OCR WORKING on generated image!")
    else:
        print("❌ OCR FAILED on generated image")
        print("   This indicates a Tesseract configuration issue")
    
    # 4. Test on your actual images
    print("\n4. TESTING ON YOUR ACTUAL IMAGES")
    
    image_paths = [
        r"D:\Pictures\Personal\front.jpg",
        r"D:\Pictures\Personal\back.jpg"
    ]
    
    for img_path in image_paths:
        if not os.path.exists(img_path):
            print(f"❌ Image not found: {img_path}")
            continue
        
        print(f"\n📸 Testing: {img_path}")
        
        # Try different preprocessing methods
        methods = [
            ("Original", lambda x: Image.open(x)),
            ("Grayscale", lambda x: cv2.cvtColor(cv2.imread(x), cv2.COLOR_BGR2GRAY)),
            ("Threshold", lambda x: cv2.threshold(
                cv2.cvtColor(cv2.imread(x), cv2.COLOR_BGR2GRAY), 
                0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]),
        ]
        
        for method_name, method_func in methods:
            try:
                if method_name == "Original":
                    processed = method_func(img_path)
                else:
                    processed = method_func(img_path)
                    # Save preprocessed image
                    debug_path = f"debug_{method_name.lower()}.jpg"
                    cv2.imwrite(debug_path, processed)
                
                text = pytesseract.image_to_string(processed)
                if text.strip():
                    print(f"✅ {method_name}: Found text! ({len(text)} chars)")
                    print(f"   Preview: {text[:100]}")
                    break
                else:
                    print(f"❌ {method_name}: No text found")
            except Exception as e:
                print(f"❌ {method_name}: Error - {e}")
    
    # 5. Cleanup
    if os.path.exists(test_path):
        os.remove(test_path)
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    diagnose_ocr()