from django.db import models


class SystemSettings(models.Model):
    """Singleton-style system settings (one row). Admin can update."""
    # Rate limits (defaults for new users)
    default_daily_limit = models.IntegerField(default=1000)
    default_monthly_limit = models.IntegerField(default=30000)
    # API key
    key_expiry_days = models.IntegerField(default=365)
    require_approval_new_keys = models.BooleanField(default=False)
    # KYC thresholds (0-100 scale in UI, we use 0-1 in verifier)
    approve_threshold = models.IntegerField(default=85)   # percent
    reject_threshold = models.IntegerField(default=40)    # percent
    auto_approve_high_confidence = models.BooleanField(default=True)
    # Images
    max_image_size_mb = models.FloatField(default=5.0)
    allowed_image_formats = models.CharField(max_length=128, default='jpg,jpeg,png,webp')
    # Security
    session_timeout_minutes = models.IntegerField(default=30)
    force_2fa_admin = models.BooleanField(default=False)
    ip_whitelist_enabled = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'System settings'
        verbose_name_plural = 'System settings'

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={})
        return obj

    def allowed_formats_list(self):
        return [x.strip().lower() for x in self.allowed_image_formats.split(',') if x.strip()]
