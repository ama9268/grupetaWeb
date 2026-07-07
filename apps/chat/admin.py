from django.contrib import admin

from .models import ChatRoom, Message


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'category', 'is_archived', 'created_at')
    list_filter = ('category', 'is_archived')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'user', 'content', 'is_deleted', 'created_at')
    list_filter = ('is_deleted', 'room')
    search_fields = ('content', 'user__email')
    raw_id_fields = ('room', 'user', 'deleted_by')
