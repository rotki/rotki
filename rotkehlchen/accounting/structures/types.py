
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.utils.mixins.enums import DBCharEnumMixIn


class ActionType(DBCharEnumMixIn):
    TRADE = 1
    ASSET_MOVEMENT = 2
    HISTORY_EVENT = 3
    # ledger action that was removed was 4

    def serialize(self) -> str:
        return self.name.lower()

    @classmethod
    def deserialize(cls, value: str) -> 'ActionType':
        try:
            return getattr(cls, value.upper())
        except AttributeError as e:
            raise DeserializationError(f'Failed to deserialize {cls.__name__} value {value}') from e  # noqa: E501
