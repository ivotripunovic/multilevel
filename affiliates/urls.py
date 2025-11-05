from django.urls import path
from . import views

urlpatterns = [
    # /register/ -> affiliates.views.register_view
    path("", views.register_view, name="affiliates-register"),
]