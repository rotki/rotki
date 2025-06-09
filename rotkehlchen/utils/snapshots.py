from csv import DictReader
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_timestamp
from rotkehlchen.types import Location, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.sqlite import DBCursor


def validate_import_data(
        balances_data: list[dict[str, str]],
        location_data: list[dict[str, str]],
) -> tuple[bool, str]:
    """Validates the snapshot data about to be imported.
    It returns the status of the validation and an error message if any.
    """
    # check if the headers match the type stored in the db
    has_invalid_headers = (
        tuple(balances_data[0].keys()) != ('timestamp', 'category', 'asset_identifier', 'amount', 'usd_value') or  # noqa: E501
        tuple(location_data[0].keys()) != ('timestamp', 'location', 'usd_value')
    )
    if has_invalid_headers:
        return False, 'csv file has invalid headers'

    # check if the timestamp can be converted to int
    try:
        balances_timestamps = [deserialize_timestamp(entry['timestamp']) for entry in balances_data]  # noqa: E501
        location_data_timestamps = [deserialize_timestamp(entry['timestamp']) for entry in location_data]  # noqa: E501
    except DeserializationError:
        return False, 'csv file contains invalid timestamp format'
    # check if all timestamps are the same.
    has_different_timestamps = (
        balances_timestamps.count(balances_timestamps[0]) != len(balances_timestamps) or
        location_data_timestamps.count(location_data_timestamps[0]) != len(location_data_timestamps) or  # noqa: E501
        balances_timestamps[0] != location_data_timestamps[0]
    )
    if has_different_timestamps is True:
        return False, 'csv file has different timestamps'

    return True, ''


def parse_import_snapshot_data(
        balances_snapshot_file: Path,
        location_data_snapshot_file: Path,
) -> tuple[str, list[DBAssetBalance], list[LocationData]]:
    """This function does the following:
    - Takes the path to the snapshot and converts it to a list of dictionaries.
    - The list of dictionaries is then passed through a series of validation checks.
    - This data is then converted to their respective data types
    i.e `DBAssetBalance` & `LocationData`.

    It returns the status of the validation, list of balances & list of location data.
    """
    balances_list = _csv_to_dict(balances_snapshot_file)
    location_data_list = _csv_to_dict(location_data_snapshot_file)

    is_valid, message = validate_import_data(
        balances_data=balances_list,
        location_data=location_data_list,
    )
    if is_valid is False:
        return message, [], []

    try:
        processed_balances_list: list[DBAssetBalance] = [DBAssetBalance(
            category=BalanceType.deserialize(entry['category']),
            time=Timestamp(int(entry['timestamp'])),
            asset=Asset(identifier=entry['asset_identifier']).check_existence(),
            amount=deserialize_fval(
                value=entry['amount'],
                name='amount',
                location='snapshot import',
            ),
            usd_value=deserialize_fval(
                value=entry['usd_value'],
                name='usd_value',
                location='snapshot import',
            ),
        ) for entry in balances_list]
    except UnknownAsset as err:
        error_msg = f'snapshot contains an unknown asset ({err.identifier}). Try adding this asset manually.'  # noqa: E501
        return error_msg, [], []
    except DeserializationError as err:
        error_msg = f'Error occurred while importing snapshot due to: {err!s}'
        return error_msg, [], []

    try:
        processed_location_data_list: list[LocationData] = [LocationData(
            time=Timestamp(int(entry['timestamp'])),
            location=Location.deserialize(entry['location']).serialize_for_db(),
            usd_value=str(deserialize_fval(
                value=entry['usd_value'],
                name='usd_value',
                location='snapshot import',
            )),
        ) for entry in location_data_list]
    except DeserializationError as err:
        error_msg = f'Error occurred while importing snapshot due to: {err!s}'
        return error_msg, [], []

    return '', processed_balances_list, processed_location_data_list


def _csv_to_dict(file: Path) -> list[dict[str, str]]:
    """Converts a csv file to a list of dictionary."""
    with open(file, encoding='utf8') as csv_file:
        csv_reader = DictReader(csv_file)
        return list(csv_reader)


def get_main_currency_price(
        cursor: 'DBCursor',
        db: DBHandler,
        timestamp: Timestamp,
        msg_aggregator: MessagesAggregator,
) -> tuple[AssetWithOracles, Price]:
    """Gets the main currency and its equivalent price at a particular timestamp."""
    main_currency = db.get_setting(cursor, name='main_currency')
    main_currency_price = None
    try:
        main_currency_price = PriceHistorian().query_historical_price(
            from_asset=A_USD,
            to_asset=main_currency,
            timestamp=timestamp,
        )
    except NoPriceForGivenTimestamp:
        main_currency_price = Price(ONE)
        msg_aggregator.add_error(
            f'Could not find {main_currency.symbol} price for timestamp {timestamp}. '
            f'Using USD for export. Please add manual price '
            f'from USD to your main currency {main_currency}',
        )
    return main_currency, main_currency_price
