from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentTransactionViewSet

router = DefaultRouter()
router.register(r"payments", PaymentTransactionViewSet, basename="payment-transaction")

urlpatterns = [
    path("api/", include(router.urls)),
]
