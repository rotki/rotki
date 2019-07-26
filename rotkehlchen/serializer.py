from typing import Any, Dict, List, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.utils import AssetBalance, LocationData, SingleAssetBalance
from rotkehlchen.errors import DeserializationError
from rotkehlchen.fval import AcceptableFValInitInput, FVal
from rotkehlchen.typing import (
    AssetAmount,
    EthTokenInfo,
    Fee,
    Optional,
    Price,
    Timestamp,
    TradeType,
)
from rotkehlchen.utils.misc import createTimeStamp


def _process_entry(entry: Any) -> Union[str, List[Any], Dict[str, Any], Any]:
    if isinstance(entry, FVal):
        return str(entry)
    elif isinstance(entry, list):
        new_list = list()
        for new_entry in entry:
            new_list.append(_process_entry(new_entry))
        return new_list
    elif isinstance(entry, dict):
        new_dict = dict()
        for k, v in entry.items():
            if isinstance(k, Asset):
                k = k.identifier
            new_dict[k] = _process_entry(v)
        return new_dict
    elif isinstance(entry, LocationData):
        return {'time': entry.time, 'location': entry.location, 'usd_value': entry.usd_value}
    elif isinstance(entry, SingleAssetBalance):
        return {'time': entry.time, 'amount': entry.amount, 'usd_value': entry.usd_value}
    elif isinstance(entry, AssetBalance):
        return {
            'time': entry.time,
            'asset': entry.asset.identifier,
            'amount': entry.amount,
            'usd_value': entry.usd_value,
        }
    elif isinstance(entry, EthTokenInfo):
        return entry._asdict()
    elif isinstance(entry, tuple):
        raise ValueError('Query results should not contain tuples')
    elif isinstance(entry, Asset):
        return entry.identifier
    else:
        return entry


def process_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Before sending out a result a dictionary via the server we are turning:

        - all Decimals to strings so that the serialization to float/big number
          is handled by the client application and we lose nothing in the transfer

        - if a dictionary has an Asset for a key use its identifier as the key value
    """
    processed_result = _process_entry(result)
    assert isinstance(processed_result, Dict)
    return processed_result


def process_result_list(result: List[Any]) -> List[Any]:
    """Just lke process_result but for lists"""
    processed_result = _process_entry(result)
    assert isinstance(processed_result, List)
    return processed_result


def deserialize_fee(fee: Optional[str]) -> Fee:
    """Deserializes a fee from a json entry. Fee in the JSON entry can also be null
    in which case a ZERO fee is returned.

    Can throw DeserializationError if the fee is not as expected
    """
    if not fee:
        return Fee(ZERO)

    try:
        result = Fee(FVal(fee))
    except ValueError as e:
        raise DeserializationError(f'Failed to deserialize a fee entry due to: {str(e)}')

    return result


def deserialize_timestamp(timestamp: Union[int, str]) -> Timestamp:
    """Deserializes a timestamp from a json entry. Given entry can either be a
    string or an int.

    Can throw DeserializationError if the data is not as expected
    """
    if not timestamp:
        raise DeserializationError('Failed to deserialize a timestamp entry from a null entry')

    if isinstance(timestamp, int):
        return Timestamp(timestamp)
    elif isinstance(timestamp, str):
        return Timestamp(int(timestamp))
    else:
        raise DeserializationError(
            f'Failed to deserialize a timestamp entry. Unexpected type {type(timestamp)} given',
        )


def deserialize_timestamp_from_poloniex_date(date: str) -> Timestamp:
    """Deserializes a timestamp from a poloniex api query result date entry

    Can throw DeserializationError if the data is not as expected
    """
    if not date:
        raise DeserializationError(
            'Failed to deserialize a timestamp entry from a null entry in poloniex',
        )

    if not isinstance(date, str):
        raise DeserializationError(
            f'Failed to deserialize a timestamp entry from a {type(date)} entry in poloniex',
        )

    try:
        return Timestamp(createTimeStamp(datestr=date, formatstr="%Y-%m-%d %H:%M:%S"))
    except ValueError:
        raise DeserializationError(f'Failed to deserialize {date} poloniex timestamp entry')


def deserialize_asset_amount(amount: AcceptableFValInitInput) -> AssetAmount:
    try:
        result = AssetAmount(FVal(amount))
    except ValueError as e:
        raise DeserializationError(f'Failed to deserialize an amount entry: {str(e)}')

    return result


def deserialize_price(amount: AcceptableFValInitInput) -> Price:
    try:
        result = Price(FVal(amount))
    except ValueError as e:
        raise DeserializationError(f'Failed to deserialize a price/rate entry: {str(e)}')

    return result


def deserialize_trade_type(symbol: str) -> TradeType:
    """Take a string and attempts to turn it into a TradeType

    Can throw DeserializationError if the symbol is not as expected
    """
    if not isinstance(symbol, str):
        raise DeserializationError(
            f'Failed to deserialize trade type symbol from {type(symbol)} entry',
        )

    if symbol == 'buy':
        return TradeType.BUY
    elif symbol == 'sell':
        return TradeType.SELL
    elif symbol == 'settlement_buy':
        return TradeType.SETTLEMENT_BUY
    elif symbol == 'settlement_sell':
        return TradeType.SETTLEMENT_SELL
    else:
        raise DeserializationError(
            f'Failed to deserialize trade type symbol. Unknown symbol {symbol} for trade type',
        )
