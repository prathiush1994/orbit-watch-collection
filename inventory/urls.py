from django.urls import path
from . import views

urlpatterns = [
    path("", views.inventory_list, name="admin_inventory_list"),
    path(
        "<int:inventory_id>/add/",
        views.inventory_add_stock,
        name="admin_inventory_add_stock",
    ),
    path("<int:inventory_id>/log/", views.inventory_log, name="admin_inventory_log"),
]
