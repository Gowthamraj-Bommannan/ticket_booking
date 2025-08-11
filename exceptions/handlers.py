from rest_framework.exceptions import APIException
from rest_framework import status
from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.core.exceptions import (
    ObjectDoesNotExist,
    ValidationError as DjangoValidationError,
)
from rest_framework.exceptions import ValidationError as DRFValidationError
from utils.constants import (
    GeneralMessage,
)
import logging

logger = logging.getLogger("payment")


def custom_exception_handler(exc, context):
    # Handle Django's DoesNotExist as 404
    if isinstance(exc, ObjectDoesNotExist):
        return Response(
            {"success": False, "error": "Not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Handle Django and DRF validation errors as 400
    if isinstance(exc, (DjangoValidationError, DRFValidationError)):
        return Response(
            {
                "success": False,
                "error": exc.detail if hasattr(exc, "detail") else str(exc),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Handle all APIException (including your custom ones)
    if isinstance(exc, APIException):
        detail = exc.detail if hasattr(exc, "detail") else str(exc)
        code = (
            exc.status_code
            if hasattr(exc, "status_code")
            else status.HTTP_400_BAD_REQUEST
        )
        return Response({"success": False, "error": detail}, status=code)

    # Fallback to DRF's default handler (for AuthenticationFailed, NotAuthenticated, etc.)
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {"success": False, "error": response.data}
        return response

    # Catch-all for any other exception
    return Response(
        {
            "success": False,
            "error": "An unexpected error occurred.",
            "detail": str(exc),
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

class AlreadyExistsException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "already_exists"


class NotFoundException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "not_found"


class PermissionDeniedException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "permission_denied"


class UnauthorizedAccessException(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "unauthorized_access"


class InvalidInputException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = GeneralMessage.INVALID_INPUT
    default_code = "invalid_input"

class MethodNotAllowedException(APIException):
    status_code = status.HTTP_405_METHOD_NOT_ALLOWED
    default_code = "method_not_allowed"

class TimeoutException(APIException):
    status_code = status.HTTP_408_REQUEST_TIMEOUT
    default_code = "timeout"

