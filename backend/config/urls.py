"""Root URL configuration for the Medical Handover Quality Agent API."""

from django.urls import include, path

urlpatterns = [
    path("api/", include("handovers.urls")),
]