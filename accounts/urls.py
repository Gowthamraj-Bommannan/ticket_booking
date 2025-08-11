from django.urls import path
from .views import (
    LoginView,
    LogoutView,
    ProfileView,
    ChangePasswordView,
    StaffRequestListView,
    StaffRequestDetailView,
    ApproveStaffRequestView,
    RejectStaffRequestView,
    ApproveAllStaffRequestsView,
    RejectAllStaffRequestsView,
    user_tickets,
    UnifiedRegistrationView,
    OTPValidationView,
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Unified Registration System
    path("api/auth/register/", UnifiedRegistrationView.as_view(), name="register-unified"),
    path("api/auth/validate-otp/", OTPValidationView.as_view(), name="validate-otp"),
    
    # User Authentication
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    
    # User Profile Management
    path("api/profile/", ProfileView.as_view(), name="profile"),
    path("api/profile/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("api/user/tickets/", user_tickets, name="user-tickets"),
    
    # Admin Staff Approval Panel
    path(
        "api/admin/staff-requests/",
        StaffRequestListView.as_view(),
        name="staff-requests-list",
    ),
    path(
        "api/admin/staff-requests/<int:pk>/",
        StaffRequestDetailView.as_view(),
        name="staff-request-detail",
    ),
    path(
        "api/admin/staff-requests/approve/<int:pk>/",
        ApproveStaffRequestView.as_view(),
        name="approve-staff-request",
    ),
    path(
        "api/admin/staff-requests/reject/<int:pk>/",
        RejectStaffRequestView.as_view(),
        name="reject-staff-request",
    ),
    path(
        "api/admin/staff-requests/approve-all/",
        ApproveAllStaffRequestsView.as_view(),
        name="approve-all-staff-requests",
    ),
    path(
        "api/admin/staff-requests/reject-all/",
        RejectAllStaffRequestsView.as_view(),
        name="reject-all-staff-requests",
    ),
]
