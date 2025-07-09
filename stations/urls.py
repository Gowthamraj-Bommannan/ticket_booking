from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StationViewSet

router = DefaultRouter()
router.register(r'admin/stations', StationViewSet, basename='admin-stations')

urlpatterns = [
    path('api/', include(router.urls)),
] 