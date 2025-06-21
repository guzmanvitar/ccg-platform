"""
URL configuration for ccg_platform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView


def verification_sent_view(request):
    """Custom view for email verification sent page"""
    context = {}
    if request.user.is_authenticated:
        context["email"] = request.user.email
    elif "email" in request.session:
        context["email"] = request.session["email"]
    return TemplateView.as_view(template_name="account/verification_sent.html")(
        request, **context
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("inference.urls")),
    path("geoassign/", include("geoassign.urls")),
    # Override allauth verification sent view
    path(
        "accounts/confirm-email/",
        verification_sent_view,
        name="account_email_verification_sent",
    ),
    path("accounts/", include("allauth.urls")),
]
