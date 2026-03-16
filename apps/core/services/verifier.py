import cv2
import numpy as np
from PIL import Image
import os
import re
from datetime import datetime
from .face_matcher import FaceMatcher
from .ocr_service import OCRService
from .fraud_detector import FraudDetector
import logging

logger = logging.getLogger(__name__)

class KYCVerifier:
    """Main KYC verification service with REAL features"""
    
    def __init__(self):
        self.confidence_threshold = 0.7
        self.face_matcher = FaceMatcher(tolerance=0.6)
        self.ocr_service = OCRService()
        self.fraud_detector = FraudDetector()
        try:
            from apps.core.models import SystemSettings
            s = SystemSettings.get_settings()
            self.auto_approve_threshold = s.approve_threshold / 100.0
            self.auto_reject_threshold = s.reject_threshold / 100.0
        except Exception:
            self.auto_approve_threshold = 0.85
            self.auto_reject_threshold = 0.40
        
    def verify_submission(self, submission):
        """
        Run all verification checks on a submission
        Returns: dict with results and confidence score
        """
        try:
            documents = submission.documents.all()
            id_front = None
            id_back = None
            selfie = None
            for doc in documents:
                if doc.document_type == 'id_front':
                    id_front = doc
                elif doc.document_type == 'id_back':
                    id_back = doc
                elif doc.document_type == 'selfie':
                    selfie = doc

            results = {
                'checks': {},
                'overall_confidence': 0.0,
                'status': 'pending',
                'flags': [],
                'fraud_report': None
            }

            if not id_front or not selfie:
                results['flags'].append('Missing required documents')
                results['status'] = 'rejected'
                return results

            if id_front and os.path.exists(id_front.file.path):
                quality_result = self._check_image_quality(id_front.file.path)
                results['checks']['image_quality'] = quality_result
                if quality_result['score'] < 0.5:
                    results['flags'].append('Poor image quality')

            if selfie and os.path.exists(selfie.file.path):
                face_quality = self.face_matcher.extract_face_quality(selfie.file.path)
                results['checks']['face_quality'] = face_quality
                if not face_quality['face_present']:
                    results['flags'].append('No face detected in selfie')
                elif face_quality.get('face_count', 0) > 1:
                    results['flags'].append('Multiple faces detected in selfie')

            if (id_front and selfie and
                os.path.exists(id_front.file.path) and
                os.path.exists(selfie.file.path)):
                face_match = self.face_matcher.compare_faces(
                    id_front.file.path,
                    selfie.file.path
                )
                results['checks']['face_match'] = face_match
                score = face_match.get('score')
                if not face_match.get('face_detected', False):
                    results['flags'].append('Face detection failed')
                elif score is not None and score < 0.6:
                    results['flags'].append("Face match score too low: %s" % score)
                elif score is not None and score > 0.8:
                    results['checks']['face_match']['excellent'] = True

            if id_front and os.path.exists(id_front.file.path):
                ocr_result = self.ocr_service.process_id_document(
                    id_front.file.path,
                    id_type=submission.id_type,
                    user_data={
                        'full_name': submission.user_full_name,
                        'id_number': submission.id_number
                    }
                )
                results['checks']['ocr'] = ocr_result
                if ocr_result.get('confidence', 0) < 0.5:
                    results['flags'].append('OCR confidence too low')
                if ocr_result.get('validation'):
                    validation = ocr_result['validation']
                    if not validation.get('id_number_match'):
                        results['flags'].append('ID number mismatch')
                    if not validation.get('name_match'):
                        results['flags'].append('Name mismatch')

            id_valid = self._validate_id_number(submission.id_type, submission.id_number)
            results['checks']['id_format'] = {'valid': id_valid}
            if not id_valid:
                results['flags'].append('Invalid ID number format')

            fraud_report = self.fraud_detector.analyze_submission(submission)
            results['fraud_report'] = fraud_report
            results['checks']['fraud'] = fraud_report
            if fraud_report['is_fraudulent']:
                results['flags'].extend(fraud_report['flags'])
            
            # Always calculate overall confidence (so UI shows real score even when rejected)
            scores = []
            
            # Image quality score (20%)
            if results['checks'].get('image_quality', {}).get('score') is not None:
                scores.append(results['checks']['image_quality']['score'] * 0.2)
            else:
                scores.append(0.0)
            
            # Face match score (40%)
            if results['checks'].get('face_match', {}).get('score') is not None:
                face_score = results['checks']['face_match']['score']
                scores.append(face_score * 0.4)
            else:
                scores.append(0.0)
            
            # OCR confidence (30%)
            if results['checks'].get('ocr', {}).get('confidence') is not None:
                ocr_conf = results['checks']['ocr']['confidence']
                scores.append(ocr_conf * 0.3)
            else:
                scores.append(0.0)
            
            # Fraud check (10% - inverted risk)
            if fraud_report:
                risk_score = 1 - fraud_report['overall_risk_score']
                scores.append(risk_score * 0.1)
            else:
                scores.append(0.1)
            
            results['overall_confidence'] = round(float(sum(scores)), 4)

            if fraud_report['is_fraudulent'] and fraud_report['recommended_action'] == 'block':
                results['status'] = 'rejected'
                results['rejection_reason'] = 'Fraud detection triggered'
                results['summary'] = self._generate_summary(results)
                return results

            conf = results['overall_confidence']
            if conf >= self.auto_approve_threshold:
                results['status'] = 'approved'
            elif conf < self.auto_reject_threshold:
                results['status'] = 'rejected'
                if not results.get('rejection_reason'):
                    results['rejection_reason'] = 'Confidence below reject threshold'
            else:
                results['status'] = 'flagged'

            results['summary'] = self._generate_summary(results)
            logger.info("Verification complete: %s with confidence %s" % (results['status'], results['overall_confidence']))
            return results
            
        except Exception as e:
            logger.error(f"Verification error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'overall_confidence': 0.0,
                'flags': ['System error during verification']
            }
    
    def _generate_summary(self, results):
        """Generate human-readable summary"""
        summary = []
        
        if results['checks'].get('face_match', {}).get('match'):
            summary.append("Face match successful")
        elif results['checks'].get('face_match', {}).get('score', 0) > 0.6:
            summary.append("Face match acceptable")
        else:
            summary.append("Face match failed")
        
        if results['checks'].get('ocr', {}).get('validation', {}).get('id_number_match'):
            summary.append("ID number verified")
        else:
            summary.append("ID number mismatch")
        
        if results['fraud_report'] and not results['fraud_report']['is_fraudulent']:
            summary.append("No fraud detected")
        elif results['fraud_report']:
            summary.append(f"Fraud risk: {results['fraud_report']['overall_risk_score']:.2f}")
        
        return summary
    
    def _check_image_quality(self, image_path):
        """Check image quality metrics"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return {'score': 0, 'error': 'Cannot read image'}
            
            # Check resolution
            height, width = img.shape[:2]
            resolution_score = min(1.0, (height * width) / (1000 * 1000))
            
            # Check brightness
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            brightness_score = 1.0 - abs(brightness - 128) / 128
            
            # Check blur
            laplacian = cv2.Laplacian(gray, cv2.CV_64F).var()
            blur_score = min(1.0, laplacian / 100)
            
            # Combined score
            final_score = (resolution_score * 0.3 + brightness_score * 0.3 + blur_score * 0.4)
            
            return {
                'score': round(float(final_score), 2),
                'resolution': f"{width}x{height}",
                'brightness': round(float(brightness), 2),
                'sharpness': round(float(blur_score), 2)
            }
        except Exception as e:
            return {'score': 0, 'error': str(e)}
    
    def _validate_id_number(self, id_type, id_number):
        """Validate ID number format"""
        patterns = {
            'kebele': r'^\d{6,12}$',
            'passport': r'^[A-Z0-9]{6,12}$',
            'drivers_license': r'^[A-Z]{1,2}\d{5,10}$',
            'national_id': r'^\d{10,16}$'
        }
        
        pattern = patterns.get(id_type, r'^.*$')
        return bool(re.match(pattern, str(id_number)))