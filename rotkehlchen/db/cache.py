from collections.abc import Callable
from typing import Final, TypedDict, Unpack, overload

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.constants import EXTRAINTERNALTXPREFIX
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.mixins.enums import Enum


class DBCacheStatic(Enum):
    """It contains all the keys that don't depend on a variable
    that can be stored in the `key_value_cache` table"""
    LAST_BALANCE_SAVE: Final = 'last_balance_save'
    LAST_DATA_UPLOAD_TS: Final = 'last_data_upload_ts'
    LAST_DATA_UPDATES_TS: Final = 'last_data_updates_ts'
    LAST_OWNED_ASSETS_UPDATE: Final = 'last_owned_assets_update'
    LAST_EVM_ACCOUNTS_DETECT_TS: Final = 'last_evm_accounts_detect_ts'
    LAST_SPAM_ASSETS_DETECT_KEY: Final = 'last_spam_assets_detect_key'
    LAST_AUGMENTED_SPAM_ASSETS_DETECT_KEY: Final = 'last_augmented_spam_assets_detect_key'
    LAST_EVENTS_PROCESSING_TASK_TS: Final = 'last_events_processing_task_ts'
    LAST_PRODUCED_BLOCKS_QUERY_TS: Final = 'last_produced_blocks_query_ts'
    LAST_WITHDRAWALS_EXIT_QUERY_TS: Final = 'last_withdrawals_exit_query_ts'
    LAST_MONERIUM_QUERY_TS: Final = 'last_monerium_query_ts'
    LAST_AAVE_V3_ASSETS_UPDATE: Final = 'last_aave_v3_assets_update'
    LAST_DELETE_PAST_CALENDAR_EVENTS: Final = 'last_delete_past_calendar_events'
    LAST_CREATE_REMINDER_CHECK_TS: Final = 'last_create_reminder_check_ts'
    LAST_GRAPH_DELEGATIONS_CHECK_TS: Final = 'last_graph_delegations_check_ts'


class LabeledLocationArgsType(TypedDict):
    """Type of kwargs, used to get the value of `DBCacheDynamic.LAST_CRYPTOTX_OFFSET`"""
    location: str
    location_name: str


class LabeledLocationIdArgsType(LabeledLocationArgsType):
    """Type of kwargs, used to get the value of `DBCacheDynamic.LAST_QUERY_TS` and `DBCacheDynamic.LAST_QUERY_ID`"""  # noqa: E501
    account_id: str


class AddressArgType(TypedDict):
    """Type of kwargs, used to get the value of `DBCacheDynamic.WITHDRAWALS_TS` and `DBCacheDynamic.WITHDRAWALS_IDX`"""  # noqa: E501
    address: ChecksumEvmAddress


class ExtraTxArgType(TypedDict):
    """Type of kwargs, used to get the value of `DBCacheDynamic.EXTRA_INTERNAL_TX`"""
    tx_hash: str  # using str instead of EVMTxHash because DB schema is in TEXT
    receiver: ChecksumEvmAddress


def _deserialize_int_from_str(value: str) -> int | None:
    return int(value)


def _deserialize_timestamp_from_str(value: str) -> Timestamp | None:
    return Timestamp(int(value))


class DBCacheDynamic(Enum):
    """It contains all the formattable keys that depend on a variable
    that can be stored in the `key_value_cache` table"""
    LAST_CRYPTOTX_OFFSET: Final = '{location}_{location_name}_last_cryptotx_offset', _deserialize_int_from_str  # noqa: E501
    LAST_QUERY_TS: Final = '{location}_{location_name}_{account_id}_last_query_ts', _deserialize_timestamp_from_str  # noqa: E501
    LAST_QUERY_ID: Final = '{location}_{location_name}_{account_id}_last_query_id', lambda x: x  # return it as is, a string  # noqa: E501
    LAST_BLOCK_ID: Final = '{location}_{location_name}_{account_id}_last_block_id', _deserialize_int_from_str  # noqa: E501
    WITHDRAWALS_TS: Final = 'ethwithdrawalsts_{address}', _deserialize_timestamp_from_str
    WITHDRAWALS_IDX: Final = 'ethwithdrawalsidx_{address}', _deserialize_int_from_str
    EXTRA_INTERNAL_TX: Final = f'{EXTRAINTERNALTXPREFIX}_{{tx_hash}}_{{receiver}}', string_to_evm_address  # noqa: E501

    @overload
    def get_db_key(self, **kwargs: Unpack[LabeledLocationArgsType]) -> str:
        ...

    @overload
    def get_db_key(self, **kwargs: Unpack[LabeledLocationIdArgsType]) -> str:
        ...

    @overload
    def get_db_key(self, **kwargs: Unpack[AddressArgType]) -> str:
        ...

    @overload
    def get_db_key(self, **kwargs: Unpack[ExtraTxArgType]) -> str:
        ...

    def get_db_key(self, **kwargs: str) -> str:
        """Get the key that is used in the DB schema for the given kwargs.

        May Raise KeyError if incompatible kwargs are passed. Pass the kwargs according to the
        supported overloads only. The potential KeyError is handled by type checking. It is
        considered a programming error and it is not handled explicitly."""
        return self.value[0].format(**kwargs)

    @property
    def deserialize_callback(self) -> Callable[[str], int | Timestamp | ChecksumEvmAddress | None]:
        return self.value[1]
