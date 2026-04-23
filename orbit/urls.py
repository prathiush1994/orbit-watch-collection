from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
import nested_admin
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    # Nested admin (must be here)
    path("nested_admin/", include("nested_admin.urls")),
    # Custom admin panel
    path("adminpanel/", include("adminpanel.urls")),
    # Main routes
    path("", views.home, name="home"),
    path("store/", include("store.urls")),
    path("user/", include("accounts.urls")),
    path("carts/", include("carts.urls")),
    path("wishlist/", include("wishlist.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("orders/", include("orders.urls")),
    path("wallet/", include("wallet.urls")),
    path("inventory/", include("inventory.urls")),
    path("accounts/", include("allauth.urls")),
    path("reviews/", include("reviews.urls")),
]


# Media files (development only)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
