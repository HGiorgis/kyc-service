import pytesseract
from PIL import Image
import cv2
import re

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_id_info(image_path):
    """Extract specific ID information"""
    
    print("=" * 60)
    print(f"EXTRACTING INFO FROM: {image_path}")
    print("=" * 60)
    
    # Read image
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Enhance for better OCR
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Extract text
    text = pytesseract.image_to_string(thresh)
    
    print("\n📝 FULL EXTRACTED TEXT:")
    print("-" * 40)
    print(text)
    print("-" * 40)
    
    # Look for ID number patterns
    id_patterns = [
        r'\d{4}-\d{4}-\d{4}',  # XXXX-XXXX-XXXX
        r'\d{9,12}',            # 9-12 digits
        r'[A-Z]{1,3}\d{6,9}',   # Letters + digits
    ]
    
    print("\n🔍 POTENTIAL ID NUMBERS FOUND:")
    for pattern in id_patterns:
        matches = re.findall(pattern, text)
        if matches:
            for match in matches:
                print(f"  - {match}")
    
    # Look for name patterns
    print("\n👤 POTENTIAL NAMES FOUND:")
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if len(line) > 10 and not re.search(r'\d', line):
            if any(word in line.upper() for word in ['NAME', 'APELYIDO', 'GIVEN']):
                print(f"  - {line}")
    
    return text

# Extract from front
front_text = extract_id_info(r"D:\Pictures\Personal\front.jpg")

# Extract from back
print("\n" + "=" * 60)
back_text = extract_id_info(r"D:\Pictures\Personal\back.jpg")