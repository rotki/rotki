from enum import Enum
from typing import Final, Literal

from rotkehlchen.errors.serialization import DeserializationError

KDF_ITER: Final = 64000

KRAKEN_ACCOUNT_TYPE_KEY: Final = 'kraken_account_type'
OKX_LOCATION_KEY: Final = 'okx_location'
BINANCE_MARKETS_KEY: Final = 'binance_selected_trade_pairs'
USER_CREDENTIAL_MAPPING_KEYS: Final = (KRAKEN_ACCOUNT_TYPE_KEY, BINANCE_MARKETS_KEY, OKX_LOCATION_KEY)  # noqa: E501


# -- EVM transactions attributes values -- used in evm_tx_mappings
TX_DECODED: Final = 0
TX_SPAM: Final = 1

# -- history_events_mappings values --
HISTORY_MAPPING_KEY_STATE: Final = 'state'
HISTORY_MAPPING_STATE_CUSTOMIZED: Final = 1


EVM_ACCOUNTS_DETAILS_LAST_QUERIED_TS: Final = 'last_queried_timestamp'
EVM_ACCOUNTS_DETAILS_TOKENS: Final = 'tokens'

# sqlite treats NULLs as different values in UNIQUE checks.
# we use "NONE" instead of NULL so that only one "no value" row can exist.
NO_ACCOUNTING_COUNTERPARTY: Final = 'NONE'
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
HISTORY_BASE_ENTRY_FIELDS: Final = 'entry_type, history_events.identifier AS history_events_identifier, event_identifier, sequence_index, timestamp, location, location_label, asset, amount, notes, type, subtype, extra_data, ignored '  # noqa: E501
HISTORY_BASE_ENTRY_LENGTH: Final = 13

CHAIN_EVENT_FIELDS: Final = 'tx_ref, counterparty, address'
CHAIN_FIELD_LENGTH: Final = 3

ETH_STAKING_EVENT_FIELDS: Final = 'validator_index, is_exit_or_blocknumber'
ETH_STAKING_FIELD_LENGTH: Final = 2

EXTRAINTERNALTXPREFIX: Final = 'extrainternaltx'
