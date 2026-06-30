from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('pending/', views.PendingApprovalView.as_view(), name='pending'),
    path('manage/', views.ManageUsersView.as_view(), name='manage_users'),
    path('approve/<int:user_id>/', views.approve_user, name='approve_user'),
    path('reject/<int:user_id>/', views.reject_user, name='reject_user'),
    path('role/<int:user_id>/', views.change_role, name='change_role'),
]
