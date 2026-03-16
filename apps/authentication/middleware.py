from django.utils import timezone
from django.http import JsonResponse
from .models import APIKey

class RateLimitMiddleware:
    """Check rate limits for API requests"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only check for API paths
        if not request.path.startswith('/api/'):
            return self.get_response(request)
        
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return self.get_response(request)
        
        try:
            # Find the API key
            key_obj = APIKey.objects.get(is_active=True)
            is_valid, _ = key_obj.validate_key(api_key)
            
            if is_valid:
                # Check rate limits
                can_proceed, message = key_obj.user.check_rate_limit()
                if not can_proceed:
                    return JsonResponse(
                        {'error': message, 'code': 'rate_limit_exceeded'},
                        status=429
                    )
        except:
            pass
        
        return self.get_response(request)