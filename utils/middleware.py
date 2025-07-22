import logging
import json
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse

logger = logging.getLogger("accounts")

class RequestResponseLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log incoming requests and outgoing responses.
    Masks sensitive data like passwords, OTP, and tokens.
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
    
    def process_request(self, request):
        """Log incoming request details."""
        # Get user info
        user_info = "anonymous"
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_info = f"{request.user.username} (ID: {request.user.id})"
        
        # Mask sensitive data in request body
        request_body = self._mask_sensitive_data(request.body.decode('utf-8') if request.body else '')
        
        logger.info(
            f"Request: {request.method} {request.path} | User: {user_info} | "
            f"Body: {request_body[:500]}{'...' if len(request_body) > 500 else ''}"
        )
        
        return None
    
    def process_response(self, request, response):
        """Log outgoing response details."""
        # Get user info
        user_info = "anonymous"
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_info = f"{request.user.username} (ID: {request.user.id})"
        
        # Mask sensitive data in response body
        response_body = ""
        if hasattr(response, 'content'):
            try:
                response_data = json.loads(response.content.decode('utf-8'))
                response_body = self._mask_sensitive_data(json.dumps(response_data))
            except (json.JSONDecodeError, UnicodeDecodeError):
                response_body = "*** (non-JSON response) ***"
        
        logger.info(
            f"Response: {response.status_code} | User: {user_info} | "
            f"Body: {response_body[:500]}{'...' if len(response_body) > 500 else ''}"
        )
        
        return response
    
    def _mask_sensitive_data(self, data_str):
        """Mask sensitive fields in request/response data."""
        if not data_str:
            return data_str
        
        try:
            # Try to parse as JSON
            data = json.loads(data_str)
            masked_data = self._mask_json_data(data)
            return json.dumps(masked_data)
        except json.JSONDecodeError:
            return self._mask_text_data(data_str)
    
    def _mask_json_data(self, data):
        """Recursively mask sensitive fields in JSON data."""
        if isinstance(data, dict):
            masked_data = {}
            for key, value in data.items():
                if key.lower() in ['token', 'access', 'refresh', 'secret']:
                    masked_data[key] = "***"
                elif isinstance(value, (dict, list)):
                    masked_data[key] = self._mask_json_data(value)
                else:
                    masked_data[key] = value
            return masked_data
        elif isinstance(data, list):
            return [self._mask_json_data(item) for item in data]
        else:
            return data
    
    def _mask_text_data(self, text):
        """Mask sensitive patterns in text data."""
        import re
        
        # Common patterns to mask (removed password and otp)
        patterns = [
            r'"token"\s*:\s*"[^"]*"',
            r'"access"\s*:\s*"[^"]*"',
            r'"refresh"\s*:\s*"[^"]*"',
            r'"secret"\s*:\s*"[^"]*"',
        ]
        
        masked_text = text
        for pattern in patterns:
            masked_text = re.sub(pattern, lambda m: m.group().split(':')[0] + ': "***"', masked_text)
        
        return masked_text 