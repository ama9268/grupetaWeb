from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    path('', views.MemberListView.as_view(), name='list'),
    path('perfil/editar/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('perfil/editar/<int:pk>/', views.ProfileEditView.as_view(), name='profile_edit_member'),
    path('<int:pk>/', views.MemberDetailView.as_view(), name='detail'),
]
