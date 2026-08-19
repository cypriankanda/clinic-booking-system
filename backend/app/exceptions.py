class AppError(Exception):
    """Base class for all handled domain errors. Carries an HTTP status and a
    machine-readable code so error_handlers.py can map it consistently."""

    status_code = 400
    error_code = "APP_ERROR"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404
    error_code = "NOT_FOUND"


class ValidationFailedError(AppError):
    """Business-rule validation failure (outside working hours, in the past,
    within the booking-notice buffer, malformed slot alignment, etc.)."""

    status_code = 422
    error_code = "VALIDATION_FAILED"


class ConflictError(AppError):
    """Slot already booked, or an action attempted on an already-cancelled
    appointment."""

    status_code = 409
    error_code = "CONFLICT"
