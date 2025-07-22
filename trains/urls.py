from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrainViewSet, TrainScheduleViewSet

router = DefaultRouter()
router.register(r'admin/trains', TrainViewSet, basename='admin-trains')
router.register(r'admin/train-schedule', TrainScheduleViewSet, basename='admin-trains-schedule')

urlpatterns = [
    path('api/', include(router.urls)),
] 