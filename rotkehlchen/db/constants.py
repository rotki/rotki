from enum import Enum
from typing import Final, Literal

from rotkehlchen.errors.serialization import DeserializationError

KRAKEN_ACCOUNT_TYPE_KEY = 'kraken_account_type'
BINANCE_MARKETS_KEY = 'binance_selected_trade_pairs'
USER_CREDENTIAL_MAPPING_KEYS = (KRAKEN_ACCOUNT_TYPE_KEY, BINANCE_MARKETS_KEY)


# -- EVM transactions attributes values -- used in evm_tx_mappings
EVMTX_DECODED = 0
EVMTX_SPAM = 1

# -- history_events_mappings values --
HISTORY_MAPPING_KEY_STATE = 'state'
HISTORY_MAPPING_STATE_CUSTOMIZED = 1


EVM_ACCOUNTS_DETAILS_LAST_QUERIED_TS = 'last_queried_timestamp'
EVM_ACCOUNTS_DETAILS_TOKENS = 'tokens'

NO_ACCOUNTING_COUNTERPARTY = 'NONE'
LINKABLE_ACCOUNTING_SETTINGS_NAME = Literal[
    'include_gas_costs',
    'include_crypto2crypto',
]
LINKABLE_ACCOUNTING_PROPERTIES = Literal[
    'taxable',
    'count_entire_amount_spend',
    'count_cost_basis_pnl',
]

# Chunk size to use when specifying large numbers of sql variables in a single sql statement.
# The absolute max would be 32766 - see https://www.sqlite.org/limits.html#max_variable_number
SQL_VARIABLE_CHUNK_SIZE: Final = 10000


class UpdateType(Enum):
    SPAM_ASSETS = 'spam_assets'
    RPC_NODES = 'rpc_nodes'
    CONTRACTS = 'contracts'
    GLOBAL_ADDRESSBOOK = 'global_addressbook'
    ACCOUNTING_RULES = 'accounting_rules'
    LOCATION_ASSET_MAPPINGS = 'location_asset_mappings'
    COUNTERPARTY_ASSET_MAPPINGS = 'counterparty_asset_mappings'
    LOCATION_UNSUPPORTED_ASSETS = 'location_unsupported_assets'

    def serialize(self) -> str:
        """Serializes the update type for the DB and API"""
        return f'{self.value}_version'

    @classmethod
    def deserialize(cls: type['UpdateType'], value: str) -> 'UpdateType':
        """Deserialize string from api/DB to UpdateType
        May raise:
        - Deserialization error if value is not a valid UpdateType
        """
        try:
            return cls(value[:-8])  # length of the _version suffix
        except ValueError as e:
            raise DeserializationError(f'Failed to deserialize UpdateTypevalue {value}') from e


# Giving a name for history_events.identifier since without it in the free version case https://github.com/rotki/rotki/issues/7362 we were hitting a no such column: history_events.identifier  # noqa: E501
HISTORY_BASE_ENTRY_FIELDS = 'entry_type, history_events.identifier AS history_events_identifier, event_identifier, sequence_index, timestamp, location, location_label, asset, amount, notes, type, subtype, extra_data, ignored '  # noqa: E501
HISTORY_BASE_ENTRY_LENGTH = 13

EVM_EVENT_FIELDS = 'tx_hash, counterparty, product, address'
EVM_FIELD_LENGTH = 4

ETH_STAKING_EVENT_FIELDS = 'validator_index, is_exit_or_blocknumber'
ETH_STAKING_FIELD_LENGTH = 2

EXTRAINTERNALTXPREFIX: Final = 'extrainternaltx'

# Tuples that contain first the name of a table and then the columns that
# reference assets ids. This is used to query all assets that a user has ever owned.
TABLES_WITH_ASSETS = (
    ('manually_tracked_balances', 'asset'),
    ('margin_positions', 'pl_currency', 'fee_currency'),
    ('timed_balances', 'currency'),
    ('history_events', 'asset'),
)
