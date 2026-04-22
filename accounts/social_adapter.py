from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from accounts.models import Account


class MyAccountAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user):
        # We don't use username — skip this
        pass

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        # Keep user inactive until OTP verification
        user.is_active = False
        if commit:
            user.save()
        return user


class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def pre_social_login(self, request, sociallogin):
        # User already exists — just connect and log them in, skip signup page
        if sociallogin.is_existing:
            return
        try:
            email = sociallogin.account.extra_data.get("email", "")
            user = Account.objects.get(email=email)
            sociallogin.connect(request, user)
        except Account.DoesNotExist:
            pass

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        data = sociallogin.account.extra_data
        user.first_name = data.get("given_name", "")
        user.last_name = data.get("family_name", "")
        user.email_verified = True
        user.is_active = True
        user.otp = None
        user.otp_created_at = None
        user.otp_purpose = None
        user.set_unusable_password()
        user.save()
        return user

    def get_login_redirect_url(self, request):
        # After Google login succeeds, merge session cart → user cart
        # and merge session wishlist → user wishlist
        _merge_cart_on_login(request)
        _merge_wishlist_on_login(request)
        return "/"


def _merge_cart_on_login(request):
    try:
        from carts.models import Cart, CartItem

        session_key = request.session.session_key
        if not session_key:
            return

        session_cart = Cart.objects.filter(cart_id=session_key).first()
        if not session_cart:
            return

        user_cart, _ = Cart.objects.get_or_create(user=request.user)

        for item in CartItem.objects.filter(cart=session_cart):
            user_item, created = CartItem.objects.get_or_create(
                cart=user_cart,
                variant=item.variant,
            )
            if not created:
                # Add quantities but respect per-product limit of 3
                new_qty = min(user_item.quantity + item.quantity, 3)
                user_item.quantity = new_qty
            else:
                user_item.quantity = min(item.quantity, 3)
            user_item.save()

        session_cart.delete()

    except Exception:
        pass  # Never break login because of a cart error


def _merge_wishlist_on_login(request):
    try:
        from wishlist.models import Wishlist

        pending = request.session.pop("pending_wishlist", [])
        for variant_id in pending:
            Wishlist.objects.get_or_create(
                user=request.user,
                variant_id=variant_id,
            )

    except Exception:
        pass  # Never break login because of a wishlist error
