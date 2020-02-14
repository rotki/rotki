import calendar
import datetime
import json
import logging
import operator
import re
import sys
import time
from http import HTTPStatus
from typing import Any, Callable, Dict, List, Union

import gevent
import requests
from rlp.sedes import big_endian_int

from rotkehlchen.constants import ALL_REMOTES_TIMEOUT, ZERO
from rotkehlchen.constants.timing import QUERY_RETRY_TIMES
from rotkehlchen.errors import (
    ConversionError,
    DeserializationError,
    RecoverableRequestError,
    RemoteError,
    UnableToDecryptRemoteData,
)
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import Fee, FilePath, Timestamp
from rotkehlchen.utils.serialization import rlk_jsondumps, rlk_jsonloads

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def ts_now() -> Timestamp:
    return Timestamp(int(time.time()))


def create_timestamp(datestr: str, formatstr: str = '%Y-%m-%d %H:%M:%S') -> Timestamp:
    """Can throw ValueError due to strptime"""
    return Timestamp(calendar.timegm(time.strptime(datestr, formatstr)))


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
    # Required due to prolems with fomrisoformat recognizing the ZULU mark
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
    except ValueError:
        raise DeserializationError(f'Couldnt read {datestr} as iso8601ts timestamp')

    return Timestamp(ts + 1) if add_a_second else ts


def timestamp_to_iso8601(ts: Timestamp) -> str:
    """Turns a timestamp to an iso8601 compliant string time"""
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).isoformat()


def satoshis_to_btc(satoshis: FVal) -> FVal:
    return satoshis * FVal('0.00000001')


def timestamp_to_date(ts: Timestamp, formatstr: str = '%d/%m/%Y %H:%M:%S') -> str:
    return datetime.datetime.utcfromtimestamp(ts).strftime(formatstr)


def from_wei(wei_value: FVal) -> FVal:
    return wei_value / FVal(10 ** 18)


def combine_dicts(a: Dict, b: Dict, op: Callable = operator.add) -> Dict:
    new_dict = a.copy()
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


def dict_get_sumof(d: Dict[str, Dict[str, FVal]], attribute: str) -> FVal:
    sum_ = ZERO
    for _, value in d.items():
        sum_ += value[attribute]
    return sum_


def merge_dicts(*dict_args: Dict) -> Dict:
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def retry_calls(
        times: int,
        location: str,
        handle_429: bool,
        backoff_in_seconds: Union[int, float],
        method_name: str,
        function: Callable[..., Any],
        **kwargs: Any,
) -> Any:
    """Calls a function that deals with external apis for a given number of times
    untils it fails or until it succeeds.

    If it fails with an acceptable error then we wait for a bit until the next try.

    Can also handle 429 errors with a specific backoff in seconds if required.

    - Raises RemoteError if there is something wrong with contacting the remote
    """
    tries = times
    while True:
        try:
            result = function(**kwargs)

            if handle_429:
                if result.status_code == HTTPStatus.TOO_MANY_REQUESTS and tries != 0:
                    gevent.sleep(backoff_in_seconds)
                    continue
            return result

        except (requests.exceptions.ConnectionError, RecoverableRequestError) as e:
            if isinstance(e, RecoverableRequestError):
                time.sleep(5)

            tries -= 1
            if tries == 0:
                raise RemoteError(
                    "{} query for {} failed after {} tries. Reason: {}".format(
                        location,
                        method_name,
                        times,
                        e,
                    ))


def request_get(
        url: str,
        timeout: int = ALL_REMOTES_TIMEOUT,
        handle_429: bool = False,
        backoff_in_seconds: Union[int, float] = 0,
) -> Union[Dict, List]:
    """
    May raise:
    - UnableToDecryptRemoteData from request_get
    - Remote error if the get request fails
    """
    # TODO make this a bit more smart. Perhaps conditional on the type of request.
    # Not all requests would need repeated attempts
    response = retry_calls(
        times=QUERY_RETRY_TIMES,
        location='',
        handle_429=handle_429,
        backoff_in_seconds=backoff_in_seconds,
        method_name=url,
        function=requests.get,
        # function's arguments
        url=url,
        timeout=timeout,
    )

    try:
        result = rlk_jsonloads(response.text)
    except json.decoder.JSONDecodeError:
        raise UnableToDecryptRemoteData(f'{url} returned malformed json')

    return result


def request_get_direct(
        url: str,
        timeout: int = ALL_REMOTES_TIMEOUT,
        handle_429: bool = False,
        backoff_in_seconds: Union[int, float] = 0,
) -> str:
    """Like request_get, but the endpoint only returns a direct value

    May raise:
    - UnableToDecryptRemoteData from request_get
    - Remote error if the get request fails
    """
    return str(request_get(url, timeout, handle_429, backoff_in_seconds))


def request_get_dict(
        url: str,
        timeout: int = ALL_REMOTES_TIMEOUT,
        handle_429: bool = False,
        backoff_in_seconds: Union[int, float] = 0,
) -> Dict:
    """Like request_get, but the endpoint only returns a dict

    May raise:
    - UnableToDecryptRemoteData from request_get
    - Remote error if the get request fails
    """
    response = request_get(url, timeout, handle_429, backoff_in_seconds)
    assert isinstance(response, Dict)
    return response


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
    elif isinstance(val, (bytes, str)):
        # Since float string are not converted to int we have to first convert
        # to float and try to convert to int afterwards
        try:
            val = float(val)
        except ValueError:
            raise ConversionError(f'Could not convert {val!r} to a float')
        if val.is_integer() or accept_only_exact is False:
            return int(val)
    elif isinstance(val, int):
        return val
    elif isinstance(val, float):
        if val.is_integer() or accept_only_exact is False:
            return int(val)

    raise ConversionError(f'Can not convert {val} which is of type {type(val)} to int.')


def taxable_gain_for_sell(
        taxable_amount: FVal,
        rate_in_profit_currency: FVal,
        total_fee_in_profit_currency: Fee,
        selling_amount: FVal,
) -> FVal:
    return (
        rate_in_profit_currency * taxable_amount -
        total_fee_in_profit_currency * (taxable_amount / selling_amount)
    )


def int_to_big_endian(x: int) -> bytes:
    return big_endian_int.serialize(x)


def hexstring_to_bytes(hexstr: str) -> bytes:
    return bytes.fromhex(hexstr.replace("0x", ""))


def get_system_spec() -> Dict[str, str]:
    """Collect information about the system and installation."""
    import pkg_resources
    import platform

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


def write_history_data_in_file(
        data: List[Dict[str, Any]],
        filepath: FilePath,
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> None:
    log.info(
        'Writing history file',
        filepath=filepath,
        start_time=start_ts,
        end_time=end_ts,
    )
    with open(filepath, 'w') as outfile:
        history_dict: Dict[str, Any] = {}
        history_dict['data'] = data
        history_dict['start_time'] = start_ts
        history_dict['end_time'] = end_ts
        outfile.write(rlk_jsondumps(history_dict))
