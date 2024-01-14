from typing import TypedDict, Unpack, overload

from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.mixins.enums import Enum


class DBCacheStatic(Enum):
    """It contains all the keys that don't depend on a variable
    that can be stored in the `key_value_cache` table"""
    LAST_BALANCE_SAVE = 'last_balance_save'
    LAST_DATA_UPLOAD_TS = 'last_data_upload_ts'
    LAST_DATA_UPDATES_TS = 'last_data_updates_ts'
    LAST_OWNED_ASSETS_UPDATE = 'last_owned_assets_update'
    LAST_EVM_ACCOUNTS_DETECT_TS = 'last_evm_accounts_detect_ts'
    LAST_SPAM_ASSETS_DETECT_KEY = 'last_spam_assets_detect_key'
    LAST_AUGMENTED_SPAM_ASSETS_DETECT_KEY = 'last_augmented_spam_assets_detect_key'
    LAST_EVENTS_PROCESSING_TASK_TS = 'last_events_processing_task_ts'
    LAST_PRODUCED_BLOCKS_QUERY_TS = 'last_produced_blocks_query_ts'
    LAST_WITHDRAWALS_EXIT_QUERY_TS = 'last_withdrawals_exit_query_ts'
    LAST_MONERIUM_QUERY_TS = 'last_monerium_query_ts'


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


class DBCacheDynamic(Enum):
    """It contains all the formattable keys that depend on a variable
    that can be stored in the `key_value_cache` table"""
    LAST_CRYPTOTX_OFFSET = '{location}_{location_name}_last_cryptotx_offset'
    LAST_QUERY_TS = '{location}_{location_name}_{account_id}_last_query_ts'
    LAST_QUERY_ID = '{location}_{location_name}_{account_id}_last_query_id'
    WITHDRAWALS_TS = 'ethwithdrawalsts_{address}'
    WITHDRAWALS_IDX = 'ethwithdrawalsidx_{address}'

    @overload
    def get_db_key(self, **kwargs: Unpack[LabeledLocationArgsType]) -> str:
        ...

    @overload
    def get_db_key(self, **kwargs: Unpack[LabeledLocationIdArgsType]) -> str:
        ...

    @overload
    def get_db_key(self, **kwargs: Unpack[AddressArgType]) -> str:
        ...

    def get_db_key(self, **kwargs: str) -> str:
        """Get the key that is used in the DB schema for the given kwargs.

        May Raise KeyError if incompatible kwargs are passed. Pass the kwargs according to the
        supported overloads only. The potential KeyError is handled by type checking. It is
        considered a programming error and it is not handled explicitly."""
        return self.value.format(**kwargs)
