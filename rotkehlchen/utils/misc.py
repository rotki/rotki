import calendar
import datetime
import functools
import logging
import operator
import re
import sys
import time
from binascii import unhexlify
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Sequence
from itertools import zip_longest
from typing import TYPE_CHECKING, Any, TypeVar, overload

from eth_utils import is_hexstr
from eth_utils.address import to_checksum_address
from solders.solders import Pubkey

from rotkehlchen.errors.serialization import ConversionError, DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress, SolanaAddress, Timestamp, TimestampMS
from rotkehlchen.utils.version_check import get_current_version, get_system_spec

if TYPE_CHECKING:
    from requests import Session

log = logging.getLogger(__name__)


def ts_now() -> Timestamp:
    return Timestamp(int(time.time()))


def ts_now_in_ms() -> TimestampMS:
    return TimestampMS(int(time.time() * 1000))


def ts_sec_to_ms(ts: Timestamp) -> TimestampMS:
    return TimestampMS(ts * 1000)


def ts_ms_to_sec(ts: TimestampMS) -> Timestamp:
    return Timestamp(int(ts / 1000))


def create_timestamp(datestr: str, formatstr: str) -> Timestamp:
    """
    Convert datestr to unix timestamp (int) depending on the given formatstr.
    Example format str: '%Y-%m-%d %H:%M:%S. More details here:
    https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior

    May raise:
    - ValueError due to strptime
    """
    return Timestamp(calendar.timegm(time.strptime(datestr, formatstr)))


def timestamp_to_daystart_timestamp(timestamp: Timestamp) -> Timestamp:
    """Turns the given timestamp to the timestamp of the start of the day"""
    date = timestamp_to_date(timestamp, formatstr='%Y-%m-%d')
    return create_timestamp(date, formatstr='%Y-%m-%d')


FRACTION_SECS_RE = re.compile(r'.*\.(\d+).*')


def iso8601ts_to_timestamp(datestr: str) -> Timestamp:
    """Requires python 3.7 due to fromisoformat()

    But this is still a rather not good function and requires a few tricks to make
    it work. So TODO: perhaps switch to python-dateutil package?

    Dateutils package info:
    https://stackoverflow.com/questions/127803/how-do-i-parse-an-iso-8601-formatted-date
    Required tricks for fromisoformat:
    https://stackoverflow.com/questions/127803/how-do-i-parse-an-iso-8601-formatted-date/49784038#49784038

    May raise:
    - DeserializationError
    """
    # Required due to problems with fromisoformat recognizing the ZULU mark
    datestr = datestr.replace('Z', '+00:00')
    # The following function does not always properly handle fractions of a second
    # so let's just remove it and round to the nearest second since we only deal
    # with seconds in the rotkehlchen timestamps
    match = FRACTION_SECS_RE.search(datestr)
    add_a_second = False
    if match:
        fraction_str = match.group(1)
        datestr = datestr.replace('.' + fraction_str, '')
        num = int(fraction_str) / int('1' + '0' * len(fraction_str))
        if num > 0.5:
            add_a_second = True
    try:
        ts = Timestamp(int(datetime.datetime.fromisoformat(datestr).timestamp()))
    except ValueError as e:
        raise DeserializationError(f'Couldnt read {datestr} as iso8601ts timestamp') from e

    return Timestamp(ts + 1) if add_a_second else ts


def timestamp_to_iso8601(ts: Timestamp, utc_as_z: bool = False) -> str:
    """Turns a timestamp to an iso8601 compliant string time

    If `utc_as_z` is True then timezone will be shown with a Z instead of the standard
    +00:00. Z is useful for proper URL encoding."""
    res = datetime.datetime.fromtimestamp(ts, tz=datetime.UTC).isoformat()
    return res if utc_as_z is False else res.replace('+00:00', 'Z')


def satoshis_to_btc(satoshis: int | FVal) -> FVal:
    return satoshis * FVal('0.00000001')


def timestamp_to_date(
        ts: Timestamp,
        formatstr: str = '%d/%m/%Y %H:%M:%S',
        treat_as_local: bool = False,
) -> str:
    """
    Transforms a timestamp to a datestring depending on given formatstr and UTC/local choice
    May raise:
    - OSError: if the ts provided is outside the limits for the system. Happens providing
    close to 0 ts in windows. https://github.com/python/cpython/issues/107078
    - ValueError if the timestamp is out of range.
    """
    if treat_as_local is False:
        date = datetime.datetime.fromtimestamp(ts, tz=datetime.UTC).strftime(formatstr)
    else:  # localtime
        date = datetime.datetime.fromtimestamp(
            ts,
            tz=datetime.datetime.fromtimestamp(ts).astimezone().tzinfo,
        ).strftime(formatstr)

    # Depending on the formatstr we could have empty strings at the end. Strip them.
    return date.rstrip()


def from_wei(wei_value: FVal | int) -> FVal:
    return wei_value / FVal(10 ** 18)


def from_gwei(gwei_value: FVal | int) -> FVal:
    return gwei_value / FVal(10 ** 9)


K = TypeVar('K')
V = TypeVar('V')


@overload
def combine_dicts(a: dict[K, V], b: dict[K, V], op: Callable = operator.add) -> dict[K, V]:
    ...


@overload
def combine_dicts(
        a: defaultdict[K, V],
        b: defaultdict[K, V],
        op: Callable = operator.add,
) -> defaultdict[K, V]:
    ...


def combine_dicts(
        a: dict[K, V] | defaultdict[K, V],
        b: dict[K, V] | defaultdict[K, V],
        op: Callable = operator.add,
) -> dict[K, V] | defaultdict[K, V]:
    new_dict = a.copy()
    # issue for pylint's false positive here: https://github.com/PyCQA/pylint/issues/3987
    if op == operator.sub:  # pylint: disable=comparison-with-callable
        new_dict.update({k: -v for k, v in b.items()})  # type: ignore
    else:
        new_dict.update(b)
    new_dict.update([(k, op(a[k], b[k])) for k in set(b) & set(a)])
    return new_dict


def combine_nested_dicts_inplace(
        a: defaultdict[K, defaultdict[Any, V]],
        b: defaultdict[K, defaultdict[Any, V]],
        op: Callable = operator.add,
) -> defaultdict[K, defaultdict[Any, V]]:
    """Combines nested defaultdicts by modifying `a` in place.

    For each key in `b`, combines the inner dicts using the given operation.
    Returns the modified `a` for method chaining.
    """
    for outer_key, inner_dict_b in b.items():
        if outer_key not in a:  # create new inner dict with same default factory as b's inner dict  # noqa: E501
            a[outer_key] = defaultdict(inner_dict_b.default_factory)

        inner_dict_a = a[outer_key]
        for inner_key, value_b in inner_dict_b.items():  # combine inner dictionaries
            if inner_key in inner_dict_a:
                inner_dict_a[inner_key] = op(inner_dict_a[inner_key], value_b)
            elif op is operator.sub:
                inner_dict_a[inner_key] = op(inner_dict_a.default_factory(), value_b)  # type: ignore[misc]
            else:
                inner_dict_a[inner_key] = value_b
    return a


def convert_to_int(
        val: FVal | (bytes | (str | float)),
        accept_only_exact: bool = True,
) -> int:
    """Try to convert to an int. Either from an FVal or a string. If it's a float
    and it's not whole (like 42.0) and accept_only_exact is False then raise

    Raises:
        ConversionError: If either the given value is not an exact number or its
        type can not be converted
    """
    if isinstance(val, FVal):
        return val.to_int(accept_only_exact)
    if isinstance(val, bytes | str):
        # Since float string are not converted to int we have to first convert
        # to float and try to convert to int afterwards
        try:
            if isinstance(val, str) and val.startswith('0x'):
                return int(val, 16)
            return int(val)
        except ValueError:
            # else also try to turn it into a float
            try:
                return FVal(val).to_int(exact=accept_only_exact)
            except ValueError as e:
                raise ConversionError(f'Could not convert {val!r} to an int') from e
    if isinstance(val, int):
        return val
    if isinstance(val, float) and (val.is_integer() or accept_only_exact is False):
        return int(val)
    # else
    raise ConversionError(f'Can not convert {val} which is of type {type(val)} to int.')


def set_user_agent(session: 'Session') -> None:
    """update the given session headers by adding our user agent string"""
    session.headers.update({'User-Agent': f'rotki/{get_system_spec()["rotkehlchen"]}'})


def hexstr_to_int(value: str) -> int:
    """Turns a hexstring into an int

    May raise:
    - DeserializationError if it can't convert a value to an int or if an unexpected
    type is given.
    """
    try:
        int_value = int(value, 16)
    except ValueError as e:
        raise DeserializationError(f'Could not convert string "{value}" to an int') from e

    return int_value


def bytes_to_hexstr(value: bytes) -> str:
    """Turns bytes into a hexstr

    May raise:
    - DeserializationError if it can't convert a value to hextstrt or if an unexpected
    type is given.
    """
    try:
        hexstr = value.hex()
    except (ConversionError, AttributeError) as e:
        raise DeserializationError(f'Could not turn {value!r} to hex') from e

    return '0x' + hexstr


def bytes_to_address(value: bytes) -> ChecksumEvmAddress:
    """Turns 32 bytes/hexbytes into a checksummed EVM address

    May raise:
    - DeserializationError if it can't convert a value to an int or if an unexpected
    type is given.
    """
    return bytes32hexstr_to_address(bytes_to_hexstr(value))


def bytes_to_solana_address(value: bytes) -> SolanaAddress:
    """Converts bytes into a solana address
    May raise DeserializationError if the value does not contain a valid solana address.
    """
    try:
        return SolanaAddress(str(Pubkey(value)))
    except (ValueError, TypeError) as e:
        raise DeserializationError(f'Invalid solana address: {value!r}') from e


def address_to_bytes32(address: ChecksumEvmAddress) -> bytes:
    return unhexlify(24 * '0' + address.lower()[2:])


def bytes32hexstr_to_address(hexstr: str) -> ChecksumEvmAddress:
    """Turns a 32bit 0x hexstring to checksum evm address"""
    try:
        return ChecksumEvmAddress(to_checksum_address(hexstr[26:]))
    except ValueError as e:
        raise DeserializationError(
            f'Invalid ethereum address: {hexstr[24:]}',
        ) from e


T = TypeVar('T')


@overload
def get_chunks(lst: list[T], n: int) -> Iterator[list[T]]:
    ...


@overload
def get_chunks(lst: Sequence[T], n: int) -> Iterator[Sequence[T]]:
    ...


def get_chunks(lst: Sequence[T] | list[T], n: int) -> Iterator[Sequence[T]] | Iterator[list[T]]:
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def rgetattr(obj: Any, attr: str, *args: Any) -> Any:
    """
    Recursive getattr for nested hierarchies. Taken from:
    https://stackoverflow.com/questions/31174295/getattr-and-setattr-on-nested-subobjects-chained-properties
    """
    def _getattr(obj: Any, attr: str) -> Any:
        return getattr(obj, attr, *args)
    return functools.reduce(_getattr, [obj] + attr.split('.'))


def pairwise(iterable: Iterable[Any]) -> Iterator:
    """ Takes an iterable and returns an iterator that iterates over two of its
    elements in each iteration.

    IMPORTANT: If an ODD number of elements is given then the last one is not iterated.
    For a function that does so check pairwise_longest.
    s -> (s0, s1), (s2, s3), (s4, s5), ..."""
    a = iter(iterable)
    return zip(a, a, strict=False)


def pairwise_longest(iterable: Iterable[Any]) -> Iterator:
    """ Takes an iterable and returns an iterator that iterates over two of its
    elements in each iteration.

    If an odd number of elements is passed then the last elements is None.

    s -> (s0, s1), (s2, s3), (s4, s5), (s6, None)..."""
    a = iter(iterable)
    return zip_longest(a, a)


def shift_num_right_by(num: int, digits: int) -> int:
    """Shift a number to the right by discarding some digits

    We actually use string conversion here since division can provide
    wrong results due to precision errors for very big numbers. e.g.:
    6150000000000000000000000000000000000000000000000 // 1e27
    6.149999999999999e+21   <--- wrong
    """
    try:
        return int(str(num)[:-digits])
    except ValueError:
        # this can happen if num is 0, in which case the shifting code above will raise
        # https://github.com/rotki/rotki/issues/3310
        # Also log if it happens for any other reason
        if num != 0:
            log.error(f'At shift_num_right_by() got unecpected value {num} for num')
        return 0


def is_valid_ethereum_tx_hash(val: str) -> bool:
    """Validates an Ethereum transaction hash."""
    return len(val) == 66 and is_hexstr(val) is True


def create_order_by_rules_list(
        data: dict[str, Any],
        default_order_by_fields: list[str] | None = None,
        default_ascending: list[bool] | None = None,
        is_ascending_by_default: bool = False,
) -> list[tuple[str, bool]] | None:
    """Create a list of attributes and sorting order taking values from DBOrderBySchema
    to be used by the filters that allow sorting. By default, the attribute used for sorting is
    timestamp and the ascending value for this field is False.
    """
    order_by_attributes = data['order_by_attributes'] if data['order_by_attributes'] is not None else default_order_by_fields  # noqa: E501
    if order_by_attributes is None:
        return None

    ascending = data['ascending'] if data['ascending'] is not None else default_ascending
    if ascending is None:
        ascending = []
    return list(zip_longest(order_by_attributes, ascending, fillvalue=is_ascending_by_default))  # type: ignore[arg-type]


def is_production() -> bool:
    """Determine if we are in production by checking if we are packaged and non-dev version"""
    if getattr(sys, 'frozen', False) is False:
        return False

    return get_current_version().our_version.dev is None
