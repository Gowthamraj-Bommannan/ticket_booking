import logging
import uuid
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("LOGGING")


class RequestResponseLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log incoming requests and outgoing responses.
    Masks sensitive data like passwords, OTP, and tokens.
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response

    def process_request(self, request):
        """Log the basic info of the incoming request."""
        trace_id = str(uuid.uuid4())
        request.trace_id = trace_id
        user = getattr(request, "user", None)
        user_info = (
            f"{user.username} (ID: {user.id})"
            if user and user.is_authenticated
            else "anonymous"
        )

        logger.info(
            f"Trace ID: {trace_id} | Request: {request.method} {request.path} | User: {user_info}"
        )
        return None

    def process_response(self, request, response):
        """Log the response status for the same request."""
        trace_id = getattr(request, "trace_id", "N/A")
        user = getattr(request, "user", None)
        user_info = (
            f"{user.username} (ID: {user.id})"
            if user and user.is_authenticated
            else "anonymous"
        )

        logger.info(
            f"Trace ID: {trace_id} | Response: {response.status_code} | User: {user_info}"
        )
        return response
