from django.urls import path
from . import views

urlpatterns = [
    # Inventory list — /admin/inventory/
    path('', views.inventory_list, name='admin_inventory_list'),

    # Add stock to a specific variant — /admin/inventory/<id>/add/
    path('<int:inventory_id>/add/', views.inventory_add_stock, name='admin_inventory_add_stock'),

    # Full log for a specific variant — /admin/inventory/<id>/log/
    path('<int:inventory_id>/log/', views.inventory_log, name='admin_inventory_log'),
]