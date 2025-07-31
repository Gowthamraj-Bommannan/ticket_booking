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
    AlreadyExistsMessage,
    UserMessage,
    GeneralMessage,
    TrainMessage,
    StationMessage,
    RouteMessage,
    PaymentMessage,
    BookingMessage,
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


class InvalidCredentialsException(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = UserMessage.INVALID_CREDENTIALS
    default_code = "invalid_credentials_exception"


class InvalidOTPException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = UserMessage.INVALID_OTP
    default_code = "invalid_otp"


class UnauthorizedAccessException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You don't have permission to perform this action."
    default_code = "unauthorized_access"


class InvalidInputException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = GeneralMessage.INVALID_INPUT
    default_code = "invalid_input"

# ---------- TRAIN EXCEPTIONS ----------
class TrainNotFoundException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = TrainMessage.TRAIN_NOT_FOUND
    default_code = "train_not_found"


class TrainAlreadyExistsException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = TrainMessage.TRAIN_ALREADY_EXISTS
    default_code = "train_already_exists"


class TrainAlreadyInactiveException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = TrainMessage.TRAIN_ALREADY_INACTIVE
    default_code = "train_already_inactive"


class TrainAlreadyActiveException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = TrainMessage.TRAIN_ALREADY_ACTIVE
    default_code = "train_already_active"


class TrainInactiveException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = TrainMessage.TRAIN_INACTIVE_CANNOT_ACCESS
    default_code = "train_inactive"


# ---------- STATION EXCEPTIONS ----------
class StationNotFoundException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = StationMessage.STATION_NOT_FOUND
    default_code = "station_not_found"


class StationAlreadyExistsException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = StationMessage.STATION_ALREADY_EXISTS
    default_code = "station_already_exists"


class StationAlreadyActiveException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = StationMessage.STATION_ALREADY_ACTIVE
    default_code = "station_already_active"


class StationMasterExistsException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = StationMessage.STATION_MASTER_EXISTS
    default_code = "station_master_exists"


class ScheduleAlreadyExists(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = TrainMessage.SCHEDULE_ALREADY_EXISTS
    default_code = "station_master_exists"


class ScheduleNotFoundException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = TrainMessage.TRAIN_SCHEDULE_NOT_FOUND
    default_code = "route_edge_not_found"


# ---------- ROUTE/STOP EXCEPTIONS ----------
class RouteNotFoundException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = RouteMessage.ROUTE_EDGE_NOT_FOUND
    default_code = "route_edge_not_found"


class RouteAlreadyExistsException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = RouteMessage.ROUTE_EDGE_ALREADY_EXISTS
    default_code = "route_edge_already_exists"


class RouteInvalidInputException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = RouteMessage.ROUTE_EDGE_INVALID_INPUT
    default_code = "route_edge_invalid_input"


class RouteFromAndToSameException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = RouteMessage.ROUTE_EDGE_FROM_AND_TO_SAME
    default_code = "route_edge_from_and_to_same"


class RouteInvalidDistanceException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = RouteMessage.ROUTE_EDGE_INVALID_DISTANCE
    default_code = "route_edge_invalid_distance"


class RoutePermissionDeniedException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "route_permission_denied"


class RouteUnidrectionalException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A unidirectional edge in this direction already exists."
    default_code = "unidirectional_route"


class RouteStopsNotFoundException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Train should have atleast one stop."
    default_code = "no_stops_found"


# ---------- PAYMENT EXCEPTIONS ----------
class PaymentFailedException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = PaymentMessage.PAYMENT_FAILED
    default_code = "payment_failed"


class PaymentAlreadySuccessException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = PaymentMessage.PAYMENT_ALREADY_SUCCESS
    default_code = "payment_already_success"


class PaymentNotFoundException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = PaymentMessage.PAYMENT_NOT_FOUND
    default_code = "payment_not_found"


class InvalidPaymentMethodException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = PaymentMessage.INVALID_PAYMENT_METHOD
    default_code = "invalid_payment_method"


class PaymentAmountMismatchException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = PaymentMessage.PAYMENT_AMOUNT_MISMATCH
    default_code = "payment_amount_mismatch"


class PaymentGatewayErrorException(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = PaymentMessage.PAYMENT_GATEWAY_ERROR
    default_code = "payment_gateway_error"


class PaymentPendingException(APIException):
    status_code = status.HTTP_202_ACCEPTED
    default_detail = PaymentMessage.PAYMENT_PENDING
    default_code = "payment_pending"


class PaymentRefundInitiatedException(APIException):
    status_code = status.HTTP_200_OK
    default_detail = PaymentMessage.PAYMENT_REFUND_INITIATED
    default_code = "payment_refund_initiated"


class PaymentUnauthorizedException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = PaymentMessage.PAYMENT_UNAUTHORIZED
    default_code = "payment_unauthorized"


class PermissionDeniedException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = GeneralMessage.PERMISSION_DENIED
    default_code = "permission_denied"


class PaymentSessionExpiredException(APIException):
    status_code = status.HTTP_408_REQUEST_TIMEOUT
    default_detail = PaymentMessage.PAYMENT_SESSION_EXPIRED
    default_code = "payment_session_expired"


class FromAndToMustBeDifferent(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = BookingMessage.FROM_AND_TO_MUST_BE_DIFFERENT
    default_code = "from_and_must_be_different"


class AtleastOnePassenegerRequired(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = BookingMessage.ATLEAST_ONE_PASSENGER_REQUIRED
    default_code = "atleast_one_passenger_required"


class NewToStationRequired(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = BookingMessage.NEW_TO_STATION_REQUIRED
    default_code = "new_to_station_required"


class OnlyBookedTicketsExchanged(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = BookingMessage.BOOKED_TICKETS_CAN_BE_EXCHANGED
    default_code = "only_booked_tickets_can_be_exchanged"


class FromAndToStationsRequired(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = BookingMessage.FROM_AND_TO_ARE_REQUIRED
    default_code = "both_from_and_to_stations_are_required"


class BookingUnauthorizedException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = BookingMessage.FORBIDDEN
    default_code = "forbidden"
