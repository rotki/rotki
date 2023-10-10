from enum import Enum
from typing import Final, Literal

from rotkehlchen.errors.serialization import DeserializationError

KRAKEN_ACCOUNT_TYPE_KEY = 'kraken_account_type'
BINANCE_MARKETS_KEY = 'binance_selected_trade_pairs'
USER_CREDENTIAL_MAPPING_KEYS = (KRAKEN_ACCOUNT_TYPE_KEY, BINANCE_MARKETS_KEY)

# -- history_events_mappings values --
HISTORY_MAPPING_KEY_STATE = 'state'
HISTORY_MAPPING_STATE_DECODED = 0
HISTORY_MAPPING_STATE_CUSTOMIZED = 1


EVM_ACCOUNTS_DETAILS_LAST_QUERIED_TS = 'last_queried_timestamp'
EVM_ACCOUNTS_DETAILS_TOKENS = 'tokens'

LAST_DATA_UPDATES_KEY: Final = 'last_data_updates_ts'

NO_ACCOUNTING_COUNTERPARTY = 'NONE'
LINKABLE_ACCOUNTING_SETTINGS_NAME = Literal[
    'include_gas_costs',
    'include_crypto2crypto',
]
LINKABLE_ACCOUNTING_PROPERTIES = Literal[
    'count_entire_amount_spend',
    'count_cost_basis_pnl',
]


class UpdateType(Enum):
    SPAM_ASSETS = 'spam_assets'
    RPC_NODES = 'rpc_nodes'
    CONTRACTS = 'contracts'
    GLOBAL_ADDRESSBOOK = 'global_addressbook'
    ACCOUNTING_RULES = 'accounting_rules'

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
