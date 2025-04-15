from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('grafo/', views.grafo_html, name='grafo_html'),
    path('grafo/data/', views.grafo_libros, name='grafo_data'),
    path('grafo/<str:param>/', views.grafo_parametrico_html, name='grafo_param_html'),
    path('grafo/<str:param>/data/', views.grafo_parametrico_data, name='grafo_param_data'),
]
