# Register built-in adapters so get_gateway can find them by name
from .registry import register_gateway
from .dummy import DummyGateway

register_gateway("dummy", DummyGateway)

# Attempt to register stripe adapter if available
try:
    from .stripe_adapter import Gateway as StripeGateway
    register_gateway("stripe", StripeGateway)
except Exception:
    # stripe adapter not available until dependencies are installed
    pass