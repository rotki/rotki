from collections.abc import Callable
from typing import Any, Final, TypedDict, Unpack, overload

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.constants import EXTRAINTERNALTXPREFIX
from rotkehlchen.types import BTCAddress, ChecksumEvmAddress, Timestamp
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
    LAST_WITHDRAWALS_EXIT_QUERY_TS: Final = 'last_withdrawals_exit_query_ts'
    LAST_MONERIUM_QUERY_TS: Final = 'last_monerium_query_ts'
    LAST_AAVE_V3_ASSETS_UPDATE: Final = 'last_aave_v3_assets_update'
    LAST_DELETE_PAST_CALENDAR_EVENTS: Final = 'last_delete_past_calendar_events'
    LAST_CREATE_REMINDER_CHECK_TS: Final = 'last_create_reminder_check_ts'
    LAST_GRAPH_DELEGATIONS_CHECK_TS: Final = 'last_graph_delegations_check_ts'
    LAST_GNOSISPAY_QUERY_TS: Final = 'last_gnosispay_query_ts'
    LAST_SPARK_ASSETS_UPDATE: Final = 'last_spark_assets_update'
    LAST_DB_UPGRADE: Final = 'last_db_upgrade'


class LabeledLocationArgsType(TypedDict):
    """Type of kwargs, used to get the value of `DBCacheDynamic.LAST_CRYPTOTX_OFFSET`"""
    location: str
    location_name: str


class LabeledLocationIdArgsType(LabeledLocationArgsType):
    """Type of kwargs, used to get the value of `DBCacheDynamic.LAST_QUERY_TS` and `DBCacheDynamic.LAST_QUERY_ID`"""  # noqa: E501
    account_id: str


class AddressArgType(TypedDict):
    """Type of kwargs, used to get the value of `DBCacheDynamic.WITHDRAWALS_TS`, `DBCacheDynamic.WITHDRAWALS_IDX` and `DBCacheDynamic.LAST_BITCOIN_TX_ID`"""  # noqa: E501
    address: ChecksumEvmAddress | BTCAddress


class IndexArgType(TypedDict):
    """Type of kwargs, used to get the value of `DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS`"""
    index: int


class ExtraTxArgType(TypedDict):
    """Type of kwargs, used to get the value of `DBCacheDynamic.EXTRA_INTERNAL_TX`"""
    chain_id: int
    # Receiver is optional since in at least one decoder (rainbow) the receiver address
    # of the needed internal transaction is unknown.
    receiver: ChecksumEvmAddress | None
    tx_hash: str  # using str instead of EVMTxHash because DB schema is in TEXT


class BinancePairLastTradeArgsType(TypedDict):
    """Type of kwargs, used to get the value of `DBCacheDynamic.LAST_CRYPTOTX_OFFSET`"""
    location: str
    location_name: str
    queried_pair: str


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
    EXTRA_INTERNAL_TX: Final = f'{EXTRAINTERNALTXPREFIX}_{{chain_id}}_{{receiver}}_{{tx_hash}}', string_to_evm_address  # noqa: E501
    LAST_PRODUCED_BLOCKS_QUERY_TS: Final = 'last_produced_blocks_query_ts_{index}', _deserialize_timestamp_from_str  # noqa: E501
    BINANCE_PAIR_LAST_ID: Final = '{location}_{location_name}_{queried_pair}', _deserialize_int_from_str  # noqa: E501  # notice that location is added because it can be either binance or binance_us
    LAST_BITCOIN_TX_TS: Final = '{address}_last_tx_ts', _deserialize_timestamp_from_str

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

    @overload
    def get_db_key(self, **kwargs: Unpack[IndexArgType]) -> str:
        ...

    def get_db_key(self, **kwargs: Any) -> str:
        """Get the key that is used in the DB schema for the given kwargs.

        May Raise KeyError if incompatible kwargs are passed. Pass the kwargs according to the
        supported overloads only. The potential KeyError is handled by type checking. It is
        considered a programming error and it is not handled explicitly."""
        return self.value[0].format(**kwargs)

    @property
    def deserialize_callback(self) -> Callable[[str], int | Timestamp | ChecksumEvmAddress | None]:
        return self.value[1]
