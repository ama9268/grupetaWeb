from django.urls import path
from . import views

app_name = 'media_gallery'

urlpatterns = [
    path('', views.GalleryListView.as_view(), name='list'),
    path('subir/', views.MediaUploadView.as_view(), name='upload'),
    path('<int:item_id>/eliminar/', views.delete_media, name='delete'),
]
