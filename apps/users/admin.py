from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Custom admin for User model"""
    list_display = ('username', 'email', 'company_name', 'is_verified', 'is_staff')
    list_filter = ('is_verified', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('company_name', 'phone', 'is_verified', 
                      'total_api_calls', 'last_api_call')
        }),
    )
    readonly_fields = ('total_api_calls', 'last_api_call', 'created_at', 'updated_at')