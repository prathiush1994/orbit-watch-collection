from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart, name='cart'),
    path('add_cart/<int:variant_id>/', views.add_cart, name='add_cart'),
    path('remove_cart/<int:variant_id>/', views.remove_cart, name='remove_cart'),
    path('remove_cartitem/<int:variant_id>/', views.remove_cartitem, name='remove_cartitem'),
]