from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

class User(AbstractUser):
    """Extended user model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)
    
    # Rate limiting settings (admin controlled)
    daily_request_limit = models.IntegerField(default=1000)
    monthly_request_limit = models.IntegerField(default=30000)
    
    # Usage tracking
    total_api_calls = models.IntegerField(default=0)
    last_api_call = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Fix reverse accessor conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="custom_user_set",
        related_query_name="custom_user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="custom_user_set",
        related_query_name="custom_user",
    )
    
    class Meta:
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.email or self.username
    
    def get_api_key(self):
        """Get user's API key if exists"""
        try:
            return self.api_key
        except:
            return None
    
    def check_rate_limit(self):
        """Check if user has exceeded rate limits"""
        from apps.authentication.models import APIKeyLog
        today = timezone.now().date()
        
        # Count today's requests
        today_requests = APIKeyLog.objects.filter(
            api_key__user=self,
            timestamp__date=today
        ).count()
        
        if today_requests >= self.daily_request_limit:
            return False, f"Daily limit of {self.daily_request_limit} exceeded"
        
        # Count this month's requests
        month_start = timezone.now().replace(day=1)
        month_requests = APIKeyLog.objects.filter(
            api_key__user=self,
            timestamp__gte=month_start
        ).count()
        
        if month_requests >= self.monthly_request_limit:
            return False, f"Monthly limit of {self.monthly_request_limit} exceeded"
        
        return True, "OK"