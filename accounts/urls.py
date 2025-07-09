from django.urls import path
from .views import (
    RegisterView, StaffRegisterView, LoginView, LogoutView, ProfileView, 
    ChangePasswordView, BookingHistoryView, StaffRequestListView, 
    StaffRequestDetailView, ApproveStaffRequestView, RejectStaffRequestView,
    ApproveAllStaffRequestsView, RejectAllStaffRequestsView, user_tickets
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # User Authentication
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/register-staff/', StaffRegisterView.as_view(), name='register-staff'),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User Profile Management
    path('api/profile/', ProfileView.as_view(), name='profile'),
    path('api/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('api/booking-history/', BookingHistoryView.as_view(), name='booking-history'),
    path('api/user/tickets/', user_tickets, name='user-tickets'),
    
    # Admin Staff Approval Panel
    path('api/admin/staff-requests/', StaffRequestListView.as_view(), name='staff-requests-list'),
    path('api/admin/staff-requests/<int:pk>/', StaffRequestDetailView.as_view(), name='staff-request-detail'),
    path('api/admin/approve/<int:pk>/', ApproveStaffRequestView.as_view(), name='approve-staff-request'),
    path('api/admin/reject/<int:pk>/', RejectStaffRequestView.as_view(), name='reject-staff-request'),
    path('api/admin/approve-all/', ApproveAllStaffRequestsView.as_view(), name='approve-all-staff-requests'),
    path('api/admin/reject-all/', RejectAllStaffRequestsView.as_view(), name='reject-all-staff-requests'),
]