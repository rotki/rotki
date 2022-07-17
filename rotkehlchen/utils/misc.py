import calendar
import datetime
import functools
import logging
import operator
import platform
import re
import sys
import time
from itertools import zip_longest
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterable,
    Iterator,
    List,
    Tuple,
    TypeVar,
    Union,
    overload,
)

import pkg_resources
from eth_utils import is_hexstr
from eth_utils.address import to_checksum_address

from rotkehlchen.errors.serialization import ConversionError, DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress, Timestamp, TimestampMS

log = logging.getLogger(__name__)


def ts_now() -> Timestamp:
    return Timestamp(int(time.time()))


def ts_now_in_ms() -> TimestampMS:
    return TimestampMS(int(time.time() * 1000))


def ts_sec_to_ms(ts: Timestamp) -> TimestampMS:
    return TimestampMS(ts * 1000)


def ts_ms_to_sec(ts: TimestampMS) -> Timestamp:
    return Timestamp(int(ts / 1000))


def create_timestamp(datestr: str, formatstr: str = '%Y-%m-%d %H:%M:%S') -> Timestamp:
    """Can throw ValueError due to strptime"""
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
    """
    # Required due to problems with fromisoformat recognizing the ZULU mark
    datestr = datestr.replace("Z", "+00:00")
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
    res = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).isoformat()
    return res if utc_as_z is False else res.replace('+00:00', 'Z')


def satoshis_to_btc(satoshis: Union[int, FVal]) -> FVal:
    return satoshis * FVal('0.00000001')


def timestamp_to_date(
        ts: Timestamp,
        formatstr: str = '%d/%m/%Y %H:%M:%S',
        treat_as_local: bool = False,
) -> str:
    """Transforms a timestamp to a datesring depending on given formatstr and UTC/local choice"""
    if treat_as_local is False:
        date = datetime.datetime.utcfromtimestamp(ts).strftime(formatstr)
    else:  # localtime
        date = datetime.datetime.fromtimestamp(ts).strftime(formatstr)

    # Depending on the formatstr we could have empty strings at the end. Strip them.
    return date.rstrip()


def from_wei(wei_value: FVal) -> FVal:
    return wei_value / FVal(10 ** 18)


def from_gwei(gwei_value: Union[FVal, int]) -> FVal:
    return gwei_value / FVal(10 ** 9)


K = TypeVar('K')
V = TypeVar('V')


@overload
def combine_dicts(a: Dict[K, V], b: Dict[K, V], op: Callable = operator.add) -> Dict[K, V]:  # type: ignore[misc] # noqa: E501
    ...


@overload
def combine_dicts(
        a: DefaultDict[K, V],
        b: DefaultDict[K, V],
        op: Callable = operator.add,
) -> DefaultDict[K, V]:
    ...


def combine_dicts(
        a: Union[Dict[K, V], DefaultDict[K, V]],
        b: Union[Dict[K, V], DefaultDict[K, V]],
        op: Callable = operator.add,
) -> Union[Dict[K, V], DefaultDict[K, V]]:
    new_dict = a.copy()
    # issue for pylint's false positive here: https://github.com/PyCQA/pylint/issues/3987
    if op == operator.sub:  # pylint: disable=comparison-with-callable
        new_dict.update({k: -v for k, v in b.items()})  # type: ignore
    else:
        new_dict.update(b)
    new_dict.update([(k, op(a[k], b[k])) for k in set(b) & set(a)])
    return new_dict


def _add_entries(a: Dict[str, FVal], b: Dict[str, FVal]) -> Dict[str, FVal]:
    return {
        'amount': a['amount'] + b['amount'],
        'usd_value': a['usd_value'] + b['usd_value'],
    }


def combine_stat_dicts(list_of_dicts: List[Dict]) -> Dict:
    if len(list_of_dicts) == 0:
        return {}

    combined_dict = list_of_dicts[0]
    for d in list_of_dicts[1:]:
        combined_dict = combine_dicts(combined_dict, d, _add_entries)

    return combined_dict


def convert_to_int(
        val: Union[FVal, bytes, str, int, float],
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
    if isinstance(val, (bytes, str)):
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
    if isinstance(val, float):
        if val.is_integer() or accept_only_exact is False:
            return int(val)
    # else
    raise ConversionError(f'Can not convert {val} which is of type {type(val)} to int.')


def get_system_spec() -> Dict[str, str]:
    """Collect information about the system and installation."""
    if sys.platform == 'darwin':
        system_info = 'macOS {} {}'.format(
            platform.mac_ver()[0],
            platform.architecture()[0],
        )
    else:
        system_info = '{} {} {} {}'.format(
            platform.system(),
            '_'.join(platform.architecture()),
            platform.release(),
            platform.machine(),
        )

    system_spec = {
        # used to be require 'rotkehlchen.__name__' but as long as setup.py
        # target differs from package we need this
        'rotkehlchen': pkg_resources.require('rotkehlchen')[0].version,
        'python_implementation': platform.python_implementation(),
        'python_version': platform.python_version(),
        'system': system_info,
    }
    return system_spec


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


def hex_or_bytes_to_int(value: Union[bytes, str]) -> int:
    """Turns a bytes/HexBytes or a hexstring into an int

    May raise:
    - ConversionError if it can't convert a value to an int or if an unexpected
    type is given.
    """
    if isinstance(value, bytes):
        int_value = int.from_bytes(value, byteorder='big', signed=False)
    elif isinstance(value, str):
        int_value = hexstr_to_int(value)
    else:
        raise ConversionError(f'Unexpected type {type(value)} given to hex_or_bytes_to_int()')

    return int_value


def hex_or_bytes_to_str(value: Union[bytes, str]) -> str:
    """Turns a bytes/HexBytes or a hexstring into an hex string"""
    if isinstance(value, bytes):
        hexstr = value.hex()
    else:
        hexstr = value.removeprefix('0x')

    return hexstr


def hex_or_bytes_to_address(value: Union[bytes, str]) -> ChecksumEvmAddress:
    """Turns a 32bit bytes/HexBytes or a hexstring into an address

    May raise:
    - DeserializationError if it can't convert a value to an int or if an unexpected
    type is given.
    """
    try:
        hexstr = hex_or_bytes_to_str(value)
    except ConversionError as e:
        raise DeserializationError(f'Could not turn {value!r} to an ethereum address') from e
    try:
        return ChecksumEvmAddress(to_checksum_address('0x' + hexstr[24:]))
    except ValueError as e:
        raise DeserializationError(
            f'Invalid ethereum address: {hexstr[24:]}',
        ) from e


def address_to_bytes32(address: ChecksumEvmAddress) -> str:
    return '0x' + 24 * '0' + address.lower()[2:]


T = TypeVar('T')


def get_chunks(lst: List[T], n: int) -> Iterator[List[T]]:
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
    """ Takes an iteratable and returns an iterator that iterates over two of its
    elements in each iteration.

    IMPORTANT: If an ODD number of elements is given then the last one is not iterated.
    For a function that does so check pairwise_longest.
    s -> (s0, s1), (s2, s3), (s4, s5), ..."""
    a = iter(iterable)
    return zip(a, a)


def pairwise_longest(iterable: Iterable[Any]) -> Iterator:
    """ Takes an iteratable and returns an iterator that iterates over two of its
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
        data: Dict[str, Any],
        timestamp_field: str = 'timestamp',
) -> List[Tuple[str, bool]]:
    """Create a list of attributes and sorting order taking values from DBOrderBySchema
    to be used by the filters that allow sorting. By default the attribute used for sorting is
    timestamp and the ascending value for this field is False.
    """
    order_by_attribute = data['order_by_attributes'] if data['order_by_attributes'] is not None else [timestamp_field]  # noqa: E501
    ascending = data['ascending'] if data['ascending'] is not None else [False]
    return list(zip(order_by_attribute, ascending))
