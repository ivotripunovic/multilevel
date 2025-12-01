from typing import Tuple, Dict, Any
from django.http import HttpRequest


class GatewayBase:
    """
    Abstract payment gateway interface.

    Implementations must provide:
      - create_checkout_session(request, **kwargs) -> dict
      - parse_webhook(request: HttpRequest) -> Tuple[str, Dict[str, Any]]
    """

    name = "base"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    def create_checkout_session(self, request: HttpRequest, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError()

    def parse_webhook(self, request: HttpRequest) -> Tuple[str, Dict[str, Any]]:
        raise NotImplementedError()
