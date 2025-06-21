from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom adapter to provide email context to verification sent template"""

    def save_user(self, request, user, form, commit=True):
        """Save user and store email in session for verification sent template"""
        user = super().save_user(request, user, form, commit=False)
        if commit:
            user.save()
            # Store email in session for verification sent template
            request.session["email"] = user.email
            # Make sure session is saved
            request.session.modified = True
        return user


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom social account adapter to handle existing accounts"""

    def pre_social_login(self, request, sociallogin):
        """Handle existing accounts by linking them"""
        # If user is already authenticated, link the social account
        if request.user.is_authenticated:
            sociallogin.connect(request, request.user)
        else:
            # Check if a user with this email already exists
            email = sociallogin.account.extra_data.get("email")
            if email:
                try:
                    # Try to find existing user by email
                    existing_user = EmailAddress.objects.get(email=email).user
                    # Link the social account to the existing user
                    sociallogin.connect(request, existing_user)
                except EmailAddress.DoesNotExist:
                    # No existing user, proceed with normal signup
                    pass
