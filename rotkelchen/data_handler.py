import os
import time

from utils import createTimeStamp, ts_now, rlk_jsonloads, rlk_jsondumps

from history import TradesHistorian, PriceHistorian
from accounting import Accountant

DEFAULT_START_DATE = "01/08/2015"

empty_settings = {
    'statsfile_path': ''
}


class DataHandler(object):

    def __init__(
            self,
            logger,
            poloniex,
            kraken,
            bittrex,
            data_directory):

        self.data_directory = data_directory
        try:
            with open(os.path.join(self.data_directory, 'personal.json')) as f:
                self.personal = rlk_jsonloads(f.read())
        except:  # No file found or contents are not json
            self.personal = empty_settings

        self.log = logger
        self.poloniex = poloniex
        self.kraken = kraken
        self.bittrex = bittrex
        self.trades_historian = TradesHistorian(
            poloniex,
            kraken,
            bittrex,
            logger,
            self.data_directory,
            self.personal,
        )
        self.price_historian = PriceHistorian(
            self.data_directory, self.personal, logger
        )
        self.accountant = Accountant(
            logger=logger,
            price_historian=self.price_historian,
            profit_currency=self.personal.get('main_currency', 'EUR'),
            create_csv=True
        )

        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, 'data', 'eth_tokens.json')) as f:
            self.eth_tokens = rlk_jsonloads(f.read())

        # open the statsfile if existing
        self.stats = list()
        if os.path.isfile(self.personal['statsfile_path']):
            with open(self.personal['statsfile_path'], 'r') as f:
                self.stats = rlk_jsonloads(f.read())

            # Change all timestamp entries from string to timestamp if needed
            if isinstance(self.stats[0]['date'], basestring):
                new_stats = []
                for entry in self.stats:
                    entry['date'] = createTimeStamp(
                        entry['date'], "%d/%m/%Y %H:%M"
                    )
                    new_stats.append(entry)
                self.stats = new_stats
                with open(self.personal['statsfile_path'], 'w') as f:
                    f.write(rlk_jsondumps(self.stats))

    def append_to_stats(self, entry):
        data = {'date': int(time.time()), 'data': entry}
        self.stats.append(data)
        with open(self.personal['statsfile_path'], 'w') as f:
            f.write(rlk_jsondumps(self.stats))

    def extend_stats(self, data):
        self.stats.extend(data)
        with open(self.personal['statsfile_path'], 'w') as f:
            f.write(rlk_jsondumps(self.stats))

    def set_main_currency(self, currency):
        self.accountant.set_main_currency(currency)
        with open(os.path.join(self.data_directory, 'personal.json'), 'w') as f:
            self.personal['main_currency'] = currency
            f.write(rlk_jsondumps(self.personal))

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
