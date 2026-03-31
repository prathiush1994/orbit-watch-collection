from django.urls import path
from . import views

urlpatterns = [
    path('checkout/',                             views.checkout,          name='checkout'),
    path('place-order/',                          views.place_order,       name='place_order'),
    path('complete/<str:order_number>/',          views.order_complete,    name='order_complete'),
    path('my-orders/',                            views.my_orders,         name='my_orders'),
    path('detail/<str:order_number>/',            views.order_detail,      name='order_detail'),
    path('cancel/<str:order_number>/',            views.cancel_order,      name='cancel_order'),
    path('return/<str:order_number>/',            views.return_order,      name='return_order'),
    path('invoice/<str:order_number>/',           views.download_invoice,  name='download_invoice'),
]