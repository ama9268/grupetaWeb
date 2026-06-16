from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.PostListView.as_view(), name='list'),
    path('nuevo/', views.PostCreateView.as_view(), name='create'),
    path('<int:pk>/', views.PostDetailView.as_view(), name='detail'),
    path('<int:post_id>/comentar/', views.add_comment, name='add_comment'),
    path('comentario/<int:comment_id>/eliminar/', views.delete_comment, name='delete_comment'),
    path('<int:post_id>/eliminar/', views.delete_post, name='delete_post'),
    path('<int:post_id>/like/', views.toggle_like, name='toggle_like'),
]
