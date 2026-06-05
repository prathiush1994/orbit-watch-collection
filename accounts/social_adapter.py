from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter

print("SOCIAL ADAPTER FILE LOADED")


class MyAccountAdapter(DefaultAccountAdapter):

    def populate_username(self, request, user):
        pass

    def save_user(self, request, user, form, commit=True):

        print("ACCOUNT SAVE USER")

        user = super().save_user(
            request,
            user,
            form,
            commit=False,
        )

        user.is_active = True

        if commit:
            user.save()

        return user


class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def is_auto_signup_allowed(self, request, sociallogin):
        print("AUTO SIGNUP ALLOWED")
        return True

    def pre_social_login(self, request, sociallogin):
        print("PRE SOCIAL LOGIN")
        print("EMAIL =", sociallogin.user.email)

    def save_user(self, request, sociallogin, form=None):
        print("SOCIAL SAVE USER")
        return super().save_user(request, sociallogin, form)