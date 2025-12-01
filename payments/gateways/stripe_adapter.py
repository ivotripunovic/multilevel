from decimal import Decimal
from django.http import HttpRequest
from .base import GatewayBase


# lightweight Stripe adapter (lazy imports). Only used if Stripe is installed and selected.
class Gateway(GatewayBase):
    name = "stripe"

    def __init__(self, config: dict = None):
        super().__init__(config=config or {})
        try:
            import stripe  # lazy

            self._stripe = stripe
            stripe.api_key = self.config.get("api_key") or ""
            self._webhook_secret = self.config.get("webhook_secret")
        except Exception:
            self._stripe = None
            self._webhook_secret = None

    def create_checkout_session(self, request: HttpRequest, **kwargs):
        if not self._stripe:
            raise RuntimeError("stripe library not available")
        plan = kwargs.get("plan")
        domain = request.build_absolute_uri("/")[:-1]
        if getattr(plan, "stripe_price_id", None):
            session = self._stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="subscription",
                line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
                success_url=domain + "/subscriptions/success/",
                cancel_url=domain + "/subscriptions/cancel/",
                metadata=kwargs.get("metadata", {}),
                client_reference_id=str(getattr(request.user, "id", ""))
                if request.user.is_authenticated
                else None,
            )
        else:
            amt = int(Decimal(kwargs.get("amount", "0")) * 100)
            session = self._stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="payment",
                line_items=[
                    {
                        "price_data": {
                            "currency": kwargs.get("currency", "USD"),
                            "unit_amount": amt,
                            "product_data": {
                                "name": kwargs.get("description", "Charge")
                            },
                        },
                        "quantity": 1,
                    }
                ],
                success_url=domain + "/subscriptions/success/",
                cancel_url=domain + "/subscriptions/cancel/",
                metadata=kwargs.get("metadata", {}),
                client_reference_id=str(getattr(request.user, "id", ""))
                if request.user.is_authenticated
                else None,
            )
        return {"id": session.id, "url": session.url, "raw": session}

    def parse_webhook(self, request: HttpRequest):
        if not self._stripe:
            raise RuntimeError("stripe library not available")
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = (
                self._stripe.Webhook.construct_event(
                    payload, sig_header, self._webhook_secret
                )
                if self._webhook_secret
                else self._stripe.Event.construct_from(
                    request.json(), self._stripe.api_key
                )
            )
        except Exception:
            raise
        etype = event["type"]
        data = event["data"]["object"]
        # convert amounts (cents) to Decimal dollars if present
        if "amount_paid" in data:
            try:
                data["amount"] = Decimal(data["amount_paid"]) / Decimal("100")
            except Exception:
                data["amount"] = Decimal("0.00")
        elif "amount_total" in data:
            try:
                data["amount"] = Decimal(data["amount_total"]) / Decimal("100")
            except Exception:
                data["amount"] = Decimal("0.00")
        return etype, data
