# ---------- ROLE AND STATUS CHOICES ----------

class Choices:
    ROLE_CHOICES = [
            ("admin", "Admin"),
            ("user", "User"),
            ("station_master", "Station Master"),
        ]

    STATUS_CHOICES = [
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ]
    
    TRAIN_TYPE_CHOICES = [
        ("Local", "local"),
        ("Fast", "fast"),
        ("AC", "ac")
        ]
    
    DIRECTION_CHOICES = [
        ("up", "Up"),
        ("down", "Down")
        ]
    
    PAYMENT_METHOD_CHOICES = [
        ("UPI", "UPI"),
        ("WALLET", "Wallet"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("SUCCESS", "SUCCESS"),
        ("FAILED", "FAILED"),
    ]


# ---------- USER MESSAGES ----------
class UserMessage:
    USER_NOT_FOUND = "User not found."
    USER_ALREADY_EXISTS = "User already exists."
    INVALID_CREDENTIALS = "Invalid username or password."
    USER_REGISTERED_SUCCESSFULLY = "User registered successfully."
    USER_ROLE_NOT_FOUND = "Role PASSENGER is not defined in the system."
    USER_INACTIVE = "User account is disabled."
    USERNAME_AND_PASSWORD_REQUIRED = "Both username and password are required."
    USER_LOGIN_SUCCESSFUL = "Login in successful."
    OTP_SENT_REGISTRATION = (
        "OTP sent to mobile/email. Please provide OTP to complete registration."
    )
    OTP_SENT_STAFF_REGISTRATION = (
        "OTP sent to mobile/email. Please provide OTP to complete staff registration."
    )
    STAFF_REGISTRATION_WAITING = (
        "Staff registration successful. Waiting for admin approval."
    )
    INVALID_OTP = "Invalid OTP."
    PASSWORD_CHANGED_SUCCESS = "Password changed successfully."
    USER_NOT_AUTHORIZED = "Only users can view their tickets."
    STAFF_REQUEST_NOT_FOUND = "Staff request not found."
    USERNAME_TOO_SHORT = "Username must be at least 5 characters long."
    MOBILE_NUMBER_INVALID = "Mobile number must be exactly 10 digits and numeric."
    MASTER_NOT_FOUND = "Station Master not found with this ID {user_id}."
    NOT_STATION_MASTER = "User is not a station master."
    PASSWORD_TOO_SHORT = "Password must be at least 8 characters long."
    PASSWORD_TOO_LONG = "Password must not exceed 16 characters."
    STATION_MASTER_EXISTS = "Station master already exist for this station."
    MASTER_ALREADY_ASSIGNED = "Station master already assigned to another station."


# ---------- UNIQUE FIELD CONFLICTS ----------
class AlreadyExistsMessage:
    EMAIL_ALREADY_EXISTS = "Email already exists."
    USERNAME_ALREADY_EXISTS = "Username already exists."
    MOBILE_ALREADY_EXISTS = "Mobile number already exists."


class GeneralMessage:
    INVALID_INPUT = "Invalid input provided."
    QUERY_MISSING = "Search query parameter is required."
    PERMISSION_DENIED = "You do not have permission to perform this action."
    SOMETHING_WENT_WRONG = "Something went wrong. Please try again later."


# ---------STATION CONSTANTS-----------
class StationMessage:
    STATION_NOT_FOUND = "Station not found."
    STATION_CODE_NOT_FOUND = "Station with '{from_code}' or '{to_code}' not found."
    STATION_ALREADY_EXISTS = "Station with this name or code already exists."
    STATION_CODE_REQUIRED = "Station code is required."
    STATION_NAME_REQUIRED = "Station name is required."
    STATION_NAME_TOO_SHORT = "Station name must be at least 3 characters."
    STATION_CODE_INVALID = "Station code must be 2 to 5 characters."
    STATION_SEARCH_QUERY_REQUIRED = "Search query for station is required."
    STATION_DELETED_SUCCESSFULLY = "Station deleted successfully."
    STATION_UPDATED = "Station Updated Successfully."
    STATION_WITH_CODE_NOT_EXISTS = "Station with code '{station_code}' does not exist."
    STATION_WITH_ID_NOT_EXISTS = (
        "Station with ID {station_id} does not exist or is inactive."
    )
    STATION_ALREADY_INACTIVE = "Station is already inactive."
    STATION_ALREADY_ACTIVE = "Station is already active."
    STATION_DEACTIVATED = (
        "Station {station_name} ({station_code}) has been deactivated."
    )
    STATION_ACTIVATED = "Station {station_name} ({station_code}) has been activated."
    STATION_INACTIVE_CANNOT_ACCESS = "Station is inactive and cannot be accessed."
    STATION_INACTIVE_FOR_ROUTE = "Cannot create route with inactive station."
    STATION_INACTIVE_FOR_BOOKING = "Cannot create booking with inactive station."
    STATION_MASTER_EXISTS = "Station master already exist for this station."
    


# ------------TRAIN CONSTANTS-------------
class TrainMessage:
    TRAIN_NOT_FOUND = "Train not found."
    TRAIN_ALREADY_EXISTS = "Train with this name already exists."
    TRAIN_NUMBER_REQUIRED = "Train number is required."
    TRAIN_NAME_REQUIRED = "Train name is required."
    TRAIN_NAME_TOO_SHORT = "Train name must be at least 3 characters long."
    TRAIN_NAME_INVALID = "Train name should contains alphabets only."
    TRAIN_NUMBER_INVALID = "Train number must be numeric."
    TRAIN_COMPARTMENT_COUNT_INVALID = "Compartment count must be a positive integer."
    TRAIN_SEAT_COUNT_INVALID = "Seats per compartment must be a positive integer."
    TRAIN_WITH_NUMBER_NOT_EXIST = "Train with number '{train_number}' does not exist."
    TRAIN_QUERY_MISSING = "train_number query parameter is required."
    TRAIN_ALREADY_INACTIVE = "Train is already inactive."
    TRAIN_ALREADY_ACTIVE = "Train is already active."
    TRAIN_DEACTIVATED = "Train {train_name} ({train_number}) has been deactivated."
    TRAIN_ACTIVATED = "Train {train_name} ({train_number}) has been activated."
    TRAIN_INACTIVE_CANNOT_ACCESS = "Train is inactive and cannot be accessed."
    TRAIN_INACTIVE_FOR_ROUTE = "Cannot create route for inactive train."
    TRAIN_INACTIVE_FOR_BOOKING = "Cannot create booking for inactive train."
    TRAIN_CLASS_NOT_FOUND = "Classes are only General, FC and AC."
    TRAIN_DUPLICATE_CLASS = "Duplicate class types are not allowed."
    TRAIN_CLASES_MUST_DEFINED = "At least one class must be specified."
    TRAIN_CLASS_INVALID = "Invalid class type: {class_data['class_type']}. Must be one of {valid_class_types}"
    TRAIN_SCHEDULE_REQUIRED = "Train Scheduled is required."
    TRAIN_SCHEDULE_NOT_FOUND = "Train schedule not found."
    SCHEDULE_DIRECTION_NOT_BE_SAME = (
        "Train direction should be sequential. (Up and down)"
    )
    SCHEDULE_ALREADY_EXISTS = (
        "Train already has a schedule with same start time and diretion."
    )
    TRAIN_SCHEDULE_MUST_BE_DIFFERENT = "Train's new schedule must start from the station where the previous journey ended."
    TRAIN_SCHEDULE_OVERLAPS = "This train already has a schedule that overlaps with the requested time window."


# ----------- ROUTE/STOP CONSTANTS -------------
class RouteMessage:
    ROUTE_EDGE_NOT_FOUND = "Route edge not found."
    ROUTE_EDGE_ALREADY_EXISTS = "Route edge with this stations already exists."
    ROUTE_EDGE_INVALID_INPUT = "Invalid input for route edge."
    ROUTE_EDGE_INVALID_DISTANCE = "Distance must be a positive integer."
    ROUTE_EDGE_FROM_STATION_REQUIRED = "From station is required."
    ROUTE_EDGE_TO_STATION_REQUIRED = "To station is required."
    ROUTE_EDGE_STATION_NOT_FOUND = "From or to station not found."
    ROUTE_EDGE_FROM_AND_TO_SAME = "from_station and to_station must be different."
    ROUTE_EDGE_PERMISSION_DENIED = "You do not have permission to create route edges."
    ROUTE_NOT_FOUND_BETWEEN = "No route found between {from_station} and {to_station}."
    ROUTE_ALREADY_EXISTS_IN_SAME_TIME = "Route already exists in this timings."
    ROUTE_EDGE_UNIDIRECTIONAL_EXISTS = "A unidirectional edge in this direction already exists."
    ROUTE_EDGE_MISSING_FIELDS = "Missing required fields: from_station, to_station, or distance."
    ROUTE_EDGE_CATEGORY_INVALID = "Category must be 'local' or 'fast'."
    ROUTE_EDGE_NO_STOPS = "Train should have atleast one stop."
    ROUTE_TEMPLATE_NOT_ENOUGH_STOPS = "Route template does not have enough stops."

# ----------- PAYMENT CONSTANTS -------------
class PaymentMessage:
    PAYMENT_FAILED = "Payment failed. Please try again."
    PAYMENT_ALREADY_SUCCESS = "Payment already completed for this booking."
    PAYMENT_NOT_FOUND = "Payment transaction not found."
    INVALID_PAYMENT_METHOD = "Invalid payment method (Only Upi and Wallet)."
    PAYMENT_AMOUNT_MISMATCH = "Payment amount does not match booking total."
    PAYMENT_GATEWAY_ERROR = "Payment gateway error. Please try again later."
    PAYMENT_PENDING = "Payment is still pending."
    PAYMENT_REFUND_INITIATED = "Refund has been initiated for this payment."
    PAYMENT_UNAUTHORIZED = "You are not authorized to perform this payment."
    PAYMENT_SESSION_EXPIRED = "Payment session has expired. Please start again."
    PAYMENT_AMOUNT_ZERO = "Amount must be greater than zero."
    PAYMENT_TRANSACTION_ID_BLANK = "Transaction ID cannot be blank."
    PAYMENT_STATUS_INVALID = "Status must be SUCCESS or FAILED."


class BookingMessage:
    FROM_AND_TO_MUST_BE_DIFFERENT = "From and To station codes must be different."
    ATLEAST_ONE_PASSENGER_REQUIRED = "At least one passenger is required."
    INVALID_CLASS_TYPE = "Invalid class type."
    NEW_TO_STATION_REQUIRED = "New to station required."
    BOOKED_TICKETS_CAN_BE_EXCHANGED = "Only booked tickets can be exchanged."
    FROM_AND_TO_ARE_REQUIRED = "Both from and to stations are required."
    FORBIDDEN = "You do not have the permission for this."
