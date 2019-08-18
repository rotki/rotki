from typing import Union, cast

from typing_extensions import Literal

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import DeserializationError
from rotkehlchen.fval import AcceptableFValInitInput, FVal
from rotkehlchen.typing import AssetAmount, Exchange, Fee, Optional, Price, Timestamp, TradeType
from rotkehlchen.utils.misc import convert_to_int, create_timestamp


def deserialize_fee(fee: Optional[str]) -> Fee:
    """Deserializes a fee from a json entry. Fee in the JSON entry can also be null
    in which case a ZERO fee is returned.

    Can throw DeserializationError if the fee is not as expected
    """
    if fee is None:
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
    if timestamp is None:
        raise DeserializationError('Failed to deserialize a timestamp entry from a null entry')

    if isinstance(timestamp, int):
        return Timestamp(timestamp)
    elif isinstance(timestamp, str):
        try:
            return Timestamp(int(timestamp))
        except ValueError:
            # String could not be turned to an int
            raise DeserializationError(
                f'Failed to deserialize a timestamp entry from string {timestamp}',
            )

    # else
    raise DeserializationError(
        f'Failed to deserialize a timestamp entry. Unexpected type {type(timestamp)} given',
    )


def deserialize_timestamp_from_date(date: str, formatstr: str, location: str) -> Timestamp:
    """Deserializes a timestamp from a date entry depending on the format str

    Can throw DeserializationError if the data is not as expected
    """
    if not date:
        raise DeserializationError(
            f'Failed to deserialize a timestamp from a null entry in {location}',
        )

    if not isinstance(date, str):
        raise DeserializationError(
            f'Failed to deserialize a timestamp from a {type(date)} entry in {location}',
        )

    try:
        return Timestamp(create_timestamp(datestr=date, formatstr=formatstr))
    except ValueError:
        raise DeserializationError(f'Failed to deserialize {date} {location} timestamp entry')


def deserialize_timestamp_from_poloniex_date(date: str) -> Timestamp:
    """Deserializes a timestamp from a poloniex api query result date entry

    Can throw DeserializationError if the data is not as expected
    """
    return deserialize_timestamp_from_date(date, '%Y-%m-%d %H:%M:%S', 'poloniex')


def deserialize_timestamp_from_bittrex_date(date: str) -> Timestamp:
    """Deserializes a timestamp from a bittrex api query result date entry

    Can throw DeserializationError if the data is not as expected
    """
    return deserialize_timestamp_from_date(date, '%Y-%m-%dT%H:%M:%S.%f', 'bittrex')


def deserialize_timestamp_from_kraken(time: Union[str, FVal]) -> Timestamp:
    """Deserializes a timestamp from a kraken api query result entry
    Kraken has timestamps in floating point strings. Example: '1561161486.3056'.

    If the dictionary has passed through rlk_jsonloads the entry can also be an Fval

    Can throw DeserializationError if the data is not as expected
    """
    if not time:
        raise DeserializationError(
            'Failed to deserialize a timestamp entry from a null entry in kraken',
        )

    if isinstance(time, str):
        try:
            return Timestamp(convert_to_int(time, accept_only_exact=False))
        except ValueError:
            raise DeserializationError(f'Failed to deserialize {time} kraken timestamp entry')
    elif isinstance(time, FVal):
        try:
            return Timestamp(time.to_int(exact=False))
        except ValueError:
            raise DeserializationError(
                f'Failed to deserialize {time} kraken timestamp entry from an FVal',
            )

    else:
        raise DeserializationError(
            f'Failed to deserialize a timestamp entry from a {type(time)} entry in kraken',
        )


def deserialize_timestamp_from_binance(time: int) -> Timestamp:
    """Deserializes a timestamp from a binance api query result entry
    Kraken has timestamps in integer but also including milliseconds


    Can throw DeserializationError if the data is not as expected
    """
    if not isinstance(time, int):
        raise DeserializationError(
            f'Failed to deserialize a timestamp entry from a {type(time)} entry in binance',
        )

    return Timestamp(int(time / 1000))


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
    """Takes a string and attempts to turn it into a TradeType

    Can throw DeserializationError if the symbol is not as expected
    """
    if not isinstance(symbol, str):
        raise DeserializationError(
            f'Failed to deserialize trade type symbol from {type(symbol)} entry',
        )

    if symbol in ('buy', 'LIMIT_BUY'):
        return TradeType.BUY
    elif symbol in ('sell', 'LIMIT_SELL'):
        return TradeType.SELL
    elif symbol == 'settlement_buy':
        return TradeType.SETTLEMENT_BUY
    elif symbol == 'settlement_sell':
        return TradeType.SETTLEMENT_SELL
    else:
        raise DeserializationError(
            f'Failed to deserialize trade type symbol. Unknown symbol {symbol} for trade type',
        )


def deserialize_exchange_name(symbol: str) -> Exchange:
    """Takes a string and attempts to turn it into an Exchange enum class

    Can throw DeserializationError if the symbols is not as expected
    """

    if not isinstance(symbol, str):
        raise DeserializationError(
            f'Failed to deserialize exchange symbol from {type(symbol)} entry',
        )

    if symbol == 'kraken':
        return Exchange.KRAKEN
    elif symbol == 'poloniex':
        return Exchange.POLONIEX
    elif symbol == 'bittrex':
        return Exchange.BITTREX
    elif symbol == 'binance':
        return Exchange.BINANCE
    elif symbol == 'bitmex':
        return Exchange.BITMEX
    else:
        raise DeserializationError(
            f'Failed to deserialize exchange symbol. Unknown symbol {symbol} for exchange',
        )


def deserialize_asset_movement_category(symbol: str) -> Literal['deposit', 'withdrawal']:
    """Takes a string and determines whether to accept it as an asset mvoemen category

    Can throw DeserializationError if symbol is not as expected
    """
    if not isinstance(symbol, str):
        raise DeserializationError(
            f'Failed to deserialize asset movement category symbol from {type(symbol)} entry',
        )

    if symbol in('deposit', 'withdrawal'):
        return cast(Literal['deposit', 'withdrawal'], symbol)

    # else
    raise DeserializationError(
        f'Failed to deserialize asset movement category symbol. Unknown symbol {symbol}',
    )
