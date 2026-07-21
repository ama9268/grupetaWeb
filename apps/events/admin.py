from django.contrib import admin

from .models import Event, EventRSVP


class EventRSVPInline(admin.TabularInline):
    model = EventRSVP
    extra = 0
    raw_id_fields = ['member']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'start_at', 'state', 'created_by')
    list_filter = ('state', 'event_type')
    search_fields = ('title', 'description', 'location')
    date_hierarchy = 'start_at'
    raw_id_fields = ['associated_route', 'created_by']
    inlines = [EventRSVPInline]


@admin.register(EventRSVP)
class EventRSVPAdmin(admin.ModelAdmin):
    list_display = ('event', 'member', 'response', 'created_at')
    list_filter = ('response',)
    search_fields = ('event__title', 'member__email')
    raw_id_fields = ['event', 'member']
