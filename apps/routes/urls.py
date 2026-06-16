from django.urls import path
from . import views

app_name = 'routes'

urlpatterns = [
    path('', views.RouteListView.as_view(), name='list'),
    path('nueva/', views.RouteCreateView.as_view(), name='create'),
    path('<int:pk>/', views.RouteDetailView.as_view(), name='detail'),
]
