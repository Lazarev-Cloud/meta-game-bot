"""
Custom exception classes for the Flow Engine.

Defines a hierarchy of flow-related errors used to manage validation and flow control.
"""


class FlowEngineError(Exception):
    """Base class for all exceptions raised by the Flow Engine."""

    pass


class NameTooShortError(FlowEngineError):
    """Raised when a provided name is too short to meet validation criteria."""

    pass


class InvalidEmailError(FlowEngineError):
    """Raised when a provided email does not match the expected format."""

    pass
