from rest_framework import serializers
from .models import PaymentTransaction
from exceptions.handlers import InvalidPaymentMethodException
from utils.constants import PaymentMessage

class PaymentTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for PaymentTransaction model.
    Handles validation for payment fields.
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
        Raises exception if invalid.
        """
        allowed_methods = ["UPI", "WALLET"]
        if value not in allowed_methods:
            raise InvalidPaymentMethodException()
        return value

    def validate_amount(self, value):
        """
        Validates that the payment amount is positive.
        Raises error if invalid.
        """
        if value <= 0:
            raise serializers.ValidationError(PaymentMessage.
                                              PAYMENT_AMOUNT_ZERO)
        return value

    def validate_transaction_id(self, value):
        """
        Validates that the transaction ID is not blank.
        """
        if not value or not value.strip():
            raise serializers.ValidationError(PaymentMessage.
                                              PAYMENT_TRANSACTION_ID_BLANK)
        return value

    def validate_status(self, value):
        """
        Validates that the status is SUCCESS or FAILED.
        """
        allowed_statuses = ["SUCCESS", "FAILED"]
        if value not in allowed_statuses:
            raise serializers.ValidationError(
                PaymentMessage.PAYMENT_STATUS_INVALID
            )
        return value
