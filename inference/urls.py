from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("panthera-onca/", views.jaguar_tools, name="jaguar_tools"),
    path("upload/", views.upload_data, name="upload_data"),
    path(
        "geographic-inference/",
        views.run_geographic_inference,
        name="geographic_inference",
    ),
    path(
        "results/<str:file_hash>/",
        views.view_inference_results,
        name="view_inference_results",
    ),
]
