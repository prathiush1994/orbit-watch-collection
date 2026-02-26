from allauth.account.adapter import DefaultAccountAdapter


class MyAccountAdapter(DefaultAccountAdapter):
    
    def save_user(self, request, user, form, commit=True):

        user = super().save_user(request, user, form, commit=False)
        
        # Keep user inactive until OTP verification
        user.is_active = False
        
        if commit:
            user.save()
        
        return user