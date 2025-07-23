from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RouteEdgeViewSet, RouteTemplateViewSet

router = DefaultRouter()
router.register(r"admin/routes/", RouteEdgeViewSet, basename="route-edge")
router.register(
    r"admin/route-templates", RouteTemplateViewSet, basename="route-template"
)

urlpatterns = [
    path("api/", include(router.urls)),
]
