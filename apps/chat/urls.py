from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.ChatRoomView.as_view(), name='room'),
    path('sala/<slug:slug>/', views.ChatRoomView.as_view(), name='room_detail'),
    path('mensaje/<int:message_id>/eliminar/', views.delete_message, name='delete_message'),
]
