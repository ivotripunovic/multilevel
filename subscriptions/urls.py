from django.urls import path
from . import views

app_name = "subscriptions"
urlpatterns = [
    path("checkout/<str:plan_key>/", views.create_checkout_session_for_plan, name="checkout"),
    path("cancel/<int:subscription_id>/", views.cancel_subscription, name="cancel"),
    path("success/", views.checkout_success, name="checkout_success"),
    path("cancel-page/", views.checkout_cancel, name="checkout_cancel"),
    path("webhook/", views.gateway_webhook, name="gateway_webhook"),
]