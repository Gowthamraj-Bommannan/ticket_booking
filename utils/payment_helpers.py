import uuid
import logging
from django.utils import timezone

logger = logging.getLogger("payment")


class PaymentHelpers:
    """
    Reusable helper methods for payment operations.
    Centralizes payment-related utilities to reduce redundancy.
    """
    
    @staticmethod
    def generate_transaction_id():
        """
        Generates a unique transaction ID using UUID.
        
        Returns:
            str: Unique transaction ID
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def get_or_generate_transaction_id(transaction_id=None):
        """
        Returns transaction_id if provided, otherwise generates a new one.
        
        Args:
            transaction_id (str, optional): Existing transaction ID
            
        Returns:
            str: Transaction ID (existing or generated)
        """
        if not transaction_id:
            return PaymentHelpers.generate_transaction_id()
        return transaction_id
    
    @staticmethod
    def update_booking_status(booking, payment_status):
        """
        Updates booking status based on payment status.
        Optimized to use single save operation.
        
        Args:
            booking: Booking object to update
            payment_status (str): Payment status (SUCCESS/FAILED)
            
        Returns:
            str: Updated booking status
        """
        new_status = "BOOKED" if payment_status == "SUCCESS" else "FAILED"
        booking.booking_status = new_status
        booking.save(update_fields=['booking_status'])
        return new_status
    
    @staticmethod
    def create_payment_with_optimized_queries(serializer, booking, transaction_id):
        """
        Creates payment with optimized database queries.
        Reduces multiple queries to single operations.
        
        Args:
            serializer: Payment serializer
            booking: Booking object
            transaction_id (str): Transaction ID
            
        Returns:
            PaymentTransaction: Created payment object
        """
        # Single save operation with all required fields
        payment = serializer.save(
            booking=booking,
            paid_at=timezone.now(),
            transaction_id=transaction_id
        )
        
        # Update booking status in same transaction
        PaymentHelpers.update_booking_status(booking, payment.status)
        
        return payment 