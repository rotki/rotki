import os
import time
from json.decoder import JSONDecodeError

from rotkelchen.utils import (
    createTimeStamp,
    ts_now,
    rlk_jsonloads,
    rlk_jsondumps,
    is_number,
    get_pair_position,
)

from rotkelchen.history import TradesHistorian, PriceHistorian
from rotkelchen.accounting import Accountant
from rotkelchen.history import get_external_trades, EXTERNAL_TRADES_FILE
from rotkelchen.fval import FVal
from rotkelchen.inquirer import FIAT_CURRENCIES

import logging
logger = logging.getLogger(__name__)

DEFAULT_START_DATE = "01/08/2015"
STATS_FILE = "value.txt"

empty_settings = {
    'ui_floating_precision': 2,
    'main_currency': 'EUR',
    'historical_data_start_date': DEFAULT_START_DATE,
}


otc_fields = [
    'otc_time',
    'otc_pair',
    'otc_type',
    'otc_amount',
    'otc_rate',
    'otc_fee',
    'otc_link',
    'otc_notes'
]
otc_optional_fields = ['otc_fee', 'otc_link', 'otc_notes']
otc_numerical_fields = ['otc_amount', 'otc_rate', 'otc_fee']


def check_otctrade_data_valid(data):
    for field in otc_fields:
        if field not in data:
            return None, '{} was not provided'.format(field)

        if data[field] in ('', None) and field not in otc_optional_fields:
            return None, '{} was empty'.format(field)

        if field in otc_numerical_fields and not is_number(data[field]):
            return None, '{} should be a number'.format(field)

    if data['otc_type'] not in ('buy', 'sell'):
        return None, 'Trade type can only be buy or sell'

    try:
        timestamp = createTimeStamp(data['otc_time'], formatstr='%d/%m/%Y %H:%M')
    except ValueError as e:
        return None, 'Could not process the given datetime: {}'.format(e)

    return timestamp, ''


class DataHandler(object):

    def __init__(
            self,
            poloniex,
            kraken,
            bittrex,
            binance,
            data_directory):

        self.data_directory = data_directory
        try:
            with open(os.path.join(self.data_directory, 'personal.json')) as f:
                self.personal = rlk_jsonloads(f.read())
        except JSONDecodeError as e:
            logger.critical('personal.json file could not be decoded and is corrupt: {}'.format(e))
            self.personal = {}
        except FileNotFoundError:
            self.personal = {}

        try:
            with open(os.path.join(self.data_directory, 'settings.json')) as f:
                self.settings = rlk_jsonloads(f.read())
        except JSONDecodeError as e:
            logger.critical('settings.json file could not be decoded and is corrupt: {}'.format(e))
            self.settings = empty_settings
        except FileNotFoundError:
            self.settings = empty_settings

        historical_data_start = self.settings.get('historical_data_start_date', DEFAULT_START_DATE)

        self.poloniex = poloniex
        self.kraken = kraken
        self.bittrex = bittrex
        self.trades_historian = TradesHistorian(
            poloniex,
            kraken,
            bittrex,
            binance,
            self.data_directory,
            self.personal,
            historical_data_start,
        )
        self.price_historian = PriceHistorian(
            self.data_directory,
            historical_data_start,
        )
        self.accountant = Accountant(
            price_historian=self.price_historian,
            profit_currency=self.settings.get('main_currency'),
            create_csv=True
        )

        self.eth_tokens = []
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, 'data', 'eth_tokens.json'), 'r') as f:
            self.eth_tokens = rlk_jsonloads(f.read())

        # open the statsfile if existing
        self.stats = list()
        stats_file = os.path.join(self.data_directory, STATS_FILE)
        if os.path.isfile(stats_file):
            with open(stats_file, 'r') as f:
                self.stats = rlk_jsonloads(f.read())

            # Change all timestamp entries from string to timestamp if needed
            if isinstance(self.stats[0]['date'], (str, bytes)):
                new_stats = []
                for entry in self.stats:
                    entry['date'] = createTimeStamp(
                        entry['date'], "%d/%m/%Y %H:%M"
                    )
                    new_stats.append(entry)
                self.stats = new_stats
                with open(stats_file, 'w') as f:
                    f.write(rlk_jsondumps(self.stats))

    def append_to_stats(self, entry):
        data = {'date': int(time.time()), 'data': entry}
        self.stats.append(data)
        with open(os.path.join(self.data_directory, STATS_FILE), 'w') as f:
            f.write(rlk_jsondumps(self.stats))

    def extend_stats(self, data):
        self.stats.extend(data)
        with open(os.path.join(self.data_directory, STATS_FILE), 'w') as f:
            f.write(rlk_jsondumps(self.stats))

    def set_main_currency(self, currency):
        self.accountant.set_main_currency(currency)
        self.settings['main_currency'] = currency
        with open(os.path.join(self.data_directory, 'settings.json'), 'w') as f:
            f.write(rlk_jsondumps(self.settings))

    def set_ui_floating_precision(self, val):
        self.settings['ui_floating_precision'] = val
        with open(os.path.join(self.data_directory, 'settings.json'), 'w') as f:
            f.write(rlk_jsondumps(self.settings))

    def set_settings(self, settings):
        self.settings = settings
        self.accountant.set_main_currency(settings['main_currency'])
        with open(os.path.join(self.data_directory, 'settings.json'), 'w') as f:
            f.write(rlk_jsondumps(self.settings))

    def store_personal(self):
        with open(os.path.join(self.data_directory, 'personal.json'), 'w') as f:
            f.write(rlk_jsondumps(self.personal))

    def set_fiat_balance(self, currency, balance):
        if currency not in FIAT_CURRENCIES:
            return False, 'Provided currency {} is unknown'

        if balance == 0 or balance == '':
            # delete entry from currencies
            del self.personal['fiat'][currency]
        else:
            try:
                balance = FVal(balance)
            except ValueError:
                return False, 'Provided amount is not a number'

            self.personal['fiat'][currency] = balance

        self.store_personal()

        return True, ''

    def get_external_trades(self):
        return get_external_trades(self.data_directory)

    def add_external_trade(self, data):
        timestamp, message = check_otctrade_data_valid(data)
        if not timestamp:
            return False, message

        rate = float(data['otc_rate'])
        amount = float(data['otc_amount'])
        cost = rate * amount
        pair = data['otc_pair']
        external_trades = get_external_trades(self.data_directory)
        external_trades.append({
            'timestamp': timestamp,
            'pair': pair,
            'type': data['otc_type'],
            'rate': rate,
            'cost': cost,
            # for now cost/fee currency is always second.
            # TODO: Make it configurable
            'cost_currency': get_pair_position(pair, 'second'),
            'fee_currency': get_pair_position(pair, 'second'),
            'fee': data['otc_fee'],
            'amount': amount,
            'location': 'external',
            'link': data['otc_link'],
            'notes': data['otc_notes'],
        })
        with open(os.path.join(self.data_directory, EXTERNAL_TRADES_FILE), 'w') as f:
            f.write(rlk_jsondumps(external_trades))

        return True, ''

    def edit_external_trade(self, data):
        timestamp, message = check_otctrade_data_valid(data)
        if not timestamp:
            return False, message

        rate = float(data['otc_rate'])
        amount = float(data['otc_amount'])
        cost = rate * amount
        pair = data['otc_pair']
        external_trades = get_external_trades(self.data_directory)

        # TODO: When we switch to sql, editing should be done with the primary key
        found = False
        for idx, trade in enumerate(external_trades):
            if timestamp == trade['timestamp']:
                external_trades[idx] = {
                    'timestamp': timestamp,
                    'pair': pair,
                    'type': data['otc_type'],
                    'rate': rate,
                    'cost': cost,
                    # for now cost/fee currency is always second.
                    # TODO: Make it configurable
                    'cost_currency': get_pair_position(pair, 'second'),
                    'fee_currency': get_pair_position(pair, 'second'),
                    'fee': data['otc_fee'],
                    'amount': amount,
                    'location': 'external',
                    'link': data['otc_link'],
                    'notes': data['otc_notes'],
                }
                found = True
                break

        if not found:
            return False, 'Could not find the requested trade for editing'

        with open(os.path.join(self.data_directory, EXTERNAL_TRADES_FILE), 'w') as f:
            f.write(rlk_jsondumps(external_trades))

        return True, ''

    def delete_external_trade(self, data):
        external_trades = get_external_trades(self.data_directory)
        # TODO: When using sql just use primary key as id
        found_idx = -1
        for idx, trade in enumerate(external_trades):
            if trade['timestamp'] == data['timestamp']:
                found_idx = idx
                break

        if found_idx == -1:
            return False, 'Could not find the requested trade for deletion'

        del external_trades[found_idx]
        with open(os.path.join(self.data_directory, EXTERNAL_TRADES_FILE), 'w') as f:
            f.write(rlk_jsondumps(external_trades))

        return True, ''

    def process_history(self, start_ts, end_ts):
        history, margin_history, loan_history, asset_movements, eth_transactions = self.trades_historian.get_history(
            start_ts=0,  # For entire history processing we need to have full history available
            end_ts=ts_now(),
            end_at_least_ts=end_ts
        )
        return self.accountant.process_history(
            start_ts,
            end_ts,
            history,
            margin_history,
            loan_history,
            asset_movements,
            eth_transactions
        )
