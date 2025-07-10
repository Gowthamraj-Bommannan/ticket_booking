from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrainRouteViewSet, RouteTemplateViewSet, RouteTemplateStopViewSet

router = DefaultRouter()
router.register(r'train-routes', TrainRouteViewSet, basename='train-route')
router.register(r'admin/route-templates', RouteTemplateViewSet, basename='route-template')
router.register(r'admin/route-template-stops', RouteTemplateStopViewSet, basename='route-template-stop')

urlpatterns = [
    path('api/', include(router.urls)),
] 