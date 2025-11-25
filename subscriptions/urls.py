from django.urls import path
from . import views

app_name = "subscriptions"
urlpatterns = [
    path("create-checkout/<str:plan_key>/", views.create_checkout_session_for_plan, name="create-checkout"),
    path("stripe-webhook/", views.stripe_webhook, name="stripe-webhook"),
    # add success/cancel pages as needed
]