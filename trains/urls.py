from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrainViewSet

router = DefaultRouter()
router.register(r'admin/trains', TrainViewSet, basename='admin-trains')
router.register(r'trains', TrainViewSet, basename='trains')

urlpatterns = [
    path('api/', include(router.urls)),
] 