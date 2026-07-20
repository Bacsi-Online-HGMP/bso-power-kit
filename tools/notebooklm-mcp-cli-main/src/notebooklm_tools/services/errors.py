"""Service layer errors and exceptions."""


class ServiceError(Exception):
    """Base class for all service layer errors."""

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        hint: str | None = None,
        debug_code: str | None = None,
    ):
        super().__init__(message)
        self.user_message = user_message or message
        self.hint = hint
        self.debug_code = debug_code


class ValidationError(ServiceError):
    """Raised when input parameters are invalid."""

    pass


class NotFoundError(ServiceError):
    """Raised when a resource (notebook, source, etc.) is not found."""

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        hint: str | None = None,
        resource_type: str = "Resource",
        debug_code: str | None = None,
    ):
        if hint is None:
            cmd = "notebook" if resource_type.lower() == "notebook" else resource_type.lower()
            hint = f"Run 'nlm {cmd} list' to see available {cmd}s."
        super().__init__(message, user_message=user_message, hint=hint, debug_code=debug_code)


class CreationError(ServiceError):
    """Raised when a creation operation fails (e.g. fail-fast check)."""

    pass


class ExportError(ServiceError):
    """Raised when an export operation fails."""

    pass
