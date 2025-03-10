import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, Optional

from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.timing import YEAR_IN_SECONDS
from rotkehlchen.data_migrations.constants import LAST_DATA_MIGRATION
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
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    AddressNameSource,
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

ROTKEHLCHEN_DB_VERSION = 47
ROTKEHLCHEN_TRANSIENT_DB_VERSION = 2
DEFAULT_TAXFREE_AFTER_PERIOD = YEAR_IN_SECONDS
DEFAULT_INCLUDE_CRYPTO2CRYPTO = True
DEFAULT_INCLUDE_GAS_COSTS = True
DEFAULT_PREMIUM_SHOULD_SYNC = False
DEFAULT_UI_FLOATING_PRECISION = 2
DEFAULT_BALANCE_SAVE_FREQUENCY = 24
DEFAULT_MAIN_CURRENCY = A_USD
DEFAULT_DATE_DISPLAY_FORMAT = '%d/%m/%Y %H:%M:%S %Z'
DEFAULT_SUBMIT_USAGE_ANALYTICS = True
DEFAULT_ACTIVE_MODULES = tuple(set(AVAILABLE_MODULES_MAP.keys()) - DEFAULT_OFF_MODULES)
DEFAULT_BTC_DERIVATION_GAP_LIMIT = 20
DEFAULT_CALCULATE_PAST_COST_BASIS = True
DEFAULT_DISPLAY_DATE_IN_LOCALTIME = True
DEFAULT_CURRENT_PRICE_ORACLES = DEFAULT_CURRENT_PRICE_ORACLES_ORDER
DEFAULT_HISTORICAL_PRICE_ORACLES = DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER
DEFAULT_PNL_CSV_WITH_FORMULAS = True
DEFAULT_PNL_CSV_HAVE_SUMMARY = False
DEFAULT_SSF_GRAPH_MULTIPLIER = 0
DEFAULT_LAST_DATA_MIGRATION = LAST_DATA_MIGRATION
DEFAULT_COST_BASIS_METHOD = CostBasisMethod.FIFO
DEFAULT_TREAT_ETH2_AS_ETH = True
DEFAULT_ETH_STAKING_TAXABLE_AFTER_WITHDRAWAL_ENABLED = True
DEFAULT_INCLUDE_FEES_IN_COST_BASIS = True
DEFAULT_INFER_ZERO_TIMED_BALANCES = False  # If True the asset amount and value chart shows the 0 balance periods for an asset  # noqa: E501
DEFAULT_QUERY_RETRY_LIMIT = 5
DEFAULT_CONNECT_TIMEOUT = 30
DEFAULT_READ_TIMEOUT = 30
DEFAULT_ORACLE_PENALTY_THRESHOLD_COUNT = 5
DEFAULT_ORACLE_PENALTY_DURATION = 1800
DEFAULT_AUTO_DELETE_CALENDAR_ENTRIES = True
DEFAULT_AUTO_CREATE_CALENDAR_REMINDERS = True
DEFAULT_ASK_USER_UPON_SIZE_DISCREPANCY = True
DEFAULT_AUTO_DETECT_TOKENS = True
DEFAULT_CSV_EXPORT_DELIMITER = ','
DEFAULT_USE_UNIFIED_ETHERSCAN_API = False

JSON_KEYS = (
    'current_price_oracles',
    'historical_price_oracles',
    'non_syncing_exchanges',
    'evmchains_to_skip_detection',
)
BOOLEAN_KEYS = (
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
    'use_unified_etherscan_api',
)
INTEGER_KEYS = (
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
)
STRING_KEYS = (
    'ksm_rpc_endpoint',
    'dot_rpc_endpoint',
    'beacon_rpc_endpoint',
    'date_display_format',
    'frontend_settings',
    'csv_export_delimiter',
)

UPDATE_TYPES_VERSIONS = {x.serialize() for x in UpdateType}

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
]

DBSettingsFieldTypes = (
    bool |
    int |
    str |
    Asset |
    Sequence[ModuleName] |
    Sequence[CurrentPriceOracle] |
    Sequence[HistoricalPriceOracle] |
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
    use_unified_etherscan_api: bool = DEFAULT_USE_UNIFIED_ETHERSCAN_API

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
    use_unified_etherscan_api: bool | None = None

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
    # We need to save booleans as strings in the DB
    if isinstance(value, bool) and is_modifiable is True:
        value = str(value)
    # taxfree_after_period of -1 by the user means disable the setting
    elif setting == 'taxfree_after_period' and value == -1 and is_modifiable is True:
        value = None
    elif setting == 'active_modules' and is_modifiable is True:
        value = json.dumps(value)
    elif setting in {'main_currency', 'cost_basis_method'}:
        value = value.serialize()  # pylint: disable=no-member
    elif setting == 'address_name_priority' and is_modifiable is True:
        value = json.dumps(value)
    elif setting in JSON_KEYS:
        if is_modifiable is True:
            value = json.dumps([x.serialize() for x in value])
        else:
            value = [x.serialize() for x in value]
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

    def __new__(cls) -> 'CachedSettings':
        if CachedSettings.__instance is not None:
            return CachedSettings.__instance

        CachedSettings.__instance = super().__new__(cls)
        return CachedSettings.__instance

    def initialize(self, settings: DBSettings) -> None:
        """Initialize with saved DB settings

        This overwrites the default db settings set at class instantiation"""
        self._settings = settings

    def reset(self) -> None:
        self._settings = DBSettings()

    def update_entry(self, attr: str, value: DBSettingsFieldTypes) -> None:
        setattr(self._settings, attr, value)

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

    @property
    def oracle_penalty_duration(self) -> int:
        return self._settings.oracle_penalty_duration

    @property
    def oracle_penalty_threshold_count(self) -> int:
        return self._settings.oracle_penalty_threshold_count
