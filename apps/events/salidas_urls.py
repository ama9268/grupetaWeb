from django.urls import path

from . import views

app_name = 'salidas'

urlpatterns = [
    path('', views.SalidaListView.as_view(), name='list'),
    path('nueva/', views.SalidaCreateView.as_view(), name='create'),
    path('<int:pk>/', views.SalidaDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', views.SalidaUpdateView.as_view(), name='edit'),
    # Agente de recomendación de ruta: endpoints "sueltos" (sin pk, la Salida puede no
    # existir todavía en BD mientras se rellena el formulario). Solo tienen sentido aquí.
    path('rutas/recomendar/', views.route_recommend, name='route_recommend'),
    path('rutas/recomendar/explicar/', views.route_recommend_explain, name='route_recommend_explain'),
]
