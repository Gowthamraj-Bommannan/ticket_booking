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
    INVALID_CREDENTIALS = "Invalid username or password."
    PASSWORD_CHANGED_SUCCESS = "Password changed successfully."
    STAFF_REQUEST_NOT_FOUND = "Staff request not found."
    USER_NOT_AUTHORIZED = "Only users can view their tickets."
    USERNAME_TOO_SHORT = "Username must be at least 5 characters long."
    MOBILE_NUMBER_INVALID = "Mobile number must be exactly 10 digits and numeric."
    MASTER_NOT_FOUND = "Station Master not found with this ID {user_id}."
    STATION_MASTER_EXISTS = "Station master already exist for this station."
    MASTER_ALREADY_ASSIGNED = "Station master already assigned to another station."
    ADMIN_ROLE_REGISTRATION_NOT_ALLOWED = "Admin role registration is not allowed."
    OTP_EXPIRED = "OTP has expired. Please register again."
    ROLE_NOT_FOUND = "Role not found."  
    PASSWORD_NOT_MATCH = "Passwords do not match."
    USER_NOT_FOUND = "User not found."


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
    STATION_CODE_REQUIRED = "Station code is required."
    STATION_CODE_INVALID = "Station code must be 2 to 5 characters."
    STATION_ALREADY_EXISTS = "Station with this name or code already exists."
    STATION_NAME_REQUIRED = "Station name is required."
    STATION_NAME_TOO_SHORT = "Station name must be at least 3 characters."


# ------------TRAIN CONSTANTS-------------
class TrainMessage:
    TRAIN_NOT_FOUND = "Train not found."
    TRAIN_ALREADY_EXISTS = "Train with this name already exists."
    TRAIN_SCHEDULE_NOT_FOUND = "Train schedule not found."
    SCHEDULE_ALREADY_EXISTS = (
        "Train already has a schedule with same start time and diretion."
    )
    TRAIN_SCHEDULE_OVERLAPS = "This train already has a schedule that overlaps with the requested time window."
    SCHEDULE_DIRECTION_NOT_BE_SAME = (
        "Train direction should be sequential. (Up and down)"
    )
    TRAIN_SCHEDULE_MUST_BE_DIFFERENT = "Train's new schedule must start from the station where the previous journey ended."


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
    PAYMENT_UNAUTHORIZED = "You are not authorized to perform this payment."
    PAYMENT_AMOUNT_ZERO = "Amount must be greater than zero."
    PAYMENT_TRANSACTION_ID_BLANK = "Transaction ID cannot be blank."
    PAYMENT_STATUS_INVALID = "Status must be SUCCESS or FAILED."


class BookingMessage:
    FROM_AND_TO_MUST_BE_DIFFERENT = "From and To station codes must be different."
    INVALID_CLASS_TYPE = "Invalid class type."
    NEW_TO_STATION_REQUIRED = "New to station required."
    BOOKED_TICKETS_CAN_BE_EXCHANGED = "Only booked tickets can be exchanged."
    FROM_AND_TO_ARE_REQUIRED = "Both from and to stations are required."
    FORBIDDEN = "You do not have the permission for this."
    ADMIN_CANNOT_CREATE_BOOKING = "Admin users cannot create bookings."
