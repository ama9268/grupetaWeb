from django.contrib import admin
from django.contrib.auth.models import Group as DjangoGroup

from .models import Group, Membership

# El proyecto no usa grupos de permisos de Django (ver CLAUDE.md raíz); se
# desregistra para no confundirlo con apps.groups.models.Group en el admin.
admin.site.unregister(DjangoGroup)


class MembershipInline(admin.TabularInline):
    """Inline de Membership para el admin de `Group` (una fila por miembro)."""
    model = Membership
    extra = 0
    fields = ('user', 'role', 'status', 'created_at', 'decided_at', 'decided_by')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('user', 'decided_by')


class UserMembershipInline(MembershipInline):
    """Igual que `MembershipInline`, pero para el admin de `User` (una fila por
    grupeta). `Membership` tiene dos FKs a `User` (`user` y `decided_by`); hay
    que desambiguar con `fk_name`."""
    fk_name = 'user'
    fields = ('group', 'role', 'status', 'created_at', 'decided_at', 'decided_by')
    autocomplete_fields = ('group', 'decided_by')


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_by', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'role', 'status', 'created_at', 'decided_at')
    list_filter = ('group', 'role', 'status')
    search_fields = ('user__username', 'user__email', 'group__name')
    autocomplete_fields = ('user', 'group', 'decided_by')
