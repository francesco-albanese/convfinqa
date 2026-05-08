from dataclasses import dataclass

from .config import Settings

@dataclass(frozen=True, slots=True)
class Container:
    settings: Settings

    @classmethod
    def bootstrap_application(cls, settings: Settings) -> "Container":
        return cls(
            settings=settings,
        )