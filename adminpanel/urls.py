from django.urls import path
from . import views
from .views import coupon_views, admin_offer_views, admin_sales_views, admin_order_views


urlpatterns = [

    # ── Auth ─────────────────────────────────────────────
    path('login/',   views.admin_login,  name='admin_login'),
    path('logout/',  views.admin_logout, name='admin_logout'),
    path('',         views.dashboard,    name='admin_dashboard'),

    # ── Users ────────────────────────────────────────────
    path('users/',                       views.user_list,          name='admin_user_list'),
    path('users/toggle/<int:user_id>/',  views.toggle_user_status, name='admin_toggle_user'),

    # ── Brands ───────────────────────────────────────────
    path('brands/',                       views.brand_list,        name='admin_brand_list'),
    path('brands/add/',                   views.brand_add,         name='admin_brand_add'),
    path('brands/edit/<int:brand_id>/',   views.brand_edit,        name='admin_brand_edit'),
    path('brands/toggle/<int:brand_id>/', views.brand_toggle,      name='admin_brand_toggle'),
    path('brands/suggestions/',           views.brand_suggestions, name='admin_brand_suggestions'),

    # ── Categories ───────────────────────────────────────
    path('categories/',                          views.category_list,        name='admin_category_list'),
    path('categories/add/',                      views.category_add,         name='admin_category_add'),
    path('categories/edit/<int:category_id>/',   views.category_edit,        name='admin_category_edit'),
    path('categories/toggle/<int:category_id>/', views.category_toggle,      name='admin_category_toggle'),
    path('categories/suggestions/',              views.category_suggestions, name='admin_category_suggestions'),

    # ── Products ─────────────────────────────────────────
    path('products/',                                views.product_list,          name='admin_product_list'),
    path('products/add/',                            views.product_add,           name='admin_product_add'),
    path('products/edit/<int:product_id>/',          views.product_edit,          name='admin_product_edit'),
    path('products/suggestions/',                    views.product_suggestions,   name='admin_product_suggestions'),

    # ── Variants ─────────────────────────────────────────
    path('variants/add/<int:product_id>/',           views.variant_add,           name='admin_variant_add'),
    path('variants/edit/<int:variant_id>/',          views.variant_edit,          name='admin_variant_edit'),
    path('variants/image/add/<int:variant_id>/',     views.variant_image_add,     name='admin_variant_image_add'),
    path('variants/image/delete/<int:image_id>/',    views.variant_image_delete,  name='admin_variant_image_delete'),
    path('products/<int:product_id>/variants/',      views.product_variants,      name='admin_product_variants'),

    # ── Settings ─────────────────────────────────────────
    path('settings/', views.settings, name='admin_settings'),

    # ── Orders ───────────────────────────────────────────
    path('orders/',                     views.admin_order_list,   name='admin_order_list'),
    path('orders/<str:order_number>/',  views.admin_order_detail, name='admin_order_detail'),
    path('orders/return/approve/<str:order_number>/', views.approve_return, name='adminpanel_approve_return'),
    path('orders/<str:order_number>/item/<int:item_id>/approve-return/',
        admin_order_views.admin_approve_item_return, name='admin_approve_item_return'),

    # ── Coupons ──────────────────────────────────────────
    path('coupons/',                    coupon_views.admin_coupon_list,   name='admin_coupon_list'),
    path('coupons/add/',                coupon_views.admin_coupon_add,    name='admin_coupon_add'),
    path('coupons/<int:coupon_id>/edit/',   coupon_views.admin_coupon_edit,   name='admin_coupon_edit'),
    path('coupons/<int:coupon_id>/toggle/', coupon_views.admin_coupon_toggle, name='admin_coupon_toggle'),
    path('coupons/<int:coupon_id>/delete/', coupon_views.admin_coupon_delete, name='admin_coupon_delete'),

    # ── Offers ───────────────────────────────────────────
    path('offers/',                         admin_offer_views.admin_offer_list,           name='admin_offer_list'),

    # Product offers
    path('offers/product/add/',             admin_offer_views.admin_product_offer_add,    name='admin_product_offer_add'),
    path('offers/product/<int:offer_id>/edit/',   admin_offer_views.admin_product_offer_edit,   name='admin_product_offer_edit'),
    path('offers/product/<int:offer_id>/toggle/', admin_offer_views.admin_product_offer_toggle, name='admin_product_offer_toggle'),
    path('offers/product/<int:offer_id>/delete/', admin_offer_views.admin_product_offer_delete, name='admin_product_offer_delete'),



    # Category offers
    path('offers/category/add/',            admin_offer_views.admin_category_offer_add,    name='admin_category_offer_add'),
    path('offers/category/<int:offer_id>/edit/',   admin_offer_views.admin_category_offer_edit,   name='admin_category_offer_edit'),
    path('offers/category/<int:offer_id>/toggle/', admin_offer_views.admin_category_offer_toggle, name='admin_category_offer_toggle'),
    path('offers/category/<int:offer_id>/delete/', admin_offer_views.admin_category_offer_delete, name='admin_category_offer_delete'),

    # ── Sales Report ─────────────────────────────────────
    path('sales/',       admin_sales_views.admin_sales_report, name='admin_sales_report'),
    path('sales/pdf/',   admin_sales_views.admin_sales_pdf,    name='admin_sales_pdf'),
    path('sales/excel/', admin_sales_views.admin_sales_excel,  name='admin_sales_excel'),
]
