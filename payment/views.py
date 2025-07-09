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

class PaymentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='process')
    def process(self, request):
        """Process payment and ticketing in one step (mocked payment verification)"""
        booking_id = request.data.get('booking_id')
        payment_method = request.data.get('payment_method', 'CARD')
        gateway_response = request.data.get('gateway_response', {})
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        # Accept booking if status is PENDING
        if getattr(request.user, 'role', None) != 'user':
            return Response({'detail': 'Only users can process payments.'}, status=403)
        if booking.booking_status not in ['PENDING']:
            return Response({'detail': 'Booking not in PENDING state.'}, status=400)
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
        except Exception:
            # If PaymentTransaction is removed, ignore
            pass
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
        return Response({'ticket': ticket, 'receipt': receipt}, status=200)

    def _generate_payment_session_id(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12)) 