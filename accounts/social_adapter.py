from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from accounts.models import Account


class MyAccountAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user):
        pass  # No username field in this project

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        user.is_active = False  
        if commit:
            user.save()
        return user


class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def is_auto_signup_allowed(self, request, sociallogin):
        return True
