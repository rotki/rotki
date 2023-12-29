from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.mixins.enums import Enum


class DBCache(Enum):
    """It contains all the values that can be stored in the `key_value_cache` table of the DB"""
    LAST_BALANCE_SAVE = 'last_balance_save'
    LAST_DATA_UPLOAD_TS = 'last_data_upload_ts'
    LAST_DATA_UPDATES_TS = 'last_data_updates_ts'
    LAST_OWNED_ASSETS_UPDATE = 'last_owned_assets_update'
    LAST_EVM_ACCOUNTS_DETECT_TS = 'last_evm_accounts_detect_ts'
    LAST_SPAM_ASSETS_DETECT_KEY = 'last_spam_assets_detect_key'
    LAST_AUGMENTED_SPAM_ASSETS_DETECT_KEY = 'last_augmented_spam_assets_detect_key'

    @classmethod
    def deserialize(cls: type['DBCache'], value: str) -> 'DBCache':
        """The method to deserialize a string to an enum object"""
        try:
            return getattr(cls, value.upper())
        except AttributeError as e:
            raise DeserializationError(f'Failed to deserialize {cls.__name__} value {value}') from e  # noqa: E501


def serialize_cache_for_api(cache: dict[DBCache, int]) -> dict[str, Timestamp]:
    """Serialize the cache for /settings API consumption."""
    return {
        DBCache.LAST_DATA_UPLOAD_TS.value: Timestamp(cache.get(DBCache.LAST_DATA_UPLOAD_TS, 0)),
        DBCache.LAST_BALANCE_SAVE.value: Timestamp(cache.get(DBCache.LAST_BALANCE_SAVE, 0)),
    }
