from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
import logging

logger = logging.getLogger(__name__)

logger.warning("SOCIAL ADAPTER FILE LOADED")


class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def is_auto_signup_allowed(self, request, sociallogin):
        logger.warning("AUTO SIGNUP ALLOWED")
        print("logger.warning(AUTO SIGNUP ALLOWED)")
        return True

    def pre_social_login(self, request, sociallogin):
        logger.warning("PRE SOCIAL LOGIN")
        logger.warning(f"EMAIL = {sociallogin.user.email}")
        print("logger.warning(PRE SOCIAL LOGIN) /n logger.warning()",f"EMAIL = {sociallogin.user.email}")

    def save_user(self, request, sociallogin, form=None):
        logger.warning("SOCIAL SAVE USER")
        print("logger.warning(SOCIAL SAVE USER)")
        return super().save_user(request, sociallogin, form)