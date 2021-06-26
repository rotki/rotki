from enum import Enum


class WSMessageType(Enum):
    LEGACY = 1

    def __str__(self) -> str:
        return self.name.lower()
