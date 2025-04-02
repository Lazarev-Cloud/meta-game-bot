class FlowEngineError(Exception):
    """Базовый класс всех ошибок Flow Engine."""
    pass


class NameTooShortError(FlowEngineError):
    """Имя слишком короткое."""
    pass


class InvalidEmailError(FlowEngineError):
    """Неверный email."""
    pass
