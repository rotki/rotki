#!/usr/bin/env python
from __future__ import division

import json
import time
import datetime
import subprocess
import operator
import urllib2
# from exception import ConnectionError


def sfjson_loads(s):
    """Exception safe json.loads()"""
    try:
        return json.loads(s)
    except:
        return {}


def pretty_json_dumps(data):
    return json.dumps(
                data,
                sort_keys=True,
                indent=4,
                separators=(',', ': ')
            )


def ts_now():
    return int(time.time())


def createTimeStamp(datestr, formatstr="%Y-%m-%d %H:%M:%S"):
    return int(time.mktime(time.strptime(datestr, formatstr)))


def dateToTs(s):
    return int(time.mktime(datetime.datetime.strptime(s, '%d/%m/%Y').timetuple()))


def tsToDate(ts, formatstr='%d/%m/%Y'):
    return datetime.datetime.utcfromtimestamp(ts).strftime(formatstr)


def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def percToStr(perc):
    return "{:6.4}".format(perc * 100)


def floatToStr(f):
    return "{:10.8f}".format(f)


def add_entries(a, b):
    return {
        'amount': a['amount'] + b['amount'],
        'usd_value': a['usd_value'] + b['usd_value']
    }


def floatToPerc(f):
    return '{:.5%}'.format(f)


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
            resp = json.loads(resp.read())
            break
        except:
            if tries == 0:
                raise ValueError('Timeout while trying to query euro price')
            time.sleep(0.05)
            tries -= 1

    try:
        return resp['rates'][quote]
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


LOG_NOTHING = 0
LOG_NOTIFY = 1
LOG_DEBUG = 2


class Logger():
    def __init__(self, outfile, should_notify, log_level=LOG_DEBUG):
        # TODO: Make log level configurable
        self.outfile = outfile
        self.should_notify = should_notify
        self.log_level = log_level

    def output(self, s):
        if isinstance(s, dict):
            s = json.dumps(s, sort_keys=True, indent=4, separators=(',', ': '))
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
                "-a", "leftrader",
                title,
                message
            ])
        else:
            self.output("Notification:{}\n{}".format(title, message))

    def lognotify(self, title, message):
        self.output(message)
        self.notify(title, message)

    def logdebug(self, message):
        if self.log_level >= LOG_DEBUG:
            self.output(message)

    def destroy(self):
        if self.outfile:
            self.outfile.close()
