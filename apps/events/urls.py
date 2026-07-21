from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.EventListView.as_view(), name='list'),
    path('nuevo/', views.EventCreateView.as_view(), name='create'),
    path('<int:pk>/', views.EventDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', views.EventUpdateView.as_view(), name='edit'),
    # Acciones compartidas con Salidas (operan por pk, sin importar el tipo de evento —
    # ver apps/events/CLAUDE.md, sección "Salidas"): se registran una única vez aquí.
    path('<int:pk>/marcar-realizado/', views.event_mark_realizado, name='mark_realizado'),
    path('<int:pk>/archivar/', views.event_archive, name='archive'),
    path('<int:pk>/media/', views.event_media_upload, name='media_upload'),
    path('<int:pk>/viento/', views.event_wind_grid, name='wind_grid'),
    path('<int:event_id>/rsvp/<str:response>/', views.rsvp_view, name='rsvp'),
]
