from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile


# Inline model that will appear on User admin page
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


# Extend UserAdmin to include the inline
class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline, )

    # Optional: show user_type in user list table
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_user_type')

    def get_user_type(self, obj):
        return obj.core_profile.user_type if hasattr(obj, 'core_profile') else "N/A"
    get_user_type.short_description = 'User Type'


# Unregister original User admin
admin.site.unregister(User)

# Register new one with inline
admin.site.register(User, CustomUserAdmin)


# Keep Profile in admin too (optional)
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type')
