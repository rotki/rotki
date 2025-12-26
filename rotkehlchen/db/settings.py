import json
import logging
from collections.abc import Mapping, Sequence
from contextvars import ContextVar
from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING, Any, ClassVar, Final, Literal, NamedTuple, Optional

from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.chain.evm.types import (
    DEFAULT_EVM_INDEXER_ORDER,
    DEFAULT_INDEXERS_ORDER,
    EvmIndexer,
    SerializableChainIndexerOrder,
)
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.timing import DAY_IN_SECONDS, YEAR_IN_SECONDS
from rotkehlchen.data_migrations.constants import LAST_USERDB_DATA_MIGRATION
from rotkehlchen.db.constants import UpdateType
from rotkehlchen.db.utils import str_to_bool
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.types import DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER, HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.oracles.structures import DEFAULT_CURRENT_PRICE_ORACLES_ORDER, CurrentPriceOracle
from rotkehlchen.types import (
    AVAILABLE_MODULES_MAP,
    DEFAULT_ADDRESS_NAME_PRIORITY,
    DEFAULT_OFF_MODULES,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    AddressNameSource,
    ChainID,
    CostBasisMethod,
    ExchangeLocationID,
    ModuleName,
    SupportedBlockchain,
    Timestamp,
)

if TYPE_CHECKING:
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

ROTKEHLCHEN_DB_VERSION: Final = 51
ROTKEHLCHEN_TRANSIENT_DB_VERSION: Final = 2
DEFAULT_TAXFREE_AFTER_PERIOD: Final = YEAR_IN_SECONDS
DEFAULT_INCLUDE_CRYPTO2CRYPTO: Final = True
DEFAULT_INCLUDE_GAS_COSTS: Final = True
DEFAULT_PREMIUM_SHOULD_SYNC: Final = False
DEFAULT_UI_FLOATING_PRECISION: Final = 2
DEFAULT_BALANCE_SAVE_FREQUENCY: Final = 24
DEFAULT_MAIN_CURRENCY: Final = A_USD
DEFAULT_DATE_DISPLAY_FORMAT: Final = '%d/%m/%Y %H:%M:%S %Z'
DEFAULT_SUBMIT_USAGE_ANALYTICS: Final = True
DEFAULT_ACTIVE_MODULES: Final = tuple(set(AVAILABLE_MODULES_MAP.keys()) - DEFAULT_OFF_MODULES)
DEFAULT_BTC_DERIVATION_GAP_LIMIT: Final = 20
DEFAULT_CALCULATE_PAST_COST_BASIS: Final = True
DEFAULT_DISPLAY_DATE_IN_LOCALTIME: Final = True
DEFAULT_CURRENT_PRICE_ORACLES: Final = DEFAULT_CURRENT_PRICE_ORACLES_ORDER
DEFAULT_HISTORICAL_PRICE_ORACLES: Final = DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER
DEFAULT_PNL_CSV_WITH_FORMULAS: Final = True
DEFAULT_PNL_CSV_HAVE_SUMMARY: Final = False
DEFAULT_SSF_GRAPH_MULTIPLIER: Final = 0
DEFAULT_LAST_DATA_MIGRATION: Final = LAST_USERDB_DATA_MIGRATION
DEFAULT_COST_BASIS_METHOD: Final = CostBasisMethod.FIFO
DEFAULT_TREAT_ETH2_AS_ETH: Final = True
DEFAULT_ETH_STAKING_TAXABLE_AFTER_WITHDRAWAL_ENABLED: Final = True
DEFAULT_INCLUDE_FEES_IN_COST_BASIS: Final = True
DEFAULT_INFER_ZERO_TIMED_BALANCES: Final = False  # If True the asset amount and value chart shows the 0 balance periods for an asset  # noqa: E501
DEFAULT_QUERY_RETRY_LIMIT: Final = 5
DEFAULT_CONNECT_TIMEOUT: Final = 30
DEFAULT_READ_TIMEOUT: Final = 30
DEFAULT_ORACLE_PENALTY_THRESHOLD_COUNT: Final = 5
DEFAULT_ORACLE_PENALTY_DURATION: Final = 1800
DEFAULT_AUTO_DELETE_CALENDAR_ENTRIES: Final = True
DEFAULT_AUTO_CREATE_CALENDAR_REMINDERS: Final = True
DEFAULT_ASK_USER_UPON_SIZE_DISCREPANCY: Final = True
DEFAULT_AUTO_DETECT_TOKENS: Final = True
DEFAULT_CSV_EXPORT_DELIMITER: Final = ','
DEFAULT_EVENTS_PROCESSING_FREQUENCY: Final = DAY_IN_SECONDS

LIST_KEYS: Final = (
    'current_price_oracles',
    'historical_price_oracles',
    'non_syncing_exchanges',
    'evmchains_to_skip_detection',
    'default_evm_indexer_order',
)
JSON_KEYS: Final = ('evm_indexers_order',)
BOOLEAN_KEYS: Final = (
    'have_premium',
    'include_crypto2crypto',
    'include_gas_costs',
    'premium_should_sync',
    'submit_usage_analytics',
    'calculate_past_cost_basis',
    'display_date_in_localtime',
    'pnl_csv_with_formulas',
    'pnl_csv_have_summary',
    'treat_eth2_as_eth',
    'eth_staking_taxable_after_withdrawal_enabled',
    'include_fees_in_cost_basis',
    'infer_zero_timed_balances',
    'auto_delete_calendar_entries',
    'auto_create_calendar_reminders',
    'ask_user_upon_size_discrepancy',
    'auto_detect_tokens',
)
INTEGER_KEYS: Final = (
    'version',
    'ui_floating_precision',
    'balance_save_frequency',
    'btc_derivation_gap_limit',
    'ssf_graph_multiplier',
    'last_data_migration',
    'query_retry_limit',
    'connect_timeout',
    'read_timeout',
    'oracle_penalty_threshold_count',
    'oracle_penalty_duration',
    'events_processing_frequency',
)
STRING_KEYS: Final = (
    'ksm_rpc_endpoint',
    'dot_rpc_endpoint',
    'beacon_rpc_endpoint',
    'btc_mempool_api',
    'date_display_format',
    'frontend_settings',
    'csv_export_delimiter',
)

UPDATE_TYPES_VERSIONS: Final = {x.serialize() for x in UpdateType}

CachedDBSettingsFieldNames = Literal[
    'have_premium',
    'version',
    'premium_should_sync',
    'include_crypto2crypto',
    'ui_floating_precision',
    'taxfree_after_period',
    'balance_save_frequency',
    'include_gas_costs',
    'ksm_rpc_endpoint',
    'dot_rpc_endpoint',
    'beacon_rpc_endpoint',
    'btc_mempool_api',
    'main_currency',
    'date_display_format',
    'submit_usage_analytics',
    'active_modules',
    'frontend_settings',
    'btc_derivation_gap_limit',
    'calculate_past_cost_basis',
    'display_date_in_localtime',
    'current_price_oracles',
    'historical_price_oracles',
    'evm_indexers_order',
    'default_evm_indexer_order',
    'pnl_csv_with_formulas',
    'pnl_csv_have_summary',
    'ssf_graph_multiplier',
    'last_data_migration',
    'non_syncing_exchanges',
    'evmchains_to_skip_detection',
    'cost_basis_method',
    'treat_eth2_as_eth',
    'eth_staking_taxable_after_withdrawal_enabled',
    'address_name_priority',
    'include_fees_in_cost_basis',
    'infer_zero_timed_balances',
    'query_retry_limit',
    'connect_timeout',
    'read_timeout',
    'oracle_penalty_threshold_count',
    'oracle_penalty_duration',
    'auto_delete_calendar_entries',
    'auto_create_calendar_reminders',
    'ask_user_upon_size_discrepancy',
    'events_processing_frequency',
]

DBSettingsFieldTypes = (
    bool |
    int |
    str |
    Asset |
    Sequence[ModuleName] |
    Sequence[CurrentPriceOracle] |
    Sequence[HistoricalPriceOracle] |
    dict[ChainID, Sequence[EvmIndexer]] |
    Sequence[ExchangeLocationID] |
    CostBasisMethod |
    Sequence[AddressNameSource]
)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBSettings:
    have_premium: bool = False
    version: int = ROTKEHLCHEN_DB_VERSION
    last_write_ts: Timestamp = field(default=Timestamp(0))
    premium_should_sync: bool = DEFAULT_PREMIUM_SHOULD_SYNC
    include_crypto2crypto: bool = DEFAULT_INCLUDE_CRYPTO2CRYPTO
    ui_floating_precision: int = DEFAULT_UI_FLOATING_PRECISION
    taxfree_after_period: int | None = DEFAULT_TAXFREE_AFTER_PERIOD
    balance_save_frequency: int = DEFAULT_BALANCE_SAVE_FREQUENCY
    include_gas_costs: bool = DEFAULT_INCLUDE_GAS_COSTS
    ksm_rpc_endpoint: str = 'http://localhost:9933'
    dot_rpc_endpoint: str = ''  # same as kusama -- must be set by user
    beacon_rpc_endpoint: str = ''  # must be set by user
    btc_mempool_api: str = ''
    main_currency: Asset = DEFAULT_MAIN_CURRENCY
    date_display_format: str = DEFAULT_DATE_DISPLAY_FORMAT
    submit_usage_analytics: bool = DEFAULT_SUBMIT_USAGE_ANALYTICS
    active_modules: Sequence[ModuleName] = field(default=DEFAULT_ACTIVE_MODULES)  # type: ignore
    frontend_settings: str = ''
    btc_derivation_gap_limit: int = DEFAULT_BTC_DERIVATION_GAP_LIMIT
    calculate_past_cost_basis: bool = DEFAULT_CALCULATE_PAST_COST_BASIS
    display_date_in_localtime: bool = DEFAULT_DISPLAY_DATE_IN_LOCALTIME
    current_price_oracles: Sequence[CurrentPriceOracle] = field(default=DEFAULT_CURRENT_PRICE_ORACLES)  # noqa: E501
    historical_price_oracles: Sequence[HistoricalPriceOracle] = field(default=DEFAULT_HISTORICAL_PRICE_ORACLES)  # noqa: E501
    evm_indexers_order: SerializableChainIndexerOrder = field(default=DEFAULT_INDEXERS_ORDER)
    default_evm_indexer_order: Sequence[EvmIndexer] = field(default=DEFAULT_EVM_INDEXER_ORDER)
    pnl_csv_with_formulas: bool = DEFAULT_PNL_CSV_WITH_FORMULAS
    pnl_csv_have_summary: bool = DEFAULT_PNL_CSV_HAVE_SUMMARY
    ssf_graph_multiplier: int = DEFAULT_SSF_GRAPH_MULTIPLIER
    last_data_migration: int = DEFAULT_LAST_DATA_MIGRATION
    non_syncing_exchanges: Sequence[ExchangeLocationID] = field(default_factory=list)
    evmchains_to_skip_detection: Sequence[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE] = field(default_factory=list)  # Both EVM and EVMLike chains # noqa: E501
    cost_basis_method: CostBasisMethod = DEFAULT_COST_BASIS_METHOD
    treat_eth2_as_eth: bool = DEFAULT_TREAT_ETH2_AS_ETH
    eth_staking_taxable_after_withdrawal_enabled: bool = DEFAULT_ETH_STAKING_TAXABLE_AFTER_WITHDRAWAL_ENABLED  # noqa: E501
    address_name_priority: Sequence[AddressNameSource] = DEFAULT_ADDRESS_NAME_PRIORITY
    include_fees_in_cost_basis: bool = DEFAULT_INCLUDE_FEES_IN_COST_BASIS
    infer_zero_timed_balances: bool = DEFAULT_INFER_ZERO_TIMED_BALANCES
    query_retry_limit: int = DEFAULT_QUERY_RETRY_LIMIT
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT
    read_timeout: int = DEFAULT_READ_TIMEOUT
    oracle_penalty_threshold_count: int = DEFAULT_ORACLE_PENALTY_THRESHOLD_COUNT
    oracle_penalty_duration: int = DEFAULT_ORACLE_PENALTY_DURATION
    auto_delete_calendar_entries: bool = DEFAULT_AUTO_DELETE_CALENDAR_ENTRIES
    auto_create_calendar_reminders: bool = DEFAULT_AUTO_CREATE_CALENDAR_REMINDERS
    ask_user_upon_size_discrepancy: bool = DEFAULT_ASK_USER_UPON_SIZE_DISCREPANCY
    auto_detect_tokens: bool = DEFAULT_AUTO_DETECT_TOKENS
    csv_export_delimiter: str = DEFAULT_CSV_EXPORT_DELIMITER
    events_processing_frequency: int = DEFAULT_EVENTS_PROCESSING_FREQUENCY

    def serialize(self) -> dict[str, Any]:
        settings_dict = {}
        for field_entry in fields(self):
            value = getattr(self, field_entry.name)
            if value is not None:
                serialized_value = serialize_db_setting(
                    value=value,
                    setting=field_entry.name,
                    is_modifiable=False,
                )
            else:
                serialized_value = value

            settings_dict[field_entry.name] = serialized_value

        return settings_dict


class ModifiableDBSettings(NamedTuple):
    premium_should_sync: bool | None = None
    include_crypto2crypto: bool | None = None
    ui_floating_precision: int | None = None
    taxfree_after_period: int | None = None
    balance_save_frequency: int | None = None
    include_gas_costs: bool | None = None
    ksm_rpc_endpoint: str | None = None
    dot_rpc_endpoint: str | None = None
    beacon_rpc_endpoint: str | None = None
    main_currency: AssetWithOracles | None = None
    date_display_format: str | None = None
    submit_usage_analytics: bool | None = None
    active_modules: list[ModuleName] | None = None
    frontend_settings: str | None = None
    btc_derivation_gap_limit: int | None = None
    calculate_past_cost_basis: bool | None = None
    display_date_in_localtime: bool | None = None
    current_price_oracles: list[CurrentPriceOracle] | None = None
    historical_price_oracles: list[HistoricalPriceOracle] | None = None
    evm_indexers_order: SerializableChainIndexerOrder | None = None
    default_evm_indexer_order: list[EvmIndexer] | None = None
    pnl_csv_with_formulas: bool | None = None
    pnl_csv_have_summary: bool | None = None
    ssf_graph_multiplier: int | None = None
    non_syncing_exchanges: list[ExchangeLocationID] | None = None
    evmchains_to_skip_detection: list[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE] | None = None
    cost_basis_method: CostBasisMethod | None = None
    treat_eth2_as_eth: bool | None = None
    eth_staking_taxable_after_withdrawal_enabled: bool | None = None
    address_name_priority: list[AddressNameSource] | None = None
    include_fees_in_cost_basis: bool | None = None
    infer_zero_timed_balances: bool | None = None
    query_retry_limit: int | None = None
    connect_timeout: int | None = None
    read_timeout: int | None = None
    oracle_penalty_threshold_count: int | None = None
    oracle_penalty_duration: int | None = None
    auto_delete_calendar_entries: bool | None = None
    auto_create_calendar_reminders: bool | None = None
    ask_user_upon_size_discrepancy: bool | None = None
    auto_detect_tokens: bool | None = None
    csv_export_delimiter: str | None = None
    btc_mempool_api: str | None = None
    events_processing_frequency: int | None = None

    def serialize(self) -> dict[str, Any]:
        settings_dict = {}
        for setting in ModifiableDBSettings._fields:
            value = getattr(self, setting)
            if value is not None:
                serialized_value = serialize_db_setting(
                    value=value,
                    setting=setting,
                    is_modifiable=True,
                )
                settings_dict[setting] = serialized_value
        return settings_dict


def read_boolean(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return str_to_bool(value)
    # else
    raise DeserializationError(
        f'Failed to read a boolean from {value} which is of type {type(value)}',
    )


def _deserialize_evm_indexers_order(value: str) -> SerializableChainIndexerOrder:
    """Deserialize per-chain indexer order mapping."""
    result: dict[ChainID, Sequence[EvmIndexer]] = {}
    try:
        indexers = json.loads(value)
    except json.JSONDecodeError as e:
        log.error(f'Failed to load indexers settings due to {e}. Skipping')
        return SerializableChainIndexerOrder(result)

    for chain in EVM_CHAIN_IDS_WITH_TRANSACTIONS:
        if (order := indexers.get(chain.to_name())) is not None:
            try:
                result[chain] = [EvmIndexer.deserialize(idx) for idx in order]
            except DeserializationError as e:
                log.error(
                    f'Found unexpected indexer for chain {chain.to_name()} in '
                    f'{order} with {e}. Skipping',
                )

    return SerializableChainIndexerOrder(result)


def db_settings_from_dict(
        settings_dict: dict[str, Any],
        msg_aggregator: 'MessagesAggregator',
) -> DBSettings:
    specified_args: dict[str, Any] = {}
    for key, value in settings_dict.items():
        if key in BOOLEAN_KEYS:
            specified_args[key] = read_boolean(value)
        elif key in INTEGER_KEYS:
            specified_args[key] = int(value)
        elif key in STRING_KEYS:
            specified_args[key] = str(value)
        elif key in UPDATE_TYPES_VERSIONS:
            continue  # these are handled separately
        elif key == 'taxfree_after_period':
            # taxfree_after_period can also be None, to signify disabled setting
            if value is None:
                specified_args[key] = value
            else:
                int_value = int(value)
                if int_value <= 0:
                    msg_aggregator.add_warning(
                        f'A negative or zero value ({int_value}) for taxfree_after_period '
                        f'ended up in the DB. Setting it to None. Please open an issue in '
                        f'Github: https://github.com/rotki/rotki/issues/new/choose',
                    )
                    int_value = None  # type: ignore[assignment]  # we do it on purpose
                specified_args[key] = int_value

        elif key == 'main_currency':
            specified_args[key] = Asset(str(value)).resolve_to_asset_with_oracles()
        elif key == 'last_write_ts':
            specified_args[key] = Timestamp(int(value))
        elif key == 'active_modules':
            specified_args[key] = json.loads(value)
        elif key == 'current_price_oracles':
            oracles = json.loads(value)
            specified_args[key] = [CurrentPriceOracle.deserialize(oracle) for oracle in oracles]
        elif key == 'historical_price_oracles':
            oracles = json.loads(value)
            specified_args[key] = [HistoricalPriceOracle.deserialize(oracle) for oracle in oracles]
        elif key == 'evm_indexers_order':
            specified_args[key] = _deserialize_evm_indexers_order(value=value)
        elif key == 'default_evm_indexer_order':
            specified_args[key] = [EvmIndexer.deserialize(entry) for entry in json.loads(value)]
        elif key == 'non_syncing_exchanges':
            values = json.loads(value)
            specified_args[key] = [ExchangeLocationID.deserialize(x) for x in values]
        elif key == 'evmchains_to_skip_detection':
            values = json.loads(value)
            specified_args[key] = [SupportedBlockchain.deserialize(x) for x in values]
        elif key == 'cost_basis_method':
            specified_args[key] = CostBasisMethod.deserialize(value)
        elif key == 'address_name_priority':
            specified_args[key] = json.loads(value)
        else:
            log.error(
                f'Unknown DB setting {key} given. Ignoring it. Should not '
                f'happen so please open an issue in Github.',
            )

    return DBSettings(**specified_args)


def serialize_db_setting(
        value: Any,
        setting: Any,
        is_modifiable: bool,
) -> Any:
    """Utility function to serialize a db setting.
    `is_modifiable` represents `ModifiableDBSettings` specific flag.
    """
    # Handle settings that serialize regardless of is_modifiable
    if setting in {'main_currency', 'cost_basis_method'}:
        return value.serialize()  # pylint: disable=no-member

    if is_modifiable:
        if isinstance(value, bool):
            # We need to save booleans as strings in the DB
            return str(value)
        if setting == 'taxfree_after_period' and value == -1:
            # taxfree_after_period of -1 by the user means disable the setting
            return None
        if setting in {'active_modules', 'address_name_priority'}:
            return json.dumps(value)
        if setting in LIST_KEYS:
            return json.dumps([x.serialize() for x in value])
        if setting in JSON_KEYS:
            return json.dumps(value.serialize())
    else:
        if setting in LIST_KEYS:
            return [x.serialize() for x in value]
        if setting in JSON_KEYS:
            return value.serialize()

    return value


class CachedSettings:
    """
    Singleton class that manages the cached settings.

    It is initialized with default settings whenever it is created.
    When a user is unlocked on login/signup, it will be updated with
    saved DB settings if any via the initialize method and is reset
    on user logout. This way the cached settings are bound to the
    user's session and not shared between users. It is updated when a
    setting is updated.

    Keep in mind:
    - last_write_ts is not cached for performance reasons
    (see comment on write_ctx method of DBConnection class)
    - settings that are not attributes of the DBSettings dataclass and are
    not set with the set_setting method are not being cached. Settings not in the DBSettings
    but set with the set_setting method are cached.
    """
    __instance: Optional['CachedSettings'] = None
    _settings: DBSettings = DBSettings()  # the default settings values
    _evm_indexers_order_per_chain: ClassVar[Mapping[ChainID, tuple[EvmIndexer, ...]]] = {}
    evm_indexers_order_override_var: ClassVar[ContextVar[tuple[EvmIndexer, ...] | None]] = ContextVar(  # noqa: E501
        'cachedsettings_evm_indexer_override',
        default=None,
    )

    def __new__(cls) -> 'CachedSettings':
        if CachedSettings.__instance is not None:
            return CachedSettings.__instance

        CachedSettings.__instance = super().__new__(cls)
        CachedSettings.__instance._refresh_indexers_cache()
        return CachedSettings.__instance

    def _refresh_indexers_cache(self) -> None:
        """Normalize indexer order once for quick lookups."""
        chain_to_indexers = {}
        for chain in EVM_CHAIN_IDS_WITH_TRANSACTIONS:
            chain_to_indexers[chain] = self._settings.evm_indexers_order.get(
                chain,
                self._settings.default_evm_indexer_order,
            )

        self.__class__._evm_indexers_order_per_chain = chain_to_indexers  # type: ignore

    def initialize(self, settings: DBSettings) -> None:
        """Initialize with saved DB settings

        This overwrites the default db settings set at class instantiation"""
        self._settings = settings
        self._refresh_indexers_cache()

    def reset(self) -> None:
        self._settings = DBSettings()
        self._refresh_indexers_cache()

    def update_entry(self, attr: str, value: DBSettingsFieldTypes) -> None:
        setattr(self._settings, attr, value)
        if attr in ('evm_indexers_order', 'default_evm_indexer_order'):
            self._refresh_indexers_cache()

    def update_entries(self, settings: ModifiableDBSettings) -> None:
        for attr in settings._fields:
            if getattr(settings, attr) is None:  # ModifiableDBSettings contain the values to modify and None for the others. Ignore None  # noqa: E501
                continue
            self.update_entry(attr, getattr(settings, attr))

    def get_entry(self, attr: CachedDBSettingsFieldNames) -> DBSettingsFieldTypes:
        return getattr(self._settings, attr)

    def get_settings(self) -> DBSettings:
        return self._settings

    # commonly used settings with their own get function
    def get_timeout_tuple(self) -> tuple[int, int]:
        conn_timeout = self.get_entry('connect_timeout')
        read_timeout = self.get_entry('read_timeout')
        return conn_timeout, read_timeout  # type: ignore

    def get_query_retry_limit(self) -> int:
        return self.get_entry('query_retry_limit')  # type: ignore

    def get_evm_indexers_order_for_chain(self, chain_id: ChainID) -> tuple[EvmIndexer, ...]:
        """Return chain-specific indexer order falling back to defaults."""
        default_order = self._evm_indexers_order_per_chain[chain_id]
        if (override := self.evm_indexers_order_override_var.get()) is None:
            return default_order

        return tuple(override)

    @property
    def oracle_penalty_duration(self) -> int:
        return self._settings.oracle_penalty_duration

    @property
    def oracle_penalty_threshold_count(self) -> int:
        return self._settings.oracle_penalty_threshold_count

    @property
    def main_currency(self) -> Asset:
        return self._settings.main_currency
