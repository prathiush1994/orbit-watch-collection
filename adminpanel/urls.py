from django.urls import path
from . import views


urlpatterns = [
    path('login/',   views.admin_login,  name='admin_login'),
    path('logout/',  views.admin_logout, name='admin_logout'),
    path('',         views.dashboard,    name='admin_dashboard'),

    path('users/',                       views.user_list,          name='admin_user_list'),
    path('users/toggle/<int:user_id>/',  views.toggle_user_status, name='admin_toggle_user'),

    path('brands/',                       views.brand_list,        name='admin_brand_list'),
    path('brands/add/',                   views.brand_add,         name='admin_brand_add'),
    path('brands/edit/<int:brand_id>/',   views.brand_edit,        name='admin_brand_edit'),
    path('brands/toggle/<int:brand_id>/', views.brand_toggle,      name='admin_brand_toggle'),
    path('brands/suggestions/',           views.brand_suggestions, name='admin_brand_suggestions'),

    path('categories/',                          views.category_list,        name='admin_category_list'),
    path('categories/add/',                      views.category_add,         name='admin_category_add'),
    path('categories/edit/<int:category_id>/',   views.category_edit,        name='admin_category_edit'),
    path('categories/toggle/<int:category_id>/', views.category_toggle,      name='admin_category_toggle'),
    path('categories/suggestions/',              views.category_suggestions, name='admin_category_suggestions'),

    path('products/',                                views.product_list,          name='admin_product_list'),
    path('products/add/',                            views.product_add,           name='admin_product_add'),
    path('products/edit/<int:product_id>/',          views.product_edit,          name='admin_product_edit'),
    path('products/suggestions/',                    views.product_suggestions,   name='admin_product_suggestions'),

    path('variants/add/<int:product_id>/',           views.variant_add,           name='admin_variant_add'),
    path('variants/edit/<int:variant_id>/',          views.variant_edit,          name='admin_variant_edit'),
    path('variants/image/add/<int:variant_id>/',     views.variant_image_add,     name='admin_variant_image_add'),
    path('variants/image/delete/<int:image_id>/',    views.variant_image_delete,  name='admin_variant_image_delete'),

    path('products/<int:product_id>/variants/',       views.product_variants,     name='admin_product_variants'),


    path('settings/', views.settings, name='admin_settings'),

    path('orders/',                     views.admin_order_list,   name='admin_order_list'),
    path('orders/<str:order_number>/',  views.admin_order_detail, name='admin_order_detail'),
]