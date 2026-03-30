from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import nested_admin

# Import your home view — adjust the import if yours is different
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # nested_admin URLs — MUST be in this file, not in store/urls.py
    path('nested_admin/', include('nested_admin.urls')),

    # Custom admin panel
    path('adminpanel/', include('adminpanel.urls')),

    # Your app URLs
    path('', views.home, name='home'),
    path('store/', include('store.urls')),
    path('accounts/', include('accounts.urls')),
    path('carts/', include('carts.urls')),
    path('wishlist/', include('wishlist.urls')),
    path('dashboard/', include('dashboard.urls')),

    # allauth
    path('auth/', include('allauth.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)