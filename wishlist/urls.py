from django.urls import path
from . import views

urlpatterns = [
    path("wishlist/", views.wishlist, name="wishlist"),
    path(
        "wishlist/toggle/<int:variant_id>/",
        views.toggle_wishlist,
        name="toggle_wishlist"),
    path(
        "wishlist/remove/<int:variant_id>/",
        views.remove_wishlist,
        name="remove_wishlist"),
    path(
        "wishlist/add-to-cart/<int:variant_id>/",
        views.add_to_cart_from_wishlist,
        name="wishlist_add_to_cart",
    ),
]
