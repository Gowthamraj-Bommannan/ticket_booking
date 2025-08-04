from rest_framework import serializers
from .models import PaymentTransaction
from utils.validators import PaymentValidators

class PaymentTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for PaymentTransaction model.
    Handles validation for payment fields using centralized validators.
    """

    transaction_id = serializers.CharField(required=False)

    class Meta:
        model = PaymentTransaction
        fields = [
            "booking",
            "amount",
            "payment_method",
            "status",
            "transaction_id",
            "paid_at",
        ]
        read_only_fields = ["id", "paid_at"]

    def validate_payment_method(self, value):
        """
        Validates that the payment method is UPI or WALLET.
        Uses centralized validator.
        """
        return PaymentValidators.validate_payment_method(value)

    def validate_amount(self, value):
        """
        Validates that the payment amount is positive.
        Uses centralized validator.
        """
        return PaymentValidators.validate_payment_amount(value)

    def validate_transaction_id(self, value):
        """
        Validates that the transaction ID is not blank.
        Uses centralized validator.
        """
        return PaymentValidators.validate_transaction_id(value)

    def validate_status(self, value):
        """
        Validates that the status is SUCCESS or FAILED.
        Uses centralized validator.
        """
        return PaymentValidators.validate_payment_status(value)
