from django.urls import path
from . import views

urlpatterns = [
    path('', views.store, name='store'),
    path('search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('<slug:category_slug>/', views.store, name='products_by_category'),
    path('<slug:category_slug>/<slug:variant_slug>/', views.product_detail, name='product_detail'),
]