# Re-export from the parent adminpanel app's decorators
# so each view file can simply do: from .decorators import admin_required
from adminpanel.decorators import admin_required

__all__ = ['admin_required']