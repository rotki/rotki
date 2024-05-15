from typing import Any


class RotkehlchenPermissionError(Exception):
    """Raised at login if we need additional data from the user

    The payload contains information to be shown to the user by the frontend so
    they can decide what to do
    """
    def __init__(self, error_message: str, payload: dict[str, Any] | None) -> None:
        super().__init__(error_message)
        self.error_message = error_message
        self.message_payload = payload if payload is not None else {}


class AuthenticationError(Exception):
    pass


class PremiumAuthenticationError(Exception):
    pass


class PremiumApiError(Exception):
    pass


class PremiumPermissionError(Exception):
    pass


class IncorrectApiKeyFormat(Exception):
    pass


class APIKeyNotConfigured(Exception):
    """API key for service not provided"""
