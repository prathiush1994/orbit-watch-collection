from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/',   views.admin_login,  name='admin_login'),
    path('logout/',  views.admin_logout, name='admin_logout'),

    # Dashboard
    path('',         views.dashboard,    name='admin_dashboard'),

    # Users
    path('users/',                        views.user_list,          name='admin_user_list'),
    path('users/toggle/<int:user_id>/',   views.toggle_user_status, name='admin_toggle_user'),

    # Settings
    path('settings/', views.settings,    name='admin_settings'),
]