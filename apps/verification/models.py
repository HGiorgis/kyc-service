from django.db import models
from django.conf import settings  # Add this import
import uuid

class KYCSubmission(models.Model):
    """Main KYC submission model"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('processing', 'Processing'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('flagged', 'Flagged for Review'),
    ]
    
    ID_TYPE_CHOICES = [
        ('kebele', 'Kebele ID'),
        ('passport', 'Passport'),
        ('drivers_license', "Driver's License"),
        ('national_id', 'National ID'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Reference to user in main system (application user_id from API)
    user_id = models.CharField(max_length=100, db_index=True)
    user_email = models.EmailField()
    user_full_name = models.CharField(max_length=255)
    # Django user who submitted (via API or test page)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='kyc_submissions',
    )
    
    # ID Information
    id_type = models.CharField(max_length=20, choices=ID_TYPE_CHOICES)
    id_number = models.CharField(max_length=100)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    confidence_score = models.FloatField(default=0.0)
    
    # Verification results
    verification_data = models.JSONField(default=dict)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Admin who reviewed - FIXED: Use settings.AUTH_USER_MODEL
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Changed from 'auth.User'
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user_full_name} - {self.status}"


def kyc_document_path(instance, filename):
    """Generate file path for KYC documents"""
    ext = filename.split('.')[-1]
    return f"kyc/{instance.submission.user_id}/{instance.document_type}_{instance.id}.{ext}"


class KYCDocument(models.Model):
    """Document images for KYC submission"""
    
    DOCUMENT_TYPES = [
        ('id_front', 'ID Front'),
        ('id_back', 'ID Back'),
        ('selfie', 'Selfie'),
        ('signature', 'Signature'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(KYCSubmission, on_delete=models.CASCADE, related_name='documents')
    
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.ImageField(upload_to=kyc_document_path)
    thumbnail = models.ImageField(upload_to=kyc_document_path, null=True, blank=True)
    
    # Image analysis results
    ocr_text = models.TextField(blank=True)
    face_detected = models.BooleanField(default=False)
    quality_score = models.FloatField(default=0.0)
    processing_errors = models.JSONField(default=list)
    
    metadata = models.JSONField(default=dict)  # Image dimensions, size, etc.
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['submission', 'document_type']
    
    def __str__(self):
        return f"{self.submission.user_full_name} - {self.document_type}"


class VerificationLog(models.Model):
    """Audit log for verification actions"""
    
    ACTION_CHOICES = [
        ('submitted', 'Submitted'),
        ('auto_approved', 'Auto Approved'),
        ('auto_rejected', 'Auto Rejected'),
        ('manual_approved', 'Manual Approved'),
        ('manual_rejected', 'Manual Rejected'),
        ('flagged', 'Flagged'),
        ('updated', 'Updated'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(KYCSubmission, on_delete=models.CASCADE, related_name='logs')
    
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.CharField(max_length=100, null=True, blank=True)  # User ID or 'system'
    
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']