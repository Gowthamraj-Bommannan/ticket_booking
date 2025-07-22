from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='local-booking')

urlpatterns = [
    path('api/', include(router.urls)),
] 