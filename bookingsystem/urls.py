from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet, TrainSearchViewSet, SeatAvailabilityViewSet

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'search-trains', TrainSearchViewSet, basename='train-search')
router.register(r'availability', SeatAvailabilityViewSet, basename='seat-availability')

urlpatterns = [
    path('api/', include(router.urls)),
] 