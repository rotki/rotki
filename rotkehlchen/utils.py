#!/usr/bin/env python
import os
import json
import time
import datetime
import calendar
import operator
from urllib.request import Request, urlopen
from urllib.error import URLError
from collections import namedtuple

from rotkehlchen.errors import RecoverableRequestError
from rotkehlchen.fval import FVal


def sfjson_loads(s):
    """Exception safe json.loads()"""
    try:
        return rlk_jsonloads(s)
    except:
        return {}


def pretty_json_dumps(data):
    return json.dumps(
        data,
        sort_keys=True,
        indent=4,
        separators=(',', ': '),
        cls=RKLEncoder,
    )


def ts_now():
    return int(time.time())


def createTimeStamp(datestr, formatstr="%Y-%m-%d %H:%M:%S"):
    return int(calendar.timegm(time.strptime(datestr, formatstr)))


def dateToTs(s):
    return int(calendar.timegm(datetime.datetime.strptime(s, '%d/%m/%Y').timetuple()))


def tsToDate(ts, formatstr='%d/%m/%Y %H:%M:%S'):
    return datetime.datetime.utcfromtimestamp(ts).strftime(formatstr)


def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def add_entries(a, b):
    return {
        'amount': a['amount'] + b['amount'],
        'usd_value': a['usd_value'] + b['usd_value']
    }


ResultCache = namedtuple('ResultCache', ('result', 'timestamp'))


def cache_response_timewise(seconds=600):
    """ This is a decorator for caching results of functions of objects.
    The objects must adhere to the interface of having:
        - A results_cache dictionary attribute
        - A semaphore attribute named lock

    Objects adhering to this interface are all the exchanges and the rotkehlchen object.
    """
    def _cache_response_timewise(f):
        def wrapper(wrappingobj, *args):
            with wrappingobj.lock:
                now = ts_now()
                cache_miss = (
                    f.__name__ not in wrappingobj.results_cache or
                    now - wrappingobj.results_cache[f.__name__].timestamp > seconds
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


def query_fiat_pair(base, quote, timestamp=None):
    if base == quote:
        return FVal(1.0)

    if timestamp is None:
        querystr = 'http://api.fixer.io/latest?base={}'.format(base)
    else:
        querystr = 'http://api.fixer.io/{}?base={}'.format(
            tsToDate(timestamp, formatstr='%Y-%m-%d'), base
        )

    tries = 5
    while True:
        try:
            resp = urlopen(Request(querystr))
            resp = rlk_jsonloads(resp.read())
            break
        except:
            if tries == 0:
                raise ValueError('Timeout while trying to query euro price')
            time.sleep(0.05)
            tries -= 1

    try:
        return FVal(resp['rates'][quote])
    except:
        raise ValueError('Could not find a "{}" price for "{}"'.format(base, quote))


def from_wei(wei_value):
    return wei_value / FVal(10 ** 18)


def combine_dicts(a, b, op=operator.add):
    new_dict = a.copy()
    new_dict.update(b)
    new_dict.update([(k, op(a[k], b[k])) for k in set(b) & set(a)])
    return new_dict


def combine_stat_dicts(list_of_dicts):
    if len(list_of_dicts) == 0:
        return {}

    combined_dict = list_of_dicts[0]
    for d in list_of_dicts[1:]:
        combined_dict = combine_dicts(combined_dict, d, add_entries)

    return combined_dict


def dict_get_sumof(d, attribute, **args):
    sum = 0
    for key, value in d.items():
        sum += value[attribute]
    return sum


def get_pair_other(pair, this):
    currencies = pair.split('_')
    if len(currencies) != 2:
        raise ValueError("Could not split {} pair".format(pair))
    return currencies[0] if currencies[1] == this else currencies[1]


def get_pair_position(pair, position):
    assert position == 'first' or position == 'second'
    currencies = pair.split('_')
    if len(currencies) != 2:
        raise ValueError("Could not split {} pair".format(pair))
    return currencies[0] if position == 'first' else currencies[1]


def merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def retry_calls(times, location, method, function, *args):
    tries = times
    while True:
        try:
            result = function(*args)
            return result
        except (URLError, RecoverableRequestError) as e:
            if isinstance(e, RecoverableRequestError):
                time.sleep(5)

            tries -= 1
            if tries == 0:
                raise ValueError(
                    "{} query for {} failed after {} tries. Reason: {}".format(
                        location,
                        method,
                        times,
                        e
                    ))


def get_jsonfile_contents_or_empty_list(filepath):
    if not os.path.isfile(filepath):
        return list()

    with open(filepath, 'r') as infile:
        try:
            data = rlk_jsonloads(infile.read())
        except:
            data = list()

    return data


def get_jsonfile_contents_or_empty_dict(filepath):
    if not os.path.isfile(filepath):
        return dict()

    with open(filepath, 'r') as infile:
        try:
            data = rlk_jsonloads(infile.read())
        except:
            data = dict()

    return data


def convert_to_int(val, accept_only_exact=True):
    """Try to convert to an int. Either from an FVal or a string. If it's a float
    and it's not whole (like 42.0) and accept_only_exact is False then raise"""
    if isinstance(val, FVal):
        return val.to_int(accept_only_exact)
    elif isinstance(val, (bytes, str)):
        return int(val)
    elif isinstance(val, int):
        return val
    elif isinstance(val, float):
        if val.is_integer() or accept_only_exact is False:
            return int(val)

    raise ValueError('Can not convert {} which is of type {} to int.'.format(val, type(val)))


def rkl_decode_value(val):
    if isinstance(val, dict):
        new_val = dict()
        for k, v in val.items():
            new_val[k] = rkl_decode_value(v)
        return new_val
    elif isinstance(val, list):
        return [rkl_decode_value(x) for x in val]
    elif isinstance(val, float):
        return FVal(val)
    elif isinstance(val, (bytes, str)):
        try:
            val = float(val)
            return FVal(val)
        except:
            pass

    return val


class RKLDecoder(json.JSONDecoder):

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        return rkl_decode_value(obj)


class RKLEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, FVal):
            return str(obj)
        if isinstance(obj, float):
            raise ValueError("Trying to json encode a float.")

        return json.JSONEncoder.default(self, obj)


def rlk_jsonloads(data):
    return json.loads(data, cls=RKLDecoder)


def rlk_jsondumps(data):
    return json.dumps(data, cls=RKLEncoder)


def taxable_gain_for_sell(
        taxable_amount,
        rate_in_profit_currency,
        total_fee_in_profit_currency,
        selling_amount):
            return (
                rate_in_profit_currency * taxable_amount -
                total_fee_in_profit_currency * (taxable_amount / selling_amount)
            )


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
