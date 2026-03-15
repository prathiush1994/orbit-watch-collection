from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import nested_admin
from . import views

urlpatterns = [
    # Django built-in admin
    path('admin/', admin.site.urls),

    # nested_admin URLs (required for nested inline images in admin)
    path('nested_admin/', include('nested_admin.urls')),

    # Custom admin panel
    path('adminpanel/', include('adminpanel.urls')),

    # Main site
    path('', views.home, name='home'),
    path('store/', include('store.urls')),
    path('carts/', include('carts.urls')),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('dashboard/', include('dashboard.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)