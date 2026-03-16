import cv2
import numpy as np
import face_recognition
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class FaceMatcher:
    """Real face matching using face_recognition library"""
    
    def __init__(self, tolerance=0.6):
        """
        Initialize face matcher
        tolerance: Lower = stricter matching (0.6 is default)
        """
        self.tolerance = tolerance
    
    def compare_faces(self, id_image_path, selfie_image_path):
        """
        Compare face from ID with selfie
        Returns: dict with score and details
        """
        try:
            # Load images
            id_image = face_recognition.load_image_file(id_image_path)
            selfie_image = face_recognition.load_image_file(selfie_image_path)
            
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
        """
        Extract face quality metrics
        """
        try:
            image = face_recognition.load_image_file(image_path)
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