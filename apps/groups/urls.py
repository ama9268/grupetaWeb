from django.urls import path
from . import views

app_name = 'groups'

urlpatterns = [
    path('', views.GroupListView.as_view(), name='list'),
    path('crear/', views.GroupCreateView.as_view(), name='create'),
    path('cambiar/', views.set_active_group, name='set_active'),
    path('<slug:slug>/', views.GroupDetailView.as_view(), name='detail'),
    path('<slug:slug>/unirme/', views.request_join_group, name='request_join'),
]
