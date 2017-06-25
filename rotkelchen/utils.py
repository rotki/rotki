#!/usr/bin/env python
from __future__ import division

import json
import time
import datetime
import subprocess
import operator
import urllib2
import os
import calendar
import csv
from errors import KrakenAPIRateLimitExceeded
from fval import FVal


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


def query_fiat_pair(base, quote, timestamp=None):
    if timestamp is None:
        querystr = 'http://api.fixer.io/latest?base={}'.format(base)
    else:
        querystr = 'http://api.fixer.io/{}?base={}'.format(
            tsToDate(timestamp, formatstr='%Y-%m-%d'), base
        )

    tries = 5
    while True:
        try:
            resp = urllib2.urlopen(urllib2.Request(querystr))
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
    return wei_value / 10 ** 18


def combine_dicts(a, b, op=operator.add):
    return dict(a.items() + b.items() +
                [(k, op(a[k], b[k])) for k in set(b) & set(a)])


def combine_stat_dicts(*args):
    combined_dict = args[0]
    for d in args[1:]:
        combined_dict = combine_dicts(combined_dict, d, add_entries)

    return combined_dict


def dict_get_sumof(d, attribute, **args):
    sum = 0
    for key, value in d.iteritems():
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
        except (urllib2.URLError, KrakenAPIRateLimitExceeded) as e:
            if isinstance(e, KrakenAPIRateLimitExceeded):
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


def safe_urllib_read(urlobj):
    # Attempting to circumvent the httplib incomplete read error
    # https://stackoverflow.com/questions/14149100/incompleteread-using-httplib

    # try:
    #     ret = urlobj.read()
    # except httplib.IncompleteRead, e:
    #     ret = e.partial
    return urlobj.read()


def safe_urllib_read_to_json(urlobj):
    string = safe_urllib_read(urlobj)
    ret = rlk_jsonloads(string)
    return ret


LOG_NOTHING = 0
LOG_NOTIFY = 1
LOG_INFO = LOG_NOTIFY
LOG_ERROR = 2
LOG_DEBUG = 3
LOG_ALERT = 4


class Logger():
    def __init__(self, outfile, should_notify, log_level=LOG_INFO):
        # TODO: Make log level configurable
        self.outfile = outfile
        self.should_notify = should_notify
        self.log_level = log_level

    def output(self, s):
        if isinstance(s, dict):
            s = json.dumps(s, sort_keys=True, indent=4, separators=(',', ': '), cls=RKLEncoder)
        if self.outfile:
            self.outfile.write(str(s) + '\n')
            self.outfile.flush()
        else:
            print(s)

    def notify(self, title, message, duration=60):
        if self.should_notify:
            subprocess.call([
                "notify-send",
                "-t", str(duration * 1000),
                "-a", "rotkelchen",
                title,
                message
            ])
        else:
            self.output("Notification:{}\n{}".format(title, message))

    def lognotify(self, title, message):
        if self.log_level <= LOG_NOTIFY:
            self.output(message)
            self.notify(title, message)

    def loginfo(self, message):
        if self.log_level <= LOG_INFO:
            self.output(message)

    def logdebug(self, message):
        if self.log_level <= LOG_DEBUG:
            self.output(message)

    def logerror(self, message):
        if self.log_level <= LOG_ERROR:
            self.output(message)

    def logalert(self, message):
        if self.log_level <= LOG_ALERT:
            self.output(message)

    def destroy(self):
        if self.outfile:
            self.outfile.close()


def dict_to_csv_file(path, dictionary_list):
    with open(path, 'wb') as f:
        w = csv.DictWriter(f, dictionary_list[0].keys())
        w.writeheader()
        for dic in dictionary_list:
            w.writerow(dic)


def output_to_csv(
        out_dir,
        trades,
        loan_profits,
        asset_movements,
        tx_gas_costs,
        margin_positions):

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    dict_to_csv_file(os.path.join(out_dir, 'trades.csv'), trades)
    dict_to_csv_file(os.path.join(out_dir, 'loan_profits.csv'), loan_profits)
    dict_to_csv_file(os.path.join(out_dir, 'asset_movements.csv'), asset_movements)
    dict_to_csv_file(os.path.join(out_dir, 'tx_gas_costs.csv'), tx_gas_costs)
    dict_to_csv_file(os.path.join(out_dir, 'margin_positions.csv'), margin_positions)


def convert_to_int(val):
    """Try to convert to an int. Either from an FVal or a string. If it's a float
    and it's not whole (like 42.0) then raise"""
    if isinstance(val, FVal):
        return val.to_exact_int()
    elif isinstance(val, (str, unicode)):
        return int(val)
    elif isinstance(val, int):
        return val
    elif isinstance(val, float):
        if val.is_integer():
            return int(val)

    raise ValueError('Can not convert {} which is of type {} to int.'.format(val, type(val)))


def rkl_decode_value(val):
    if isinstance(val, dict):
        new_val = dict()
        for k, v in val.iteritems():
            new_val[k] = rkl_decode_value(v)
        return new_val
    elif isinstance(val, list):
        return [rkl_decode_value(x) for x in val]
    elif isinstance(val, float):
        return FVal(val)
    elif isinstance(val, (str, unicode)):
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
