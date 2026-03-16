# apps/api/authentication.py
from rest_framework import authentication
from rest_framework import exceptions
from apps.authentication.models import APIKey
from django.utils import timezone
import hashlib
import secrets

class APIKeyAuthentication(authentication.BaseAuthentication):
    """Custom authentication using API keys"""
    
    def authenticate(self, request):
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return None
        
        try:
            # Find the API key - need to check all active keys
            all_keys = APIKey.objects.filter(is_active=True)
            key_obj = None
            
            for key in all_keys:
                is_valid, _ = key.validate_key(api_key)
                if is_valid:
                    key_obj = key
                    break
            
            if not key_obj:
                raise exceptions.AuthenticationFailed('Invalid API key')
            
            # Check if expired
            if key_obj.expires_at and key_obj.expires_at < timezone.now():
                raise exceptions.AuthenticationFailed('API key has expired')
            
            # Do not record_usage here — views check rate limit first, then record
            return (key_obj.user, key_obj)
            
        except Exception as e:
            raise exceptions.AuthenticationFailed(str(e))