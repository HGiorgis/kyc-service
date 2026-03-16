from django.db import models
from django.conf import settings
from django.utils import timezone
import secrets
import hashlib
from datetime import timedelta

class APIKey(models.Model):
    """API Key for external systems to access KYC service"""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='api_key',
        limit_choices_to={'is_active': True}
    )
    
    name = models.CharField(max_length=100, help_text="Name for this API key")
    key = models.CharField(max_length=64, unique=True, editable=False)
    key_preview = models.CharField(max_length=8, editable=False)
    key_hash = models.CharField(max_length=128, editable=False)  # Store hash for verification
    
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Usage tracking
    last_used_at = models.DateTimeField(null=True, blank=True)
    total_requests = models.IntegerField(default=0)
    
    # Rate limiting
    requests_today = models.IntegerField(default=0)
    last_request_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.key:
            # Generate API key
            self.key = secrets.token_urlsafe(32)
            self.key_preview = self.key[:8] + '...'
            # Store hash for secure verification
            self.key_hash = hashlib.sha256(self.key.encode()).hexdigest()
            
            # Set expiry to 1 year from now
            if not self.expires_at:
                self.expires_at = timezone.now() + timedelta(days=365)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.email} - {self.key_preview}"
        
    def validate_key(self, provided_key):
        """Validate provided API key"""
        if not self.is_active:
            return False, "API key is inactive"
        
        if self.expires_at and self.expires_at < timezone.now():
            return False, "API key has expired"
        
        # Secure comparison using hash
        provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()
        if not secrets.compare_digest(self.key_hash, provided_hash):
            return False, "Invalid API key"
        
        return True, "Valid"
    
    def record_usage(self):
        """Record API usage"""
        self.total_requests += 1
        self.last_used_at = timezone.now()
        
        # Reset daily counter if new day
        today = timezone.now().date()
        if self.last_request_date != today:
            self.requests_today = 1
            self.last_request_date = today
        else:
            self.requests_today += 1
        
        self.save(update_fields=['total_requests', 'last_used_at', 
                                'requests_today', 'last_request_date'])


class APIKeyLog(models.Model):
    """Log all API requests"""
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE, related_name='logs')
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField()
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    response_time = models.FloatField(help_text="Response time in seconds")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['api_key', '-timestamp']),
        ]