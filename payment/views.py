from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import PaymentTransaction
from bookingsystem.models import Booking, Passenger
from bookingsystem.serializers import BookingSerializer
from bookingsystem.services import assign_seats, generate_unique_pnr
import random, string
from exceptions.handlers import (
    PaymentFailedException, PaymentAlreadySuccessException, PaymentNotFoundException,
    InvalidPaymentMethodException, PaymentAmountMismatchException, PaymentGatewayErrorException,
    PaymentPendingException, PaymentRefundInitiatedException, PaymentUnauthorizedException, PaymentSessionExpiredException
)
import logging
logger = logging.getLogger("payment")

class PaymentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='process')
    def process(self, request):
        """Process payment and ticketing in one step (mocked payment verification)"""
        try:
            booking_id = request.data.get('booking_id')
            payment_method = request.data.get('payment_method', 'CARD')
            gateway_response = request.data.get('gateway_response', {})
            if not booking_id:
                logger.error("No booking_id provided in payment request.")
                raise PaymentFailedException("Booking ID is required.")
            booking = get_object_or_404(Booking, id=booking_id, user=request.user)
            if getattr(request.user, 'role', None) != 'user':
                logger.warning(f"Unauthorized payment attempt by user {request.user}")
                raise PaymentUnauthorizedException()
            if booking.booking_status not in ['PENDING']:
                logger.warning(f"Booking {booking_id} not in PENDING state for payment.")
                raise PaymentFailedException("Booking not in PENDING state.")
            # Validate payment method
            valid_methods = ['CARD', 'UPI', 'NETBANKING', 'WALLET']
            if payment_method not in valid_methods:
                logger.error(f"Invalid payment method: {payment_method}")
                raise InvalidPaymentMethodException()
            # Validate payment amount (if provided)
            amount = request.data.get('amount')
            if amount is not None and float(amount) != float(booking.total_fare):
                logger.error(f"Payment amount mismatch: {amount} vs {booking.total_fare}")
                raise PaymentAmountMismatchException()
            # Check if payment already exists for this booking
            if hasattr(booking, 'payments') and booking.payments.filter(status='SUCCESS').exists():
                logger.warning(f"Payment already completed for booking {booking_id}")
                raise PaymentAlreadySuccessException()
            # Create PaymentTransaction (if model is present)
            payment = None
            try:
                payment = PaymentTransaction.objects.create(
                    booking=booking,
                    payment_gateway_id=gateway_response.get('razorpay_order_id', 'SAMPLEPAY'),
                    amount=booking.total_fare,
                    status='SUCCESS',
                    payment_method=payment_method,
                    paid_at=timezone.now()
                )
                logger.info(f"Payment transaction created: {payment.id} for booking {booking_id}")
            except Exception as e:
                logger.error(f"Payment gateway error: {str(e)}")
                raise PaymentGatewayErrorException()
            # Mark booking as paid and process ticket
            if hasattr(booking, 'is_paid'):
                booking.is_paid = True
            elif hasattr(booking, 'paid'):
                booking.paid = True
            # Generate PNR if not set
            if not booking.pnr_number:
                booking.pnr_number = generate_unique_pnr()
            # Assign seats and update booking status
            assign_seats(booking)
            if all(p.booking_status == 'CONFIRMED' for p in booking.passengers.all()):
                booking.booking_status = 'CONFIRMED'
            elif any(p.booking_status == 'RAC' for p in booking.passengers.all()):
                booking.booking_status = 'RAC'
            else:
                booking.booking_status = 'WL'
            booking.save()
            # Prepare response
            ticket = BookingSerializer(booking).data
            receipt = None
            if payment:
                receipt = {
                    'payment_id': payment.id,
                    'payment_gateway_id': payment.payment_gateway_id,
                    'amount': float(payment.amount),
                    'status': payment.status,
                    'payment_method': payment.payment_method,
                    'paid_at': payment.paid_at
                }
            logger.info(f"Payment processed successfully for booking {booking_id}")
            return Response({'ticket': ticket, 'receipt': receipt}, status=200)
        except Exception as e:
            logger.error(f"Unexpected payment error: {str(e)}", exc_info=True)
            raise PaymentFailedException(str(e))

    def _generate_payment_session_id(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12)) 