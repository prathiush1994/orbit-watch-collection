from django.contrib import admin
from django.urls import path, include
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.home, name='home'),

    path('store/', include('store.urls')),
    path('cart/', include('carts.urls')),

    # Your manual auth
    path('accounts/', include('accounts.urls')),

    # Google auth
    path('auth/', include('allauth.urls')),

    path('dashboard/', include('dashboard.urls')),

    path('adminpanel/', include('adminpanel.urls')),
] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT) 