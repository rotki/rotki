from typing import Any, Dict, NamedTuple, Optional, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.timing import YEAR_IN_SECONDS
from rotkehlchen.db.utils import str_to_bool
from rotkehlchen.errors import DeserializationError
from rotkehlchen.typing import Timestamp
from rotkehlchen.user_messages import MessagesAggregator

ROTKEHLCHEN_DB_VERSION = 8
DEFAULT_TAXFREE_AFTER_PERIOD = YEAR_IN_SECONDS
DEFAULT_INCLUDE_CRYPTO2CRYPTO = True
DEFAULT_INCLUDE_GAS_COSTS = True
DEFAULT_ANONYMIZED_LOGS = False
DEFAULT_PREMIUM_SHOULD_SYNC = False
DEFAULT_START_DATE = '01/08/2015'
DEFAULT_UI_FLOATING_PRECISION = 2
DEFAULT_BALANCE_SAVE_FREQUENCY = 24
DEFAULT_MAIN_CURRENCY = A_USD
DEFAULT_DATE_DISPLAY_FORMAT = '%d/%m/%Y %H:%M:%S %Z'
DEFAULT_SUBMIT_USAGE_ANALYTICS = True


class DBSettings(NamedTuple):
    version: int = ROTKEHLCHEN_DB_VERSION
    last_write_ts: Timestamp = Timestamp(0)
    premium_should_sync: bool = DEFAULT_PREMIUM_SHOULD_SYNC
    include_crypto2crypto: bool = DEFAULT_INCLUDE_CRYPTO2CRYPTO
    anonymized_logs: bool = DEFAULT_ANONYMIZED_LOGS
    last_data_upload_ts: Timestamp = Timestamp(0)
    ui_floating_precision: int = DEFAULT_UI_FLOATING_PRECISION
    taxfree_after_period: Optional[int] = DEFAULT_TAXFREE_AFTER_PERIOD
    balance_save_frequency: int = DEFAULT_BALANCE_SAVE_FREQUENCY
    include_gas_costs: bool = DEFAULT_INCLUDE_GAS_COSTS
    historical_data_start: str = DEFAULT_START_DATE
    eth_rpc_endpoint: str = 'http://localhost:8545'
    main_currency: Asset = DEFAULT_MAIN_CURRENCY
    date_display_format: str = DEFAULT_DATE_DISPLAY_FORMAT
    last_balance_save: Timestamp = Timestamp(0)
    submit_usage_analytics: bool = DEFAULT_SUBMIT_USAGE_ANALYTICS


class ModifiableDBSettings(NamedTuple):
    premium_should_sync: Optional[bool] = None
    include_crypto2crypto: Optional[bool] = None
    anonymized_logs: Optional[bool] = None
    ui_floating_precision: Optional[int] = None
    taxfree_after_period: Optional[int] = None
    balance_save_frequency: Optional[int] = None
    include_gas_costs: Optional[bool] = None
    historical_data_start: Optional[str] = None
    eth_rpc_endpoint: Optional[str] = None
    main_currency: Optional[Asset] = None
    date_display_format: Optional[str] = None

    def serialize(self) -> Dict[str, Any]:
        settings_dict = dict()
        for setting in ModifiableDBSettings._fields:
            value = getattr(self, setting)
            if value is not None:
                # We need to save booleans as strings in the DB
                if isinstance(value, bool):
                    value = str(value)
                # main currency needs to have only its identifier
                if setting == 'main_currency':
                    value = value.identifier  # pylint: disable=no-member
                # taxfree_after_period of -1 by the user means disable the setting
                if setting == 'taxfree_after_period' and value == -1:
                    value = None

                settings_dict[setting] = value

        return settings_dict


def read_boolean(value: Union[str, bool]) -> bool:
    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        return str_to_bool(value)

    raise DeserializationError(
        f'Failed to read a boolean from {value} which is of type {type(value)}',
    )


def db_settings_from_dict(
        settings_dict: Dict[str, Any],
        msg_aggregator: MessagesAggregator,
) -> DBSettings:
    specified_args: Dict[str, Any] = {}
    for key, value in settings_dict.items():
        if key == 'version':
            specified_args[key] = int(value)
        elif key == 'historical_data_start':
            specified_args[key] = str(value)
        elif key == 'eth_rpc_endpoint':
            specified_args[key] = str(value)
        elif key == 'ui_floating_precision':
            specified_args[key] = int(value)
        elif key == 'include_crypto2crypto':
            specified_args[key] = read_boolean(value)
        elif key == 'taxfree_after_period':
            # taxfree_after_period can also be None, to signify disabled setting
            if value is None:
                specified_args[key] = value
            else:
                specified_args[key] = int(value)
        elif key == 'balance_save_frequency':
            specified_args[key] = int(value)
        elif key == 'main_currency':
            specified_args[key] = Asset(str(value))
        elif key == 'anonymized_logs':
            specified_args[key] = read_boolean(value)
        elif key == 'include_gas_costs':
            specified_args[key] = read_boolean(value)
        elif key == 'date_display_format':
            specified_args[key] = str(value)
        elif key == 'premium_should_sync':
            specified_args[key] = read_boolean(value)
        elif key == 'last_write_ts':
            specified_args[key] = Timestamp(int(value))
        elif key == 'last_data_upload_ts':
            specified_args[key] = Timestamp(int(value))
        elif key == 'last_balance_save':
            specified_args[key] = Timestamp(int(value))
        elif key == 'submit_usage_analytics':
            specified_args[key] = read_boolean(value)
        else:
            msg_aggregator.add_warning(
                f'Unknown DB setting {key} given. Ignoring it. Should not '
                f'happen so please open an issue in Github.',
            )

    return DBSettings(**specified_args)
