from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import PaymentTransaction
from .serializers import PaymentTransactionSerializer
from utils.queryset_helpers import UserSpecificQuerysetMixin
from utils.validators import PaymentValidators
from utils.payment_helpers import PaymentHelpers
from exceptions.handlers import (
    MethodNotAllowedException,
    )
from utils.constants import PaymentMessage
import logging

logger = logging.getLogger("payment")


class PaymentTransactionViewSet(UserSpecificQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing payment transactions.
    Supports CRUD operations and payment processing with optimized database hits.
    """

    queryset = PaymentTransaction.objects.all()
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsAuthenticated]
    user_field = "booking__user"  # Specify the user relationship field

    def create(self, request, *args, **kwargs):
        """
        Handles payment creation requests with optimized database hits.
        Uses centralized validators and helpers.
        """
        user = request.user
        
        # Validate user authorization using centralized validator
        PaymentValidators.validate_user_authorized(user)
        
        # Get and validate booking with optimized query
        booking_id = request.data.get("booking")
        booking = PaymentValidators.validate_booking_for_payment(booking_id, user)
        
        # Check existing payment using centralized validator
        PaymentValidators.check_existing_successful_payment(booking)
        
        # Validate serializer data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Validate amount matches booking fare
        amount = serializer.validated_data.get("amount")
        PaymentValidators.validate_payment_amount_matches_booking(amount, booking)
        
        # Generate transaction ID using centralized helper
        transaction_id = PaymentHelpers.get_or_generate_transaction_id(
            serializer.validated_data.get("transaction_id")
        )
        
        # Create payment with optimized queries
        payment = PaymentHelpers.create_payment_with_optimized_queries(
            serializer, booking, transaction_id
        )
        
        logger.info(
            f"Payment {payment.status} for booking ticket - {booking.id} by user {user}"
        )
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "payment": PaymentTransactionSerializer(payment).data,
                "booking_status": booking.booking_status,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def update(self, request, *args, **kwargs):
        """
        Handles payment update requests.
        Updates payment status or details.
        """
        raise MethodNotAllowedException(PaymentMessage.PAYMENT_UNAUTHORIZED)

    def partial_update(self, request, *args, **kwargs):
        """
        Disallow partial update of payments.
        Always raises a permission exception.
        """
        raise MethodNotAllowedException(PaymentMessage.PAYMENT_UNAUTHORIZED)

    def destroy(self, request, *args, **kwargs):
        """
        Deletes a payment transaction.
        Removes payment record from database.
        """
        raise MethodNotAllowedException(PaymentMessage.PAYMENT_UNAUTHORIZED)
