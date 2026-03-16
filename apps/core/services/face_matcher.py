import cv2
import numpy as np
import face_recognition
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class FaceMatcher:
    """Real face matching using face_recognition library."""
    # Max dimension for face images (reduce RAM on Render ~512MB)
    MAX_FACE_PIXELS = 800

    def __init__(self, tolerance=0.6):
        self.tolerance = tolerance

    def _load_image_small(self, image_path):
        """Load image and resize to max MAX_FACE_PIXELS to save memory."""
        img = cv2.imread(image_path)
        if img is None:
            return None
        h, w = img.shape[:2]
        scale = min(1.0, self.MAX_FACE_PIXELS / max(w, h))
        if scale < 1.0:
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    def compare_faces(self, id_image_path, selfie_image_path):
        """
        Compare face from ID with selfie
        Returns: dict with score and details
        """
        try:
            id_image = self._load_image_small(id_image_path)
            selfie_image = self._load_image_small(selfie_image_path)
            if id_image is None or selfie_image is None:
                return {
                    'score': 0.0,
                    'match': False,
                    'face_detected': False,
                    'message': 'Failed to load image'
                }
            
            # Get face encodings
            id_face_encodings = face_recognition.face_encodings(id_image)
            selfie_face_encodings = face_recognition.face_encodings(selfie_image)
            
            # Check if faces detected
            if len(id_face_encodings) == 0:
                return {
                    'score': 0.0,
                    'match': False,
                    'face_detected': False,
                    'message': 'No face detected in ID image'
                }
            
            if len(selfie_face_encodings) == 0:
                return {
                    'score': 0.0,
                    'match': False,
                    'face_detected': False,
                    'message': 'No face detected in selfie'
                }
            
            # Use the first face from each image
            id_encoding = id_face_encodings[0]
            selfie_encoding = selfie_face_encodings[0]
            
            # Compare faces
            matches = face_recognition.compare_faces(
                [id_encoding], 
                selfie_encoding,
                tolerance=self.tolerance
            )
            
            # Calculate face distance (lower = more similar)
            face_distance = face_recognition.face_distance(
                [id_encoding], 
                selfie_encoding
            )[0]
            
            # Convert distance to similarity score (0-1)
            # distance of 0 = perfect match (score 1.0)
            # distance of 0.6 = threshold (score 0.4)
            similarity_score = max(0, 1 - (face_distance / self.tolerance))
            
            # Get face locations for additional info
            id_face_locations = face_recognition.face_locations(id_image)
            selfie_face_locations = face_recognition.face_locations(selfie_image)
            
            result = {
                'score': round(float(similarity_score), 3),
                'match': bool(matches[0]),
                'face_distance': round(float(face_distance), 3),
                'face_detected': True,
                'id_faces_found': len(id_face_encodings),
                'selfie_faces_found': len(selfie_face_encodings),
                'message': 'Faces compared successfully'
            }
            
            # Add face location info
            if id_face_locations:
                top, right, bottom, left = id_face_locations[0]
                result['id_face_size'] = (bottom - top) * (right - left)
            
            if selfie_face_locations:
                top, right, bottom, left = selfie_face_locations[0]
                result['selfie_face_size'] = (bottom - top) * (right - left)
            
            logger.info(f"Face match result: {result['score']} - Match: {result['match']}")
            return result
            
        except Exception as e:
            logger.error(f"Face matching error: {str(e)}")
            return {
                'score': 0.0,
                'match': False,
                'face_detected': False,
                'error': str(e),
                'message': f'Face matching failed: {str(e)}'
            }
    
    def extract_face_quality(self, image_path):
        """Extract face quality metrics (uses resized image to save memory)."""
        try:
            image = self._load_image_small(image_path)
            if image is None:
                return {'face_present': False, 'quality_score': 0.0}
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                return {
                    'face_present': False,
                    'quality_score': 0.0
                }
            
            # Get first face
            top, right, bottom, left = face_locations[0]
            face_image = image[top:bottom, left:right]
            
            # Calculate face quality based on size and clarity
            face_size = (bottom - top) * (right - left)
            
            # Convert to grayscale for clarity check
            if len(face_image.shape) == 3:
                gray = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
            else:
                gray = face_image
            
            # Calculate Laplacian variance (blur detection)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Normalize scores
            size_score = min(1.0, face_size / (500 * 500))  # Max expected size
            clarity_score = min(1.0, laplacian_var / 100)
            
            quality_score = (size_score * 0.5 + clarity_score * 0.5)
            
            return {
                'face_present': True,
                'face_count': len(face_locations),
                'face_size': face_size,
                'size_score': round(size_score, 3),
                'clarity_score': round(clarity_score, 3),
                'quality_score': round(quality_score, 3)
            }
            
        except Exception as e:
            logger.error(f"Face quality check error: {str(e)}")
            return {
                'face_present': False,
                'quality_score': 0.0,
                'error': str(e)
            }