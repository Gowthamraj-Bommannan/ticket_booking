from django.db import models
from bookingsystem.models import Booking


class PaymentTransaction(models.Model):
    """
    Represents a payment transaction for a booking.
    Stores payment status, amount, and related booking.
    """

    STATUS_CHOICES = [
        ("SUCCESS", "SUCCESS"),
        ("FAILED", "FAILED"),
    ]
    METHOD_CHOICES = [
        ("UPI", "UPI"),
        ("WALLET", "Wallet"),
    ]
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="payments"
    )
    transaction_id = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["booking"],
                condition=models.Q(status="SUCCESS"),
                name="unique_successful_payment_per_booking",
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.booking.pnr_number or self.booking.id} - {self.status}"
