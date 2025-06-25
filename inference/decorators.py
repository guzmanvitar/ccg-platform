"""
Decorators for the inference app
"""

from allauth.account.models import EmailAddress
from django.shortcuts import render


def check_email_verification(view_func):
    """Decorator to check if user's email is verified"""

    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                email_address = EmailAddress.objects.get(
                    user=request.user, primary=True
                )
                if not email_address.verified:
                    return render(
                        request,
                        "account/email_verification_required.html",
                        {"email": email_address.email},
                    )
            except EmailAddress.DoesNotExist:
                return render(
                    request,
                    "account/email_verification_required.html",
                    {"email": request.user.email},
                )
        return view_func(request, *args, **kwargs)

    return wrapper
