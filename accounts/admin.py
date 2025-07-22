from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Role, StaffRequest

admin.site.register(User)
admin.site.register(Role)
admin.site.register(StaffRequest)
