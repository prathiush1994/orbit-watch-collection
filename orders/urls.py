from django.urls import path
from . import views

urlpatterns = [
    path('checkout/',                            views.checkout,       name='checkout'),
    path('place-order/',                         views.place_order,    name='place_order'),
    path('complete/<str:order_number>/',         views.order_complete, name='order_complete'),
]