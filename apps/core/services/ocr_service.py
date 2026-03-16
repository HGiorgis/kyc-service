import pytesseract
from PIL import Image
import re
import logging
import cv2
import numpy as np
import os

logger = logging.getLogger(__name__)

# Set Tesseract path (Windows); override via env TESSERACT_CMD if needed
if os.name == 'nt' and 'TESSERACT_CMD' not in os.environ:
    _default_tesseract = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(_default_tesseract):
        pytesseract.pytesseract.tesseract_cmd = _default_tesseract


class OCRService:
    """Enhanced OCR extraction from ID documents with real Tesseract confidence."""

    def __init__(self):
        # ID number: standalone patterns + label-based (ID:, Document No., DL:, etc.)
        self.id_patterns = {
            'passport': [
                r'[A-Z]{1,2}[0-9]{6,9}',
                r'[A-Z0-9]{8,12}',
                r'P[A-Z]?\s*[0-9]{6,9}',
                r'(?:Passport|Document|ID|No\.?)[:\s]*([A-Z0-9\s-]{6,20})',
            ],
            'national_id': [
                r'\d{10,16}',
                r'\d{12}',
                r'[A-Z]{1,2}\d{6,12}',
                r'\d{3}-\d{3}-\d{3}',
                r'(?:ID|National|Document|Number|No\.?)[:\s]*([A-Z0-9\s-]{8,24})',
            ],
            'drivers_license': [
                r'[A-Z]{1,3}\s*\d{5,10}',
                r'DL\s*[A-Z]?\d{5,10}',
                r'\d{8,12}',
                r'(?:DL|License|ID|Document|Number|No\.?)[:\s]*([A-Z0-9\s-]{6,20})',
            ],
            'kebele': [
                r'\d{6,12}',
                r'KB\d{6,10}',
                r'(?:ID|Kebele|Number)[:\s]*([0-9\s-]{6,16})',
            ]
        }
        self.name_patterns = [
            r'(?:NAME|FULL NAME|PRINTED NAME|Name)[:\s]*([A-Z][A-Z\s]{2,40})',
            r'(?:Pangalan|Apelyido)[:\s]*([A-Z\s]+)',
            r'(?:FN|First Name|Given Name|GIVEN NAME|First)[:\s]*([A-Z][A-Z\s]{1,30})',
            r'(?:LN|Last Name|Surname|SURNAME|Family|Last)[:\s]*([A-Z][A-Z\s]{1,30})',
        ]
        self.date_patterns = [
            r'(\d{2}[/-]\d{2}[/-]\d{4})',
            r'(\d{4}[/-]\d{2}[/-]\d{2})',
            r'(\d{2}\s+[A-Za-z]+\s+\d{4})',
            r'(?:DOB|BIRTH|Kapanganakan)[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})',
        ]
        logger.info("OCR Service initialized")

    def preprocess_image(self, image_path):
        """Preprocess image for better OCR. Returns a dict so extract_text can iterate."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return None
            h, w = img.shape[:2]
            scale = max(2000 / w, 1500 / h)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)
            denoised = cv2.fastNlMeansDenoising(sharpened, None, 10, 7, 21)
            _, thresh1 = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            thresh2 = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 5
            )
            text1 = pytesseract.image_to_string(thresh1)
            text2 = pytesseract.image_to_string(thresh2)
            best = thresh1 if len(text1) >= len(text2) else thresh2
            return {'preprocessed': best}
        except Exception as e:
            logger.error("Preprocessing error: %s", e)
            return None

    def _get_tesseract_confidence(self, pil_img, psm=6):
        """Get average word confidence (0-100) from Tesseract image_to_data."""
        try:
            data = pytesseract.image_to_data(pil_img, config=f'--psm {psm}')
            confidences = []
            for line in data.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 11:
                    try:
                        conf = int(parts[10])
                        if conf > 0:
                            confidences.append(conf)
                    except (ValueError, IndexError):
                        pass
            return sum(confidences) / len(confidences) if confidences else 0.0
        except Exception:
            return 0.0

    def extract_text(self, image_path):
        """Extract text and return success, text, length, and avg_confidence (0-100)."""
        try:
            preprocessed = self.preprocess_image(image_path)

            if preprocessed is None:
                img = Image.open(image_path).convert('RGB')
                text = pytesseract.image_to_string(img)
                avg_conf = self._get_tesseract_confidence(img)
                text_clean = re.sub(r'\s+', ' ', text).strip()
                return {
                    'success': bool(text_clean),
                    'text': text_clean or text,
                    'length': len(text_clean),
                    'avg_confidence': avg_conf,
                    'method': 'fallback',
                }

            best_text = ""
            best_len = 0
            best_conf = 0.0
            best_pil = None

            for method_name, processed_img in preprocessed.items():
                pil_img = Image.fromarray(processed_img)
                for psm in [6, 3, 12, 13]:
                    text = pytesseract.image_to_string(pil_img, config=f'--psm {psm}')
                    text_clean = re.sub(r'\s+', ' ', text).strip()
                    if len(text_clean) > best_len:
                        best_len = len(text_clean)
                        best_text = text_clean
                        best_pil = pil_img
                if best_pil is not None:
                    best_conf = self._get_tesseract_confidence(best_pil, psm=6)
                    break

            if not best_text and preprocessed:
                single = list(preprocessed.values())[0]
                pil_img = Image.fromarray(single)
                best_text = pytesseract.image_to_string(pil_img)
                best_text = re.sub(r'\s+', ' ', best_text).strip()
                best_len = len(best_text)
                best_conf = self._get_tesseract_confidence(pil_img)

            return {
                'success': best_len > 20,
                'text': best_text,
                'length': best_len,
                'avg_confidence': best_conf,
            }
        except Exception as e:
            logger.exception("OCR extraction error: %s", e)
            return {
                'success': False,
                'text': '',
                'length': 0,
                'avg_confidence': 0.0,
                'error': str(e),
            }

    def extract_id_number(self, text, id_type=None):
        """Extract ID numbers from text (standalone and label-prefixed like 'ID: G123' or 'DL 12345')."""
        found = []
        all_patterns = list(self.id_patterns.get(id_type or 'national_id', []))
        all_patterns.extend([
            r'\b\d{6,16}\b',
            r'\b[A-Z]{1,3}\d{5,10}\b',
            r'\b\d{3}-\d{3}-\d{3}\b',
            r'\b[A-Z]{2}\d{7}\b',
        ])
        for pattern in list(dict.fromkeys(all_patterns)):
            for m in re.finditer(pattern, text, re.IGNORECASE):
                raw = m.group(0)
                # If pattern has a capturing group (label-based), use group(1)
                if m.groups():
                    raw = m.group(1) or raw
                clean = re.sub(r'[^A-Z0-9]', '', raw.upper())
                if len(clean) >= 5 and clean not in found:
                    found.append(clean)
        return found

    def _normalize_for_match(self, s):
        if not s:
            return ""
        return re.sub(r'[^A-Z0-9]', '', str(s).upper())

    def _normalize_id_for_match(self, s):
        """Normalize ID for comparison: alphanumeric only, strip common prefixes (DL, ID)."""
        raw = self._normalize_for_match(s)
        if not raw:
            return ""
        for prefix in ('DL', 'ID', 'LIC'):
            if raw.startswith(prefix) and len(raw) > len(prefix):
                raw = raw[len(prefix):]
                break
        return raw

    def process_id_document(self, image_path, id_type=None, user_data=None):
        """Full OCR processing with real Tesseract confidence and optional validation."""
        result = {
            'success': False,
            'extracted_text': '',
            'id_numbers': [],
            'names': [],
            'dates': [],
            'validation': None,
            'confidence': 0.0,
        }

        extraction = self.extract_text(image_path)
        if not extraction.get('success'):
            result['error'] = extraction.get('error', 'OCR failed')
            return result

        text = extraction.get('text', '')
        result['extracted_text'] = text[:500]
        result['id_numbers'] = self.extract_id_number(text, id_type)

        # Use Tesseract average confidence (0-100) as base, scale to 0-1
        tesseract_conf = float(extraction.get('avg_confidence', 0)) / 100.0
        # Rule-based boost
        rule = 0.0
        if result['id_numbers']:
            rule += 0.35
        if len(text) > 100:
            rule += 0.25
        # Blend: weight Tesseract confidence heavily when it's meaningful
        if tesseract_conf > 0.1:
            confidence = 0.6 * tesseract_conf + 0.4 * min(rule + 0.2, 1.0)
        else:
            confidence = rule + 0.2
        confidence = min(1.0, confidence)

        # Optional validation against user_data
        if user_data:
            validation = {'id_number_match': False, 'name_match': False}
            user_id_raw = (user_data.get('id_number') or '').strip()
            user_id_norm = self._normalize_id_for_match(user_id_raw)
            user_name = (user_data.get('full_name') or '').strip().upper()
            text_upper = text.upper()
            text_upper_no_space = re.sub(r'\s+', '', text_upper)

            # ID number: match with normalized form (strip DL/ID prefix), or containment
            if user_id_norm:
                for extracted_id in result['id_numbers']:
                    ext_norm = self._normalize_id_for_match(extracted_id)
                    if user_id_norm == ext_norm:
                        validation['id_number_match'] = True
                        break
                    if user_id_norm in ext_norm or ext_norm in user_id_norm:
                        validation['id_number_match'] = True
                        break

            # Name: flexible match — "FN"/"First name", "LN"/"Last name", or full name anywhere
            if user_name:
                name_parts = [p for p in re.split(r'[\s,.-]+', user_name) if len(p) > 1]
                if not name_parts:
                    validation['name_match'] = user_name[:8] in text_upper
                else:
                    name_no_space = ''.join(name_parts)
                    # Direct full name (with or without spaces)
                    if name_no_space in text_upper_no_space:
                        validation['name_match'] = True
                    elif any(name_no_space in re.sub(r'\s+', '', line) for line in text_upper.splitlines()):
                        validation['name_match'] = True
                    else:
                        # First/last or any two parts appear (e.g. FN ABEBE, LN KEBEDE or "ABEBE KEBEDE")
                        matches = sum(1 for p in name_parts[:4] if p in text_upper)
                        validation['name_match'] = (
                            matches >= min(2, len(name_parts)) or
                            (len(name_parts) == 1 and name_parts[0] in text_upper) or
                            user_name[:10].replace(' ', '') in text_upper_no_space
                        )
            result['validation'] = validation
            # If both ID and name matched, boost confidence (watermarks can lower Tesseract score)
            if validation.get('id_number_match') and validation.get('name_match') and confidence < 0.6:
                confidence = min(0.6, confidence + 0.15)
        result['confidence'] = round(confidence, 2)
        result['success'] = confidence >= 0.3

        return result
