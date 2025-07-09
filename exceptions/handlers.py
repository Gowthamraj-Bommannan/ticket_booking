from rest_framework.exceptions import APIException
from rest_framework import status
from rest_framework.views import exception_handler
from rest_framework.response import Response
from utils.constants import AlreadyExistsMessage, UserMessage, GeneralMessage, TrainMessage, StationMessage, RouteMessage


def custom_exception_handler(exc, context):
    # Handle our custom exceptions first
    if isinstance(exc, (EmailAlreadyExists, UsernameAlreadyExists, 
                        MobileNumberAlreadyExists, InvalidCredentials,
                        InvalidOTPException, UnauthorizedAccessException,
                        UserNotFoundException, DuplicateEmailException)):
        return Response({
            'success': False,
            'error': exc.default_detail
        }, status=exc.status_code)
    
    elif isinstance(exc, (AlreadyExists, NotFound, 
                          InvalidInput, QueryParameterMissing)):
        return Response({
            'success': False,
            'error': str(exc.detail) if hasattr(exc, 'detail') else str(exc)
        }, status=exc.status_code)
    
    elif isinstance(exc, (
        TrainNotFoundException, TrainAlreadyExistsException,
        TrainAlreadyInactiveException, TrainAlreadyActiveException,
        TrainInactiveException, StationNotFoundException,
        StationAlreadyExistsException, StationAlreadyInactiveException,
        StationAlreadyActiveException, StationInactiveException,
        RouteNotFoundException, RouteAlreadyExistsException, RouteAlreadyDefinedException,
        RouteStopNotFoundException, RouteStopAlreadyExistsException, RouteStopDuplicateSequenceException,
        RouteStopInvalidSequenceException, RouteStopDepartureMustGreaterException, RouteStopStationInactiveException,
        RouteStopTrainInactiveException, RouteStopInactiveException, RouteStopSequenceConflictException,
        RouteStopStationConflictException, RouteStopInvalidInputException
    )):
        return Response({
            'success': False,
            'error': exc.default_detail,
            'code': exc.default_code
        }, status=exc.status_code)

    # Handle DRF exceptions
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            'success': False,
            'error': response.data
        }
        return response
    
    # Handle unexpected exceptions
    return Response({
        'success': False, 
        'error': 'An unexpected error occurred.',
        'detail': str(exc)
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmailAlreadyExists(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = AlreadyExistsMessage.EMAIL_ALREADY_EXISTS
    default_code = 'email_exists'

class DuplicateEmailException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = AlreadyExistsMessage.EMAIL_ALREADY_EXISTS
    default_code = 'duplicate_email'

class UsernameAlreadyExists(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = AlreadyExistsMessage.USERNAME_ALREADY_EXISTS
    default_code = 'username_exists'

class MobileNumberAlreadyExists(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = AlreadyExistsMessage.MOBILE_ALREADY_EXISTS
    default_code = 'mobile_number_exists'

class InvalidCredentials(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = UserMessage.INVALID_CREDENTIALS
    default_code = 'invalid_credentials'
    
    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
        super().__init__(detail, code)

class InvalidCredentialsException(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = UserMessage.INVALID_CREDENTIALS
    default_code = 'invalid_credentials_exception'
    
    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
        super().__init__(detail, code)

class InvalidOTPException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = UserMessage.INVALID_OTP
    default_code = 'invalid_otp'

class UnauthorizedAccessException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You don't have permission to perform this action."
    default_code = 'unauthorized_access'

class UserNotFoundException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = UserMessage.USER_NOT_FOUND
    default_code = 'user_not_found'

class AlreadyExists(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = 'already_exists'

class InvalidInput(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'invalid_input'
    
    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = 'Invalid input provided.'
        super().__init__(detail, code)

class QueryParameterMissing(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = GeneralMessage.QUERY_MISSING
    default_code = 'missing_query'


class NotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'not_found'

# ---------- TRAIN EXCEPTIONS ----------
class TrainNotFoundException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = TrainMessage.TRAIN_NOT_FOUND
    default_code = 'train_not_found'

class TrainAlreadyExistsException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = TrainMessage.TRAIN_ALREADY_EXISTS
    default_code = 'train_already_exists'

class TrainAlreadyInactiveException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = TrainMessage.TRAIN_ALREADY_INACTIVE
    default_code = 'train_already_inactive'

class TrainAlreadyActiveException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = TrainMessage.TRAIN_ALREADY_ACTIVE
    default_code = 'train_already_active'

class TrainInactiveException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = TrainMessage.TRAIN_INACTIVE_CANNOT_ACCESS
    default_code = 'train_inactive'

# ---------- STATION EXCEPTIONS ----------
class StationNotFoundException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = StationMessage.STATION_NOT_FOUND
    default_code = 'station_not_found'

class StationAlreadyExistsException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = StationMessage.STATION_ALREADY_EXISTS
    default_code = 'station_already_exists'

class StationAlreadyInactiveException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = StationMessage.STATION_ALREADY_INACTIVE
    default_code = 'station_already_inactive'

class StationAlreadyActiveException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = StationMessage.STATION_ALREADY_ACTIVE
    default_code = 'station_already_active'

class StationInactiveException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = StationMessage.STATION_INACTIVE_CANNOT_ACCESS
    default_code = 'station_inactive'

# ---------- ROUTE/STOP EXCEPTIONS ----------
class RouteNotFoundException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = RouteMessage.ROUTE_NOT_FOUND
    default_code = 'route_not_found'

class RouteAlreadyExistsException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = RouteMessage.ROUTE_ALREADY_EXISTS
    default_code = 'route_already_exists'

class RouteAlreadyDefinedException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = RouteMessage.ROUTE_ALREADY_DEFINED
    default_code = 'route_already_defined'

class RouteStopNotFoundException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = RouteMessage.ROUTE_STOP_NOT_FOUND
    default_code = 'route_stop_not_found'

class RouteStopAlreadyExistsException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = RouteMessage.ROUTE_STOP_ALREADY_EXISTS
    default_code = 'route_stop_already_exists'

class RouteStopDuplicateSequenceException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = RouteMessage.ROUTE_STOP_DUPLICATE_SEQUENCE
    default_code = 'route_stop_duplicate_sequence'

class RouteStopInvalidSequenceException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = RouteMessage.ROUTE_STOP_INVALID_SEQUENCE
    default_code = 'route_stop_invalid_sequence'

class RouteStopDepartureMustGreaterException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = RouteMessage.ROUTE_STOP_DEPARTURE_MUST_GREATER
    default_code = 'route_stop_departure_must_greater'

class RouteStopStationInactiveException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = RouteMessage.ROUTE_STOP_STATION_INACTIVE
    default_code = 'route_stop_station_inactive'

class RouteStopTrainInactiveException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = RouteMessage.ROUTE_STOP_TRAIN_INACTIVE
    default_code = 'route_stop_train_inactive'

class RouteStopInactiveException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = RouteMessage.ROUTE_STOP_INACTIVE_CANNOT_ACCESS
    default_code = 'route_stop_inactive'

class RouteStopSequenceConflictException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = RouteMessage.ROUTE_STOP_SEQUENCE_CONFLICT
    default_code = 'route_stop_sequence_conflict'

class RouteStopStationConflictException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = RouteMessage.ROUTE_STOP_STATION_CONFLICT
    default_code = 'route_stop_station_conflict'

class RouteStopInvalidInputException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = RouteMessage.ROUTE_STOP_INVALID_INPUT
    default_code = 'route_stop_invalid_input'
 