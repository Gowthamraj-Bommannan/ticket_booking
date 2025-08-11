from django.contrib import admin
from .models import User, StaffRequest, Role, UserOTPVerification
from django.utils import timezone

admin.site.register(User)
admin.site.register(StaffRequest)
admin.site.register(Role)
admin.site.register(UserOTPVerification)
