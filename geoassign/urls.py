"""
URL configuration for geoassign app
"""

from django.urls import path

from .api.views import GeographicAssignmentView, health_check, test_pipeline

app_name = "geoassign"

urlpatterns = [
    # API endpoints
    path(
        "api/assign/", GeographicAssignmentView.as_view(), name="geographic_assignment"
    ),
    path("api/health/", health_check, name="health_check"),
    path("api/test/", test_pipeline, name="test_pipeline"),
]
