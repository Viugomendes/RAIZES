"""Addresses without a language prefix: the password page and leaving."""
from django.urls import path

from . import views

app_name = "access"

urlpatterns = [
    path("entrar/", views.enter, name="enter"),
    path("sair/", views.leave, name="leave"),
]
