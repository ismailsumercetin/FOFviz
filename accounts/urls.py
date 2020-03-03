"""
This file created manually
"""

# accounts/urls.py
from django.urls import path
from . import views


urlpatterns = [
    path('signup/', views.SignUp.as_view(), name='signup'),
    path('password/', views.change_password, name='change_password'),


]
