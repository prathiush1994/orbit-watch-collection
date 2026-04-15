from django.urls import path
from . import views

urlpatterns = [
    path('',        views.wallet_dashboard, name='wallet_dashboard'),
    path('apply/',  views.apply_wallet,     name='apply_wallet'),
    path('remove/', views.remove_wallet,    name='remove_wallet'),
]