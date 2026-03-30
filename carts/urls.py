from django.urls import path
from . import views

urlpatterns = [
    path('',                                        views.cart,                   name='cart'),
    path('add/<int:variant_id>/',                   views.add_cart,               name='add_cart'),
    path('remove/<int:variant_id>/',                views.remove_cart,            name='remove_cart'),
    path('remove-item/<int:variant_id>/',           views.remove_cartitem,        name='remove_cartitem'),

    # ── AJAX endpoint for +/− buttons ─────────────────────────────────────────
    path('update/<int:variant_id>/',                views.update_cart_quantity,   name='update_cart_quantity'),
]