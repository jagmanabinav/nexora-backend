from typing import Any, Optional


class NexoraException(Exception):
    """Base exception for Nexora application."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        fields: Optional[list[dict[str, Any]]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.fields = fields or []
        super().__init__(self.message)


class ValidationException(NexoraException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        fields: Optional[list[dict[str, Any]]] = None,
    ):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=422,
            fields=fields,
        )


class AuthenticationException(NexoraException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            code="AUTHENTICATION_FAILED",
            message=message,
            status_code=401,
        )


class AuthorizationException(NexoraException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            code="AUTHORIZATION_FAILED",
            message=message,
            status_code=403,
        )


class ResourceNotFoundException(NexoraException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str = "Resource", identifier: Any = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(
            code="NOT_FOUND",
            message=message,
            status_code=404,
        )


class ConflictException(NexoraException):
    """Raised when a conflict occurs (e.g., duplicate record)."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=409,
        )


class TenantIsolationViolation(NexoraException):
    """Raised when tenant isolation boundary is violated."""

    def __init__(self, message: str = "Tenant isolation violation"):
        super().__init__(
            code="TENANT_ISOLATION_VIOLATION",
            message=message,
            status_code=403,
        )


class InvalidStateException(NexoraException):
    """Raised when an operation is invalid for the current state."""

    def __init__(self, message: str = "Invalid state for operation"):
        super().__init__(
            code="INVALID_STATE",
            message=message,
            status_code=400,
        )


class DatabaseException(NexoraException):
    """Raised when database operations fail."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            code="DATABASE_ERROR",
            message=message,
            status_code=500,
        )


class ExternalServiceException(NexoraException):
    """Raised when external service calls fail."""

    def __init__(self, service: str, message: str = "External service error"):
        super().__init__(
            code="EXTERNAL_SERVICE_ERROR",
            message=f"{service}: {message}",
            status_code=502,
        )
