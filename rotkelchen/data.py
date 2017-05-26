import json
import os
import time

from utils import createTimeStamp

from history import TradesHistorian, PriceHistorian
from accounting import Accountant

DEFAULT_START_DATE = "01/08/2015"


class DataHandler(object):

    def __init__(
            self,
            logger,
            poloniex,
            kraken,
            bittrex,
            data_directory):

        self.data_directory = data_directory
        with open(os.path.join(self.data_directory, 'personal.json')) as f:
            self.personal = json.loads(f.read())

        self.log = logger
        self.poloniex = poloniex
        self.kraken = kraken
        self.bittrex = bittrex
        self.trades_historian = TradesHistorian(
            poloniex,
            kraken,
            bittrex,
            self.data_directory,
            self.personal
        )
        self.price_historian = PriceHistorian(
            self.data_directory, self.personal
        )
        self.accountant = Accountant(
            logger=logger,
            price_historian=self.price_historian,
            profit_currency=self.personal.get('main_currency', 'EUR')
        )

        # open the statsfile if existing
        self.stats = list()
        if os.path.isfile(self.personal['statsfile_path']):
            with open(self.personal['statsfile_path'], 'r') as f:
                self.stats = json.loads(f.read())

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
                    f.write(json.dumps(self.stats))

    def append_to_stats(self, entry):
        data = {'date': int(time.time()), 'data': entry}
        self.stats.append(data)
        with open(self.personal['statsfile_path'], 'w') as f:
            f.write(json.dumps(self.stats))

    def set_main_currency(self, currency):
        self.accountant.set_main_currency(currency)
        with open(os.path.join(self.data_directory, 'personal.json'), 'w') as f:
            self.personal['main_currency'] = currency
            f.write(json.dumps(self.personal))

    def process_history(self, start_ts, end_ts):
        history, margin_history, loan_history = self.trades_historian.get_history(start_ts, end_ts)
        return self.accountant.process_history(history, margin_history, loan_history)
