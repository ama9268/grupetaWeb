from django.urls import path
from . import views

app_name = 'routes'

urlpatterns = [
    path('', views.RouteListView.as_view(), name='list'),
    path('nueva/', views.RouteCreateView.as_view(), name='create'),
    path('<int:pk>/', views.RouteDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', views.RouteUpdateView.as_view(), name='edit'),
    path('<int:pk>/eliminar/', views.route_delete, name='delete'),

    path('strava/conectar/', views.StravaConnectView.as_view(), name='strava_connect'),
    path('strava/callback/', views.StravaCallbackView.as_view(), name='strava_callback'),
    path('strava/staging/', views.StravaStagingView.as_view(), name='strava_staging'),
    path('strava/sincronizar/', views.StravaSyncActionView.as_view(), name='strava_sync'),
    path('strava/<int:pk>/importar/', views.StravaImportActionView.as_view(), name='strava_import'),
    path('strava/<int:pk>/descartar/', views.StravaDiscardActionView.as_view(), name='strava_discard'),
]
