from django.utils import timezone
from datetime import timedelta
import hashlib
import logging
from apps.verification.models import KYCSubmission, KYCDocument

logger = logging.getLogger(__name__)

class FraudDetector:
    """Fraud detection system"""
    
    def __init__(self):
        # Suspicious patterns
        self.suspicious_id_patterns = [
            r'^0+$',  # All zeros
            r'^123456',  # Sequential
            r'^987654',  # Sequential
            r'^111111',  # Repeated
            r'^222222',
        ]
        
        # Blacklist (could be loaded from database)
        self.blacklisted_id_numbers = set()
        self.blacklisted_emails = set()
        self.blacklisted_ips = set()
    
    def check_duplicate_submission(self, user_id, id_number, exclude_submission_id=None):
        """
        Check if user already has pending/approved submission (excluding current submission).
        """
        qs = KYCSubmission.objects.filter(
            user_id=user_id,
            status__in=['pending', 'processing', 'approved']
        )
        if exclude_submission_id:
            qs = qs.exclude(pk=exclude_submission_id)
        existing = qs.exists()
        
        if existing:
            return {
                'is_fraud': True,
                'risk_score': 1.0,
                'reason': 'User already has active submission',
                'action': 'block'
            }
        
        # Check for same ID number used by different users
        same_id_submissions = KYCSubmission.objects.filter(
            id_number=id_number,
            status='approved'
        ).exclude(user_id=user_id)
        
        if same_id_submissions.exists():
            return {
                'is_fraud': True,
                'risk_score': 0.9,
                'reason': 'ID number already used by another user',
                'action': 'flag',
                'existing_submissions': same_id_submissions.count()
            }
        
        return {
            'is_fraud': False,
            'risk_score': 0.0,
            'reason': None
        }
    
    def check_rate_anomaly(self, ip_address, user_id=None):
        """
        Check for suspicious submission rates
        """
        time_threshold = timezone.now() - timedelta(hours=1)
        
        # Check submissions from same IP
        ip_submissions = KYCSubmission.objects.filter(
            ip_address=ip_address,
            created_at__gte=time_threshold
        ).count()
        
        if ip_submissions > 12:  # More than 12 submissions per hour from same IP
            return {
                'is_fraud': True,
                'risk_score': 0.7,
                'reason': f'High submission rate from IP: {ip_submissions} submissions/hour',
                'action': 'flag'
            }
        
        if user_id:
            # Check user's submission history
            user_submissions = KYCSubmission.objects.filter(
                user_id=user_id,
                created_at__gte=time_threshold
            ).count()
            
            if user_submissions > 3:
                return {
                    'is_fraud': True,
                    'risk_score': 0.6,
                    'reason': f'User submitted {user_submissions} times in last hour',
                    'action': 'flag'
                }
        
        return {
            'is_fraud': False,
            'risk_score': 0.0,
            'reason': None
        }
    
    def check_image_authenticity(self, submission):
        """
        Check for image tampering or duplicates
        """
        issues = []
        
        # Get all documents
        documents = submission.documents.all()
        
        # Check for duplicate images across submissions
        for doc in documents:
            # Calculate image hash
            try:
                with open(doc.file.path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                
                # Check if same image used in other submissions
                from apps.verification.models import KYCDocument
                duplicate_images = KYCDocument.objects.exclude(
                    submission=submission
                ).filter(
                    file__icontains=doc.file.name.split('/')[-1][:20]  # Partial match
                ).count()
                
                if duplicate_images > 0:
                    issues.append(f"Document {doc.document_type} appears in other submissions")
                    
            except Exception as e:
                logger.error(f"Image hash error: {str(e)}")
        
        if issues:
            return {
                'is_fraud': True,
                'risk_score': 0.5,
                'issues': issues,
                'action': 'flag'
            }
        
        return {
            'is_fraud': False,
            'risk_score': 0.0,
            'issues': []
        }
    
    def check_blacklist(self, id_number=None, email=None, ip_address=None):
        """
        Check against blacklist
        """
        matches = []
        
        if id_number and id_number in self.blacklisted_id_numbers:
            matches.append('id_number')
        
        if email and email in self.blacklisted_emails:
            matches.append('email')
        
        if ip_address and ip_address in self.blacklisted_ips:
            matches.append('ip_address')
        
        if matches:
            return {
                'is_fraud': True,
                'risk_score': 1.0,
                'matches': matches,
                'action': 'block'
            }
        
        return {
            'is_fraud': False,
            'risk_score': 0.0
        }
    
    def analyze_submission(self, submission):
        """
        Complete fraud analysis for a submission
        """
        fraud_report = {
            'is_fraudulent': False,
            'overall_risk_score': 0.0,
            'checks': {},
            'flags': [],
            'recommended_action': 'accept'  # accept, flag, block
        }
        
        # Check duplicate (exclude current submission so test run doesn't flag itself)
        duplicate_check = self.check_duplicate_submission(
            submission.user_id,
            submission.id_number,
            exclude_submission_id=submission.pk,
        )
        fraud_report['checks']['duplicate'] = duplicate_check
        if duplicate_check['is_fraud']:
            fraud_report['flags'].append(duplicate_check['reason'])
        
        # Check rate anomaly
        rate_check = self.check_rate_anomaly(
            submission.ip_address,
            submission.user_id
        )
        fraud_report['checks']['rate'] = rate_check
        if rate_check['is_fraud']:
            fraud_report['flags'].append(rate_check['reason'])
        
        # Check image authenticity
        image_check = self.check_image_authenticity(submission)
        fraud_report['checks']['image'] = image_check
        if image_check['is_fraud']:
            fraud_report['flags'].extend(image_check.get('issues', []))
        
        # Check blacklist
        blacklist_check = self.check_blacklist(
            id_number=submission.id_number,
            email=submission.user_email,
            ip_address=submission.ip_address
        )
        fraud_report['checks']['blacklist'] = blacklist_check
        if blacklist_check['is_fraud']:
            fraud_report['flags'].append('Found in blacklist')
        
        # Calculate overall risk score (weighted average)
        total_weight = 0
        weighted_score = 0
        
        weights = {
            'duplicate': 0.4,
            'rate': 0.2,
            'image': 0.3,
            'blacklist': 0.1
        }
        
        for check_name, check_result in fraud_report['checks'].items():
            if check_result.get('risk_score'):
                weighted_score += check_result['risk_score'] * weights.get(check_name, 0.1)
                total_weight += weights.get(check_name, 0.1)
        
        if total_weight > 0:
            fraud_report['overall_risk_score'] = weighted_score / total_weight
        
        # Determine action
        if fraud_report['overall_risk_score'] > 0.8:
            fraud_report['recommended_action'] = 'block'
            fraud_report['is_fraudulent'] = True
        elif fraud_report['overall_risk_score'] > 0.4:
            fraud_report['recommended_action'] = 'flag'
            fraud_report['is_fraudulent'] = True
        else:
            fraud_report['recommended_action'] = 'accept'
        
        return fraud_report
    
    def add_to_blacklist(self, id_number=None, email=None, ip_address=None, reason=""):
        """
        Add entries to blacklist
        """
        if id_number:
            self.blacklisted_id_numbers.add(id_number)
            # Also save to database
            # BlacklistEntry.objects.create(type='id_number', value=id_number, reason=reason)
        
        if email:
            self.blacklisted_emails.add(email)
            # BlacklistEntry.objects.create(type='email', value=email, reason=reason)
        
        if ip_address:
            self.blacklisted_ips.add(ip_address)
            # BlacklistEntry.objects.create(type='ip', value=ip_address, reason=reason)
        
        logger.info(f"Added to blacklist: ID:{id_number}, Email:{email}, IP:{ip_address}")