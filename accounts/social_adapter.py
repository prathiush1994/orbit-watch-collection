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
        print("GOOGLE ADAPTER REACHED")
        print(sociallogin.account.extra_data)
        print("GOOGLE ADAPTER REACHED")
        print("EMAIL =", sociallogin.account.extra_data.get("email"))
        return True
