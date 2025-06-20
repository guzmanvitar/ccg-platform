from allauth.account.adapter import DefaultAccountAdapter


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
