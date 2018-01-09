import os
import time

from rotkelchen.utils import createTimeStamp, ts_now, rlk_jsonloads, rlk_jsondumps

from rotkelchen.history import TradesHistorian, PriceHistorian
from rotkelchen.accounting import Accountant
from rotkelchen.history import get_external_trades

DEFAULT_START_DATE = "01/08/2015"
STATS_FILE = "value.txt"

empty_settings = {
    'ui_floating_precision': 2,
    'main_currency': 'EUR',
    'historical_data_start_date': DEFAULT_START_DATE,
}


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
        except:  # No file found or contents are not json
            self.personal = {}

        try:
            with open(os.path.join(self.data_directory, 'settings.json')) as f:
                self.settings = rlk_jsonloads(f.read())
        except:  # No file found or contents are not json
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

    def get_external_trades(self):
        return get_external_trades(self.data_directory)

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
