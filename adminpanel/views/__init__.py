from .auth_views      import admin_login, admin_logout
from .dashboard_views import dashboard
from .user_views      import user_list, toggle_user_status
from .settings_views  import settings
from .brand_views     import brand_list, brand_add, brand_edit, brand_toggle, brand_suggestions
from .category_views  import category_list, category_add, category_edit, category_toggle, category_suggestions
from .product_views   import (
    product_list, product_add, product_edit, product_suggestions,
    variant_add, variant_edit, variant_image_add, variant_image_delete, product_variants
)
from .admin_order_views import *
from .adminpanel_approve_return import *
from .coupon_views import *