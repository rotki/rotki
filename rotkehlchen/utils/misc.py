#!/usr/bin/env python
import calendar
import datetime
import json
import logging
import operator
import os
import sys
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Union

import requests
from rlp.sedes import big_endian_int

from rotkehlchen.constants import ALL_REMOTES_TIMEOUT, ZERO
from rotkehlchen.errors import RecoverableRequestError, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import Fee, FilePath, ResultCache, Timestamp
from rotkehlchen.utils.serialization import rlk_jsondumps, rlk_jsonloads, rlk_jsonloads_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def ts_now() -> Timestamp:
    return Timestamp(int(time.time()))


def createTimeStamp(datestr: str, formatstr: str = '%Y-%m-%d %H:%M:%S') -> Timestamp:
    """Can throw ValueError due to strptime"""
    return Timestamp(calendar.timegm(time.strptime(datestr, formatstr)))


def iso8601ts_to_timestamp(datestr: str) -> Timestamp:
    """Can throw ValueError due to createTimeStamp"""
    return createTimeStamp(datestr, formatstr='%Y-%m-%dT%H:%M:%S.%fZ')


def satoshis_to_btc(satoshis: FVal) -> FVal:
    return satoshis * FVal('0.00000001')


def tsToDate(ts: Timestamp, formatstr: str = '%d/%m/%Y %H:%M:%S') -> str:
    return datetime.datetime.utcfromtimestamp(ts).strftime(formatstr)


def cache_response_timewise() -> Callable:
    """ This is a decorator for caching results of functions of objects.
    The objects must adhere to the interface of having:
        - A results_cache dictionary attribute
        - A semaphore attribute named lock
        - A cache_ttl_secs attribute denoting how long the cache should live.
          Can also be 0 which means cache is disabled.

    Objects adhering to this interface are:
        - all the exchanges
        - the Rotkehlchen object
        - the Blockchain object
    """
    def _cache_response_timewise(f: Callable):
        @wraps(f)
        def wrapper(wrappingobj, *args):
            with wrappingobj.lock:
                now = ts_now()
                cache_life_secs = now - wrappingobj.results_cache[f.__name__].timestamp
                cache_miss = (
                    f.__name__ not in wrappingobj.results_cache or
                    cache_life_secs > wrappingobj.cache_ttl_secs
                )
            if cache_miss:
                result = f(wrappingobj, *args)
                with wrappingobj.lock:
                    wrappingobj.results_cache[f.__name__] = ResultCache(result, now)
                return result

            # else hit the cache
            with wrappingobj.lock:
                return wrappingobj.results_cache[f.__name__].result

        return wrapper
    return _cache_response_timewise


def from_wei(wei_value: FVal) -> FVal:
    return wei_value / FVal(10 ** 18)


def combine_dicts(a: Dict, b: Dict, op=operator.add) -> Dict:
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
        method: str,
        function: Callable[..., Any],
        *args: Any,
) -> Any:
    tries = times
    while True:
        try:
            result = function(*args)
            return result
        except (requests.exceptions.ConnectionError, RecoverableRequestError) as e:
            if isinstance(e, RecoverableRequestError):
                time.sleep(5)

            tries -= 1
            if tries == 0:
                raise RemoteError(
                    "{} query for {} failed after {} tries. Reason: {}".format(
                        location,
                        method,
                        times,
                        e,
                    ))


def request_get(uri: str, timeout: int = ALL_REMOTES_TIMEOUT) -> Union[Dict, List]:
    # TODO make this a bit more smart. Perhaps conditional on the type of request.
    # Not all requests would need repeated attempts
    response = retry_calls(
        5,
        '',
        uri,
        requests.get,
        uri,
        str(timeout),
    )

    if response.status_code != 200:
        raise RemoteError('Get {} returned status code {}'.format(uri, response.status_code))

    try:
        result = rlk_jsonloads(response.text)
    except json.decoder.JSONDecodeError:
        raise ValueError('{} returned malformed json'.format(uri))

    return result


def request_get_direct(uri: str, timeout: int = ALL_REMOTES_TIMEOUT) -> str:
    """Like request_get, but the endpoint only returns a direct value"""
    return str(request_get(uri, timeout))


def request_get_dict(uri: str, timeout: int = ALL_REMOTES_TIMEOUT) -> Dict:
    """Like request_get, but the endpoint only returns a dict"""
    response = request_get(uri, timeout)
    assert isinstance(response, Dict)
    return response


def convert_to_int(
        val: Union[FVal, bytes, str, int, float],
        accept_only_exact: bool = True,
) -> int:
    """Try to convert to an int. Either from an FVal or a string. If it's a float
    and it's not whole (like 42.0) and accept_only_exact is False then raise"""
    if isinstance(val, FVal):
        return val.to_int(accept_only_exact)
    elif isinstance(val, (bytes, str)):
        # Since float string are not converted to int we have to first convert
        # to float and try to convert to int afterwards
        val = float(val)
        return int(val)
    elif isinstance(val, int):
        return val
    elif isinstance(val, float):
        if val.is_integer() or accept_only_exact is False:
            return int(val)

    raise ValueError('Can not convert {} which is of type {} to int.'.format(val, type(val)))


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


def is_number(s: Any) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def int_to_big_endian(x: int) -> bytes:
    return big_endian_int.serialize(x)


def get_system_spec() -> Dict[str, str]:
    """Collect information about the system and installation."""
    import pkg_resources
    import platform
    import rotkehlchen

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

    system_spec = dict(
        rotkehlchen=pkg_resources.require(rotkehlchen.__name__)[0].version,
        python_implementation=platform.python_implementation(),
        python_version=platform.python_version(),
        system=system_info,
    )
    return system_spec


def simple_result(v: Any, msg: str) -> Dict:
    return {'result': v, 'message': msg}


def write_history_data_in_file(data, filepath, start_ts, end_ts):
    log.info(
        'Writing history file',
        filepath=filepath,
        start_time=start_ts,
        end_time=end_ts,
    )
    with open(filepath, 'w') as outfile:
        history_dict = dict()
        history_dict['data'] = data
        history_dict['start_time'] = start_ts
        history_dict['end_time'] = end_ts
        outfile.write(rlk_jsondumps(history_dict))


def get_jsonfile_contents_or_empty_dict(filepath: FilePath) -> Dict:
    if not os.path.isfile(filepath):
        return dict()

    with open(filepath, 'r') as infile:
        try:
            data = rlk_jsonloads_dict(infile.read())
        except json.decoder.JSONDecodeError:
            data = dict()

    return data
