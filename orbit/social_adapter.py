from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from accounts.models import Account


class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def pre_social_login(self, request, sociallogin):
        try:
            user = Account.objects.get(email=sociallogin.user.email)

            if not user.is_active:
                user.is_active = True
                user.email_verified = True
                user.save()

        except Account.DoesNotExist:
            pass

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        user.is_active = True
        user.email_verified = True
        user.save()

        return user