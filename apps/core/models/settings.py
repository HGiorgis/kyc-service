from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class SystemSettings(models.Model):
    """Global system settings"""
    
    # KYC Settings
    auto_approve_threshold = models.FloatField(
        default=0.85,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="KYC submissions above this confidence auto-approve"
    )
    auto_reject_threshold = models.FloatField(
        default=0.40,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="KYC submissions below this confidence auto-reject"
    )
    
    # Image Settings
    max_image_size_mb = models.FloatField(default=5.0, help_text="Maximum image size in MB")
    allowed_image_formats = models.CharField(
        max_length=100,
        default='jpg,jpeg,png',
        help_text="Comma-separated list of allowed formats"
    )
    
    # API Settings
    api_key_expiry_days = models.IntegerField(default=365)
    require_admin_approval = models.BooleanField(default=True)
    
    # Rate Limits
    default_daily_limit = models.IntegerField(default=1000)
    default_monthly_limit = models.IntegerField(default=30000)
    
    # Security
    session_timeout_minutes = models.IntegerField(default=30)
    enable_2fa = models.BooleanField(default=False)
    
    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"
    
    def __str__(self):
        return "System Configuration"
    
    @classmethod
    def get_settings(cls):
        """Get or create settings singleton"""
        settings, created = cls.objects.get_or_create(id=1)
        return settings


class BlacklistEntry(models.Model):
    """Blacklisted entities"""
    
    ENTRY_TYPES = [
        ('id_number', 'ID Number'),
        ('email', 'Email'),
        ('ip_address', 'IP Address'),
        ('phone', 'Phone Number'),
    ]
    
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES)
    value = models.CharField(max_length=255, db_index=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    
    class Meta:
        unique_together = ['entry_type', 'value']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.entry_type}: {self.value}"