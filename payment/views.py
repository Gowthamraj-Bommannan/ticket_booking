from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import PaymentTransaction
from .serializers import PaymentTransactionSerializer
from bookingsystem.models import Booking
from exceptions.handlers import (
    PaymentAlreadySuccessException,
    PaymentUnauthorizedException,
    PaymentFailedException,
    PermissionDeniedException,
    PaymentNotFoundException,
)
import logging
import uuid

logger = logging.getLogger("payment")


class PaymentTransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing payment transactions.
    Supports CRUD operations and payment processing.
    """

    queryset = PaymentTransaction.objects.all()
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Returns payment transactions for the current user only.
        Ensures users cannot access others' payments.
        """
        user = self.request.user
        return PaymentTransaction.objects.filter(booking__user=user)

    def create(self, request, *args, **kwargs):
        """
        Handles payment creation requests.
        Validates and processes payment data.
        """
        user = request.user
        self._validate_user(user)
        booking = self._get_and_validate_booking(request, user)
        self._check_existing_payment(booking)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data.get("amount")
        self._validate_amount(amount, booking, booking.id)
        transaction_id = self._get_or_generate_transaction_id(serializer)
        payment = serializer.save(
            booking=booking, paid_at=timezone.now(), transaction_id=transaction_id
        )
        booking.booking_status = "BOOKED" if payment.status == "SUCCESS" else "FAILED"
        booking.save()
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

    def _validate_user(self, user):
        """
        Raises exception if user is staff or superuser.
        """
        if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
            logger.warning(f"Admin/staff {user} attempted to make a payment.")
            raise PaymentUnauthorizedException()

    def _get_and_validate_booking(self, request, user):
        """
        Retrieves and validates the booking for the user.
        Raises exception if not found or not pending.
        """
        booking_id = request.data.get("booking")
        booking = get_object_or_404(Booking, id=booking_id, user=user)
        if getattr(booking, "booking_status", None) != "PENDING":
            logger.warning(f"Booking {booking_id} not found for payment.")
            raise PaymentNotFoundException()
        return booking

    def _check_existing_payment(self, booking):
        """
        Raises exception if a successful payment already exists for the booking.
        """
        if PaymentTransaction.objects.filter(
            booking=booking, status="SUCCESS"
        ).exists():
            logger.warning(f"Payment already completed for booking {booking.id}")
            raise PaymentAlreadySuccessException()

    def _validate_amount(self, amount, booking, booking_id):
        """
        Validates that the payment amount matches the booking fare.
        """
        if float(amount) != float(getattr(booking, "total_fare", 0)):
            logger.warning(
                f"Payment amount does not match booking fare for booking {booking_id}"
            )
            raise PaymentFailedException()

    def _get_or_generate_transaction_id(self, serializer):
        """
        Returns transaction_id from serializer or generates a new one.
        """
        transaction_id = serializer.validated_data.get("transaction_id")
        if not transaction_id:
            transaction_id = str(uuid.uuid4())
        return transaction_id

    def update(self, request, *args, **kwargs):
        """
        Handles payment update requests.
        Updates payment status or details.
        """
        raise PermissionDeniedException()

    def partial_update(self, request, *args, **kwargs):
        """
        Disallow partial update of payments.
        Always raises a permission exception.
        """
        raise PermissionDeniedException()

    def destroy(self, request, *args, **kwargs):
        """
        Deletes a payment transaction.
        Removes payment record from database.
        """
        raise PermissionDeniedException()
