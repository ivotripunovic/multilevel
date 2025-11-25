from typing import Dict
from django.conf import settings

_GATEWAY_CLASSES: Dict[str, type] = {}


def register_gateway(name: str, cls: type):
    _GATEWAY_CLASSES[name] = cls


def get_gateway(name: str = None, config: dict = None):
    """
    Return an instance of the selected gateway.
    Falls back to Dummy gateway.
    """
    selected = name or getattr(settings, "PAYMENT_GATEWAY", "dummy")
    config = config or getattr(settings, "PAYMENT_GATEWAY_CONFIG", {}) or {}

    # try registry first
    cls = _GATEWAY_CLASSES.get(selected)
    if cls:
        return cls(config=config)

    # try dynamic import payments.gateways.<selected>.Gateway
    try:
        module = __import__(f"payments.gateways.{selected}", fromlist=["Gateway"])
        if hasattr(module, "Gateway"):
            return getattr(module, "Gateway")(config=config)
    except Exception:
        pass

    # fallback to built-in dummy
    from .dummy import DummyGateway

    return DummyGateway(config=config)