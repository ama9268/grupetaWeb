from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.ChatRoomView.as_view(), name='room'),
    path('salas/gestionar/', views.ManageRoomsView.as_view(), name='manage_rooms'),
    path('salas/crear/', views.create_room, name='create_room'),
    path('sala/<slug:slug>/', views.ChatRoomView.as_view(), name='room_detail'),
    path('sala/<slug:slug>/adjuntar/', views.upload_attachment, name='upload_attachment'),
    path('sala/<slug:slug>/renombrar/', views.rename_room, name='rename_room'),
    path('sala/<slug:slug>/archivar/', views.toggle_archive_room, name='toggle_archive_room'),
    path('mensaje/<int:message_id>/eliminar/', views.delete_message, name='delete_message'),
]
