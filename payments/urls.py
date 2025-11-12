from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="payments-index"),
    path("create/", views.create_payment_view, name="payments-create"),
]