from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
import logging

logger = logging.getLogger(__name__)

logger.warning("SOCIAL ADAPTER FILE LOADED")


class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def on_authentication_error(
        self,
        request,
        provider,
        error=None,
        exception=None,
        extra_context=None,
    ):
        logger.error(f"PROVIDER = {provider}")
        logger.error(f"ERROR = {error}")
        logger.error(f"EXCEPTION = {exception}")
        logger.error(f"EXTRA_CONTEXT = {extra_context}")

        return super().on_authentication_error(
            request,
            provider,
            error,
            exception,
            extra_context,
        )
    
    def pre_social_login(self, request, sociallogin):
    logger.error("PRE SOCIAL LOGIN REACHED")
    logger.error(f"EMAIL={sociallogin.user.email}")