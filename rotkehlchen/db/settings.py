import json
from typing import Any, Dict, List, NamedTuple, Optional, Union

from rotkehlchen.accounting.ledger_actions import LedgerActionType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.timing import YEAR_IN_SECONDS
from rotkehlchen.db.utils import str_to_bool
from rotkehlchen.errors import DeserializationError
from rotkehlchen.history.typing import (
    DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER,
    HistoricalPriceOracle,
)
from rotkehlchen.inquirer import DEFAULT_CURRENT_PRICE_ORACLES_ORDER, CurrentPriceOracle
from rotkehlchen.typing import AVAILABLE_MODULES_MAP, ModuleName, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

ROTKEHLCHEN_DB_VERSION = 28
DEFAULT_TAXFREE_AFTER_PERIOD = YEAR_IN_SECONDS
DEFAULT_INCLUDE_CRYPTO2CRYPTO = True
DEFAULT_INCLUDE_GAS_COSTS = True
DEFAULT_PREMIUM_SHOULD_SYNC = False
DEFAULT_UI_FLOATING_PRECISION = 2
DEFAULT_BALANCE_SAVE_FREQUENCY = 24
DEFAULT_MAIN_CURRENCY = A_USD
DEFAULT_DATE_DISPLAY_FORMAT = '%d/%m/%Y %H:%M:%S %Z'
DEFAULT_SUBMIT_USAGE_ANALYTICS = True
DEFAULT_ACTIVE_MODULES = list(AVAILABLE_MODULES_MAP.keys())
DEFAULT_ACCOUNT_FOR_ASSETS_MOVEMENTS = True
DEFAULT_BTC_DERIVATION_GAP_LIMIT = 20
DEFAULT_CALCULATE_PAST_COST_BASIS = True
DEFAULT_DISPLAY_DATE_IN_LOCALTIME = True
DEFAULT_CURRENT_PRICE_ORACLES = DEFAULT_CURRENT_PRICE_ORACLES_ORDER
DEFAULT_HISTORICAL_PRICE_ORACLES = DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER
DEFAULT_TAXABLE_LEDGER_ACTIONS = [
    LedgerActionType.INCOME,
    LedgerActionType.EXPENSE,
    LedgerActionType.LOSS,
    LedgerActionType.DIVIDENDS_INCOME,
    LedgerActionType.DONATION_RECEIVED,
    LedgerActionType.GRANT,
]

JSON_KEYS = ('current_price_oracles', 'historical_price_oracles', 'taxable_ledger_actions')
BOOLEAN_KEYS = (
    'have_premium',
    'include_crypto2crypto',
    'include_gas_costs',
    'premium_should_sync',
    'submit_usage_analytics',
    'account_for_assets_movements',
    'calculate_past_cost_basis',
    'display_date_in_localtime',
)
INTEGER_KEYS = (
    'version',
    'ui_floating_precision',
    'balance_save_frequency',
    'btc_derivation_gap_limit',
)
STRING_KEYS = (
    'eth_rpc_endpoint',
    'ksm_rpc_endpoint',
    'date_display_format',
    'frontend_settings',
)
TIMESTAMP_KEYS = ('last_write_ts', 'last_data_upload_ts', 'last_balance_save')


class DBSettings(NamedTuple):
    have_premium: bool = False
    version: int = ROTKEHLCHEN_DB_VERSION
    last_write_ts: Timestamp = Timestamp(0)
    premium_should_sync: bool = DEFAULT_PREMIUM_SHOULD_SYNC
    include_crypto2crypto: bool = DEFAULT_INCLUDE_CRYPTO2CRYPTO
    last_data_upload_ts: Timestamp = Timestamp(0)
    ui_floating_precision: int = DEFAULT_UI_FLOATING_PRECISION
    taxfree_after_period: Optional[int] = DEFAULT_TAXFREE_AFTER_PERIOD
    balance_save_frequency: int = DEFAULT_BALANCE_SAVE_FREQUENCY
    include_gas_costs: bool = DEFAULT_INCLUDE_GAS_COSTS
    eth_rpc_endpoint: str = 'http://localhost:8545'
    ksm_rpc_endpoint: str = 'http://localhost:9933'
    main_currency: Asset = DEFAULT_MAIN_CURRENCY
    date_display_format: str = DEFAULT_DATE_DISPLAY_FORMAT
    last_balance_save: Timestamp = Timestamp(0)
    submit_usage_analytics: bool = DEFAULT_SUBMIT_USAGE_ANALYTICS
    active_modules: List[ModuleName] = DEFAULT_ACTIVE_MODULES  # type: ignore
    frontend_settings: str = ''
    account_for_assets_movements: bool = DEFAULT_ACCOUNT_FOR_ASSETS_MOVEMENTS
    btc_derivation_gap_limit: int = DEFAULT_BTC_DERIVATION_GAP_LIMIT
    calculate_past_cost_basis: bool = DEFAULT_CALCULATE_PAST_COST_BASIS
    display_date_in_localtime: bool = DEFAULT_DISPLAY_DATE_IN_LOCALTIME
    current_price_oracles: List[CurrentPriceOracle] = DEFAULT_CURRENT_PRICE_ORACLES
    historical_price_oracles: List[HistoricalPriceOracle] = DEFAULT_HISTORICAL_PRICE_ORACLES
    taxable_ledger_actions: List[LedgerActionType] = DEFAULT_TAXABLE_LEDGER_ACTIONS


class ModifiableDBSettings(NamedTuple):
    premium_should_sync: Optional[bool] = None
    include_crypto2crypto: Optional[bool] = None
    ui_floating_precision: Optional[int] = None
    taxfree_after_period: Optional[int] = None
    balance_save_frequency: Optional[int] = None
    include_gas_costs: Optional[bool] = None
    eth_rpc_endpoint: Optional[str] = None
    ksm_rpc_endpoint: Optional[str] = None
    main_currency: Optional[Asset] = None
    date_display_format: Optional[str] = None
    submit_usage_analytics: Optional[bool] = None
    active_modules: Optional[List[ModuleName]] = None
    frontend_settings: Optional[str] = None
    account_for_assets_movements: Optional[bool] = None
    btc_derivation_gap_limit: Optional[int] = None
    calculate_past_cost_basis: Optional[bool] = None
    display_date_in_localtime: Optional[bool] = None
    current_price_oracles: Optional[List[CurrentPriceOracle]] = None
    historical_price_oracles: Optional[List[HistoricalPriceOracle]] = None
    taxable_ledger_actions: Optional[List[LedgerActionType]] = None

    def serialize(self) -> Dict[str, Any]:
        settings_dict = {}
        for setting in ModifiableDBSettings._fields:
            value = getattr(self, setting)
            if value is not None:
                # We need to save booleans as strings in the DB
                if isinstance(value, bool):
                    value = str(value)
                # main currency needs to have only its identifier
                elif setting == 'main_currency':
                    value = value.identifier  # pylint: disable=no-member
                # taxfree_after_period of -1 by the user means disable the setting
                elif setting == 'taxfree_after_period' and value == -1:
                    value = None
                elif setting == 'active_modules':
                    value = json.dumps(value)
                elif setting in JSON_KEYS:
                    value = json.dumps([x.serialize() for x in value])

                settings_dict[setting] = value

        return settings_dict


def read_boolean(value: Union[str, bool]) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return str_to_bool(value)
    # else
    raise DeserializationError(
        f'Failed to read a boolean from {value} which is of type {type(value)}',
    )


def db_settings_from_dict(
        settings_dict: Dict[str, Any],
        msg_aggregator: MessagesAggregator,
) -> DBSettings:
    specified_args: Dict[str, Any] = {}
    for key, value in settings_dict.items():
        if key in BOOLEAN_KEYS:
            specified_args[key] = read_boolean(value)
        elif key in INTEGER_KEYS:
            specified_args[key] = int(value)
        elif key in STRING_KEYS:
            specified_args[key] = str(value)
        elif key == 'taxfree_after_period':
            # taxfree_after_period can also be None, to signify disabled setting
            if value is None:
                specified_args[key] = value
            else:
                int_value = int(value)
                if int_value <= 0:
                    value = None
                    msg_aggregator.add_warning(
                        f'A negative or zero value ({int_value}) for taxfree_after_period '
                        f'ended up in the DB. Setting it to None. Please open an issue in '
                        f'Github: https://github.com/rotki/rotki/issues/new/choose',
                    )

                else:
                    value = int_value

                specified_args[key] = value
        elif key == 'main_currency':
            specified_args[key] = Asset(str(value))
        elif key in TIMESTAMP_KEYS:
            specified_args[key] = Timestamp(int(value))
        elif key == 'active_modules':
            specified_args[key] = json.loads(value)
        elif key == 'current_price_oracles':
            oracles = json.loads(value)
            specified_args[key] = [CurrentPriceOracle.deserialize(oracle) for oracle in oracles]
        elif key == 'historical_price_oracles':
            oracles = json.loads(value)
            specified_args[key] = [HistoricalPriceOracle.deserialize(oracle) for oracle in oracles]
        elif key == 'taxable_ledger_actions':
            values = json.loads(value)
            specified_args[key] = [LedgerActionType.deserialize(x) for x in values]
        else:
            msg_aggregator.add_warning(
                f'Unknown DB setting {key} given. Ignoring it. Should not '
                f'happen so please open an issue in Github.',
            )

    return DBSettings(**specified_args)
