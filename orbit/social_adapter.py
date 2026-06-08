from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from accounts.models import Account
import logging

logger = logging.getLogger(__name__)


class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def is_auto_signup_allowed(self, request, sociallogin):
        logger.warning("AUTO SIGNUP ALLOWED")
        return True

    def pre_social_login(self, request, sociallogin):
        logger.warning("PRE SOCIAL LOGIN")
        logger.warning(f"EMAIL = {sociallogin.user.email}")

        try:
            user = Account.objects.get(email=sociallogin.user.email)

            if not user.is_active:
                user.is_active = True
                user.email_verified = True
                user.save()

        except Account.DoesNotExist:
            pass

    def save_user(self, request, sociallogin, form=None):
        logger.warning("SOCIAL SAVE USER START")

        user = super().save_user(request, sociallogin, form)

        logger.warning(f"USER CREATED: {user.email}")

        user.is_active = True
        user.email_verified = True
        user.save()

        logger.warning("SOCIAL SAVE USER END")

        return user