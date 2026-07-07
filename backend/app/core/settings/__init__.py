from pydantic import BaseModel


class BaseConfig(BaseModel):
    model_config = {"extra": "ignore"}


def __getattr__(name):
    if name == "settings":
        from app.core.loader import settings as _settings
        return _settings
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseConfig",
]
