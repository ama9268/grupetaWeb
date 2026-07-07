from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.EventListView.as_view(), name='list'),
    path('nuevo/', views.EventCreateView.as_view(), name='create'),
    path('<int:pk>/', views.EventDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', views.EventUpdateView.as_view(), name='edit'),
    path('<int:pk>/aceptar/', views.event_accept, name='accept'),
    path('<int:pk>/cancelar/', views.event_cancel, name='cancel'),
    path('<int:pk>/media/', views.event_media_upload, name='media_upload'),
    path('<int:event_id>/rsvp/<str:response>/', views.rsvp_view, name='rsvp'),
]
