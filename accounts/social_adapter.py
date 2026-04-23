from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from accounts.models import Account


class MyAccountAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user):
        pass  # No username field in this project

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        user.is_active = False  # Wait for OTP verification
        if commit:
            user.save()
        return user


class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def pre_social_login(self, request, sociallogin):
        """
        If a user with this email already exists, connect the social account
        to them instead of creating a duplicate.
        """
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
        user.last_name  = data.get("family_name", "")
        user.email_verified = True
        user.is_active = True
        user.otp = None
        user.otp_created_at = None
        user.otp_purpose = None
        user.set_unusable_password()
        user.save()
        return user

    def get_login_redirect_url(self, request):
        return "/"