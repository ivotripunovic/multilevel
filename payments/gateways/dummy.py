from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from django.http import HttpRequest
from .base import GatewayBase


class DummyGateway(GatewayBase):
    """
    Simple gateway used for local/dev testing.
    create_checkout_session returns a local success url; parse_webhook accepts JSON or form with 'event' and 'amount'.
    """
    name = "dummy"

    def create_checkout_session(self, request: HttpRequest, **kwargs):
        session_id = f"dummy-{int(timezone.now().timestamp())}"
        success_url = request.build_absolute_uri(reverse("subscriptions:checkout_success")) if request.user.is_authenticated else request.build_absolute_uri("/")
        return {"id": session_id, "url": success_url, "metadata": kwargs.get("metadata", {})}

    def parse_webhook(self, request: HttpRequest):
        # try JSON first
        try:
            payload = request.json()
        except Exception:
            payload = request.POST.dict() if hasattr(request, "POST") else {}

        event_type = payload.get("event") or payload.get("type")
        data = dict(payload)
        # normalize amount to Decimal if present
        if "amount" in data:
            try:
                data["amount"] = Decimal(str(data["amount"]))
            except Exception:
                data["amount"] = Decimal("0.00")
        return event_type, data