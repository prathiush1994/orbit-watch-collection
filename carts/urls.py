from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart, name='cart'),
    path('add/<int:variant_id>/', views.add_cart, name='add_cart'),
    path('increment/<int:variant_id>/', views.increment_cart, name='increment_cart'),
    path('decrement/<int:variant_id>/', views.decrement_cart, name='decrement_cart'),
    path('remove-item/<int:variant_id>/', views.remove_cartitem, name='remove_cartitem'),
]