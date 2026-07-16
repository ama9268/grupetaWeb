from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('pending/', views.PendingApprovalView.as_view(), name='pending'),
    path('manage/', views.ManageUsersView.as_view(), name='manage_users'),
    path('approve/<int:membership_id>/', views.approve_user, name='approve_user'),
    path('reject/<int:membership_id>/', views.reject_user, name='reject_user'),
    path('role/<int:membership_id>/', views.change_role, name='change_role'),
]
