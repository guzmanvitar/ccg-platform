from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('panthera-onca/', views.jaguar_tools, name='jaguar_tools'),
]