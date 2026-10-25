"""Application errors. Each maps to a JSON body {"error": {code, message, hint}}."""
from __future__ import annotations


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, hint: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.hint = hint


class NotFoundError(AppError):
    def __init__(self, what: str, ident: str):
        super().__init__(404, "not_found", f"{what} '{ident}' was not found.")


class ConflictError(AppError):
    def __init__(self, message: str, hint: str | None = None):
        super().__init__(409, "conflict", message, hint)


class InvalidInputError(AppError):
    def __init__(self, message: str, hint: str | None = None):
        super().__init__(422, "invalid_input", message, hint)


class UnsupportedLanguageError(AppError):
    def __init__(self, message: str, hint: str | None = None):
        super().__init__(422, "unsupported_language", message, hint)


class ProviderUnavailableError(AppError):
    def __init__(self, message: str, hint: str | None = None, code: str = "provider_unavailable"):
        super().__init__(503, code, message, hint)


class ProviderCredentialsMissingError(ProviderUnavailableError):
    def __init__(self, message: str, hint: str | None = None):
        super().__init__(message, hint, code="provider_credentials_missing")


class ProviderOutputInvalidError(AppError):
    def __init__(self, message: str):
        super().__init__(502, "provider_output_invalid", message)
