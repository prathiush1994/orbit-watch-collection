from django.urls import path
from . import views

urlpatterns = [
    # Referral (AJAX)
    path("apply-referral/",     views.apply_referral,     name="apply_referral"),
    path("remove-referral/",    views.remove_referral,    name="remove_referral"),
]