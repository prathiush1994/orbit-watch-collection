from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
import logging

logger = logging.getLogger(__name__)

logger.warning("SOCIAL ADAPTER FILE LOADED")


class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def __init__(self, *args, **kwargs):
        logger.warning("SOCIAL ADAPTER INSTANCE CREATED")
        super().__init__(*args, **kwargs)

    def is_auto_signup_allowed(self, request, sociallogin):
        logger.warning("AUTO SIGNUP ALLOWED")
        return True

    def pre_social_login(self, request, sociallogin):
        logger.warning("PRE SOCIAL LOGIN")

    def save_user(self, request, sociallogin, form=None):
        logger.warning("SOCIAL SAVE USER")
        return super().save_user(request, sociallogin, form)