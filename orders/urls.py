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

    # Coupon (AJAX)
    path('apply-coupon/',                        views.apply_coupon,    name='apply_coupon'),
    path('remove-coupon/',                       views.remove_coupon,   name='remove_coupon'),

    # Result pages
    path('complete/<str:order_number>/',       views.order_complete,     name='order_complete'),
    path('success/<str:order_number>/',        views.payment_success,    name='payment_success'),
    path('failed/',                            views.payment_failed,     name='payment_failed'),

    # Razorpay callback
    path('razorpay/callback/',                 views.razorpay_callback,  name='razorpay_callback'),

]