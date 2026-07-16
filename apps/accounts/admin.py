from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from apps.groups.admin import UserMembershipInline
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fields = ('is_admin',)


class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline, UserMembershipInline]
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'get_role')
    list_filter = ('is_active', 'profile__is_admin')

    @admin.display(description='Rol')
    def get_role(self, obj):
        return obj.profile.role_label if hasattr(obj, 'profile') else '-'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(UserProfile)
