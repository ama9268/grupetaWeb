from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fields = ('role', 'status')


class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'get_role', 'get_status')
    list_filter = ('is_active', 'profile__role', 'profile__status')

    @admin.display(description='Rol')
    def get_role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, 'profile') else '-'

    @admin.display(description='Estado')
    def get_status(self, obj):
        return obj.profile.get_status_display() if hasattr(obj, 'profile') else '-'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(UserProfile)
